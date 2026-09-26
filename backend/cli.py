import asyncio
import re
import secrets
import subprocess
import sys

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import anyio
import cappa
import granian

from cappa.output import error_format
from rich.panel import Panel
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from rich.text import Text
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession
from starlette.concurrency import run_in_threadpool
from watchfiles import Change, PythonFilter

from backend import __version__
from backend.common.enums import DataBaseType, PrimaryKeyType
from backend.common.exception.errors import BaseExceptionError
from backend.common.model import MappedBase
from backend.core.conf import settings
from backend.core.path_conf import (
    BASE_PATH,
    ENV_EXAMPLE_FILE_PATH,
    ENV_FILE_PATH,
    MYSQL_SCRIPT_DIR,
    PLUGIN_DIR,
    POSTGRESQL_SCRIPT_DIR,
    RELOAD_LOCK_FILE,
)
from backend.database.db import (
    async_db_session,
    create_database_async_engine,
    create_database_async_session,
    create_database_url,
)
from backend.database.redis import RedisCli, redis_client
from backend.plugin.core import get_plugin_sql, get_plugins
from backend.plugin.installer import install_git_plugin, install_zip_plugin, zip_plugin
from backend.plugin.installer import remove_plugin as _remove_plugin
from backend.plugin.requirements import uninstall_requirements_async
from backend.utils.console import console
from backend.utils.dynamic_import import import_module_cached
from backend.utils.sql_parser import parse_sql_script
from backend.utils.timezone import timezone

output_help = "\nFor more information, try '[cyan]--help[/]'"


class CustomReloadFilter(PythonFilter):
    """Custom reload filter"""

    _EXCLUDE_DIRS = ('frontend', '.next', 'node_modules', '.ai_state', 'OA', 'OA_MapScanner')

    def __init__(self) -> None:
        super().__init__(extra_extensions=['.json', '.yaml', '.yml'])

    def __call__(self, change: Change, path: str) -> bool:
        if RELOAD_LOCK_FILE.exists():
            return False
        normalized = path.replace('\\', '/')
        for d in self._EXCLUDE_DIRS:
            if f'/{d}/' in normalized:
                return False
        return super().__call__(change, path)


def setup_env_file() -> bool:
    if not ENV_EXAMPLE_FILE_PATH.exists():
        console.print('.env.example file does not exist', style='red')
        return False

    try:
        env_content = Path(ENV_EXAMPLE_FILE_PATH).read_text(encoding='utf-8')
        console.print('Configuring database connection information...', style='white')
        db_type = Prompt.ask('Database type', choices=['mysql', 'postgresql'], default='postgresql')
        db_host = Prompt.ask('Database host', default='127.0.0.1')
        db_port = Prompt.ask('Database port', default='5432' if db_type == 'postgresql' else '3306')
        db_user = Prompt.ask('Database username', default='postgres' if db_type == 'postgresql' else 'root')
        db_password = Prompt.ask('Database password', password=True, default='123456')

        console.print('Configuring Redis connection information...', style='white')
        redis_host = Prompt.ask('Redis host', default='127.0.0.1')
        redis_port = Prompt.ask('Redis port', default='6379')
        redis_password = Prompt.ask('Redis password (leave empty for no password)', password=True, default='')
        redis_db = Prompt.ask('Redis database number', default='0')

        console.print('Generating token secret key...', style='white')
        token_secret = secrets.token_urlsafe(32)

        console.print('Writing .env file...', style='white')
        env_content = env_content.replace("DATABASE_TYPE='postgresql'", f"DATABASE_TYPE='{db_type}'")
        settings.DATABASE_TYPE = db_type
        env_content = env_content.replace("DATABASE_HOST='127.0.0.1'", f"DATABASE_HOST='{db_host}'")
        settings.DATABASE_HOST = db_host
        env_content = env_content.replace('DATABASE_PORT=5432', f'DATABASE_PORT={db_port}')
        settings.DATABASE_PORT = db_port
        env_content = env_content.replace("DATABASE_USER='postgres'", f"DATABASE_USER='{db_user}'")
        settings.DATABASE_USER = db_user
        env_content = env_content.replace("DATABASE_PASSWORD='123456'", f"DATABASE_PASSWORD='{db_password}'")
        settings.DATABASE_PASSWORD = db_password
        env_content = env_content.replace("REDIS_HOST='127.0.0.1'", f"REDIS_HOST='{redis_host}'")
        settings.REDIS_HOST = redis_host
        env_content = env_content.replace('REDIS_PORT=6379', f'REDIS_PORT={redis_port}')
        settings.REDIS_PORT = redis_port
        env_content = env_content.replace("REDIS_PASSWORD=''", f"REDIS_PASSWORD='{redis_password}'")
        settings.REDIS_PASSWORD = redis_password
        env_content = env_content.replace('REDIS_DATABASE=0', f'REDIS_DATABASE={redis_db}')
        settings.REDIS_DATABASE = redis_db
        env_content = re.sub(r"TOKEN_SECRET_KEY='[^']*'", f"TOKEN_SECRET_KEY='{token_secret}'", env_content)
        settings.TOKEN_SECRET_KEY = token_secret

        Path(ENV_FILE_PATH).write_text(env_content, encoding='utf-8')
        console.print('.env file created successfully', style='green')
    except Exception as e:
        console.print(f'.env file creation failed: {e}', style='red')
        return False
    else:
        return True


async def create_database(conn: AsyncConnection) -> bool:
    try:
        terminate_sql = None
        if DataBaseType.mysql == settings.DATABASE_TYPE:
            check_sql = f"SHOW DATABASES LIKE '{settings.DATABASE_SCHEMA}'"
            drop_sql = f'DROP DATABASE IF EXISTS `{settings.DATABASE_SCHEMA}`'
            create_sql = (
                f'CREATE DATABASE `{settings.DATABASE_SCHEMA}` CHARACTER SET {settings.DATABASE_CHARSET} '
                f'COLLATE {settings.DATABASE_CHARSET}_unicode_ci'
            )
        else:
            check_sql = f"SELECT 1 FROM pg_database WHERE datname = '{settings.DATABASE_SCHEMA}'"
            drop_sql = f'DROP DATABASE IF EXISTS {settings.DATABASE_SCHEMA}'
            create_sql = f'CREATE DATABASE {settings.DATABASE_SCHEMA}'
            terminate_sql = (
                f'SELECT pg_terminate_backend(pid) FROM pg_stat_activity '
                f"WHERE datname = '{settings.DATABASE_SCHEMA}' AND pid <> pg_backend_pid()"
            )

        result = await conn.execute(text(check_sql))
        exists = result.fetchone() is not None
        console.print(f'Rebuilding database {settings.DATABASE_SCHEMA}...', style='white')
        if exists:
            if terminate_sql:
                await conn.execute(text(terminate_sql))
            await conn.execute(text(drop_sql))
        await conn.execute(text(create_sql))
        console.print('Database created successfully', style='green')
    except Exception as e:
        console.print(f'Database creation failed: {e}', style='red')
        return False
    else:
        return True


async def auto_init() -> None:
    """Automated initialization flow"""
    console.print('\n[bold cyan]Step 1/3:[/] Configure environment variables', style='bold')
    panel_content = Text()
    panel_content.append('[Environment variable configuration]', style='bold green')
    panel_content.append('\n\n  • Database connection information')
    panel_content.append('\n  • Redis connection information')
    panel_content.append('\n  • Token secret key (auto-generated)')

    console.print(
        Panel(panel_content, title=f'fba (v{__version__}) - Environment variables', border_style='cyan', padding=(1, 2))
    )
    if not setup_env_file():
        raise cappa.Exit('.env file configuration failed', code=1)

    console.print('\n[bold cyan]Step 2/3:[/] Database creation', style='bold')
    panel_content = Text()
    panel_content.append('[Database configuration]', style='bold green')
    panel_content.append('\n\n  • Type: ')
    panel_content.append(f'{settings.DATABASE_TYPE}', style='yellow')
    panel_content.append('\n  • Host: ')
    panel_content.append(f'{settings.DATABASE_HOST}:{settings.DATABASE_PORT}', style='yellow')
    panel_content.append('\n  • Database: ')
    panel_content.append(f'{settings.DATABASE_SCHEMA}', style='yellow')
    panel_content.append('\n  • Primary key mode: ')
    panel_content.append(f'{settings.DATABASE_PK_MODE}', style='yellow')

    console.print(Panel(panel_content, title=f'fba (v{__version__}) - Database', border_style='cyan', padding=(1, 2)))
    ok = Prompt.ask(
        'This will [red]create/rebuild the database[/red], are you sure you want to continue?',
        choices=['y', 'n'],
        default='n',
    )

    if ok.lower() == 'y':
        async_init_engine = create_database_async_engine(create_database_url(with_database=False))
        async with async_init_engine.connect() as conn:
            await conn.execution_options(isolation_level='AUTOCOMMIT')
            if not await create_database(conn):
                raise cappa.Exit('Database creation failed', code=1)
    else:
        console.print('Database operation cancelled', style='yellow')

    console.print('\n[bold cyan]Step 3/3:[/] Initialize database tables and data', style='bold')
    async_init_engine = create_database_async_engine(create_database_url())
    async_init_db_session = create_database_async_session(async_init_engine)
    redis_init_client = RedisCli(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=settings.REDIS_DATABASE,
    )
    await redis_init_client.init()
    async with async_init_db_session.begin() as db:
        await init(db, redis_init_client)


INIT_REDIS_CLEAR_PREFIXES = [
    settings.JWT_USER_REDIS_PREFIX,
    settings.TOKEN_EXTRA_INFO_REDIS_PREFIX,
    settings.TOKEN_REDIS_PREFIX,
    settings.TOKEN_REFRESH_REDIS_PREFIX,
    settings.CACHE_CONFIG_REDIS_PREFIX,
    settings.CACHE_DICT_REDIS_PREFIX,
    settings.PLUGIN_REDIS_PREFIX,
    settings.IP_LOCATION_REDIS_PREFIX,
]
"""Redis key prefixes cleared by `fba init` so stale cached/config/plugin data
doesn't survive a re-seed. Plugin cache (`fba:plugin`) is safe to clear here
because `parse_plugin_config()` (backend/plugin/core.py) rebuilds it on every
backend startup, including the `fba run` that normally follows `fba init`."""


async def init(db: AsyncSession, redis: RedisCli) -> None:
    panel_content = Text()
    panel_content.append('[Database configuration]', style='bold green')
    panel_content.append('\n\n  • Type: ')
    panel_content.append(f'{settings.DATABASE_TYPE}', style='yellow')
    panel_content.append('\n  • Host: ')
    panel_content.append(f'{settings.DATABASE_HOST}:{settings.DATABASE_PORT}', style='yellow')
    panel_content.append('\n  • Database: ')
    panel_content.append(f'{settings.DATABASE_SCHEMA}', style='yellow')
    panel_content.append('\n  • Primary key mode: ')
    panel_content.append(f'{settings.DATABASE_PK_MODE}', style='yellow')
    pk_details = panel_content.from_markup(
        '[link=https://fastapi-practices.github.io/fastapi_best_architecture_docs/backend/reference/pk.html]'
        '(learn more)[/]'
    )
    panel_content.append(pk_details)
    panel_content.append('\n\n[Redis configuration]', style='bold green')
    panel_content.append('\n\n  • Host: ')
    panel_content.append(f'{settings.REDIS_HOST}:{settings.REDIS_PORT}', style='yellow')
    panel_content.append('\n  • Database: ')
    panel_content.append(f'{settings.REDIS_DATABASE}', style='yellow')
    plugins = get_plugins()
    panel_content.append('\n\n[Installed plugins]', style='bold green')
    panel_content.append('\n\n  • ')
    if plugins:
        panel_content.append(f'{", ".join(plugins)}', style='yellow')
    else:
        panel_content.append('None', style='dim')

    console.print(
        Panel(panel_content, title=f'fba (v{__version__}) - Initialization', border_style='cyan', padding=(1, 2))
    )
    ok = Prompt.ask(
        'This will [red]create/rebuild the database tables[/red] and [red]run all database scripts[/red], '
        'are you sure you want to continue?',
        choices=['y', 'n'],
        default='n',
    )

    if ok.lower() == 'y':
        console.print('Starting initialization...', style='white')
        try:
            console.print('Clearing Redis cache', style='white')
            for prefix in INIT_REDIS_CLEAR_PREFIXES:
                await redis.delete_prefix(prefix)

            console.print('Rebuilding database tables', style='white')
            conn = await db.connection()
            await conn.run_sync(MappedBase.metadata.drop_all)
            if settings.DATABASE_TYPE != 'mysql':
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
            await conn.run_sync(MappedBase.metadata.create_all)

            console.print('Running SQL scripts', style='white')
            sql_scripts = await get_sql_scripts()
            for sql_script in sql_scripts:
                console.print(f'Running: {sql_script}', style='white')
                await execute_sql_scripts(db, sql_script, is_init=True)

            console.print('Initialization successful', style='green')
            console.print('\nGive [bold cyan]fba run[/bold cyan] a try to start the service~')
        except Exception as e:
            raise cappa.Exit(f'Initialization failed: {e}', code=1)
    else:
        console.print('Initialization cancelled', style='yellow')


def run(host: str, port: int, reload: bool, workers: int) -> None:  # noqa: FBT001
    url = f'http://{host}:{port}'
    docs_url = url + settings.FASTAPI_DOCS_URL
    redoc_url = url + settings.FASTAPI_REDOC_URL
    openapi_url = url + (settings.FASTAPI_OPENAPI_URL or '')

    panel_content = Text()
    panel_content.append('Python version: ', style='bold cyan')
    panel_content.append(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}', style='white')

    panel_content.append('\nAPI request address: ', style='bold cyan')
    panel_content.append(f'{url}{settings.FASTAPI_API_V1_PATH}', style='blue')

    panel_content.append('\n\nEnvironment mode: ', style='bold green')
    env_style = 'yellow' if settings.ENVIRONMENT == 'dev' else 'green'
    panel_content.append(f'{settings.ENVIRONMENT.upper()}', style=env_style)

    plugins = get_plugins()
    panel_content.append('\nInstalled plugins: ', style='bold green')
    if plugins:
        panel_content.append(f'{", ".join(plugins)}', style='yellow')
    else:
        panel_content.append('None', style='white')

    if settings.ENVIRONMENT == 'dev':
        panel_content.append(f'\n\n📖 Swagger docs: {docs_url}', style='bold magenta')
        panel_content.append(f'\n📚 Redoc   docs: {redoc_url}', style='bold magenta')
        panel_content.append(f'\n📡 OpenAPI JSON: {openapi_url}', style='bold magenta')

    panel_content.append('\n🌐 Official architecture docs: ', style='bold magenta')
    panel_content.append('https://fastapi-practices.github.io/fastapi_best_architecture_docs/')

    console.print(Panel(panel_content, title=f'fba (v{__version__})', border_style='purple', padding=(1, 2)))
    granian.Granian(
        target='backend.main:app',
        interface='asgi',
        address=host,
        port=port,
        reload=not reload,
        reload_filter=CustomReloadFilter,
        workers=workers,
    ).serve()


def run_celery_worker(log_level: Literal['info', 'debug']) -> None:
    try:
        subprocess.run(['celery', '-A', 'backend.app.task.celery', 'worker', '-l', f'{log_level}', '-P', 'gevent'])
    except KeyboardInterrupt:
        pass


def run_celery_beat(log_level: Literal['info', 'debug']) -> None:
    try:
        subprocess.run(['celery', '-A', 'backend.app.task.celery', 'beat', '-l', f'{log_level}'])
    except KeyboardInterrupt:
        pass


def run_celery_flower(port: int, basic_auth: str) -> None:
    try:
        subprocess.run([
            'celery',
            '-A',
            'backend.app.task.celery',
            'flower',
            f'--port={port}',
            f'--basic-auth={basic_auth}',
        ])
    except KeyboardInterrupt:
        pass


async def install_plugin(
    path: str,
    repo_url: str,
    no_sql: bool,  # noqa: FBT001
    db_type: DataBaseType,
    pk_type: PrimaryKeyType,
) -> None:
    if settings.ENVIRONMENT != 'dev':
        raise cappa.Exit('Plugin installation is only available in the dev environment', code=1)

    if not path and not repo_url:
        raise cappa.Exit('One of path or repo_url must be specified', code=1)
    if path and repo_url:
        raise cappa.Exit('path and repo_url cannot both be specified', code=1)

    plugin_name = None
    console.print('Starting plugin installation...', style='bold cyan')

    try:
        if path:
            plugin_name = await install_zip_plugin(file=path)
        if repo_url:
            plugin_name = await install_git_plugin(repo_url=repo_url)

        console.print(f'Plugin {plugin_name} installed successfully', style='bold green')

        sql_file = await get_plugin_sql(plugin_name, db_type, pk_type)
        if sql_file and not no_sql:
            console.print('Automatically running the plugin SQL script...', style='bold cyan')
            async with async_db_session.begin() as db:
                await execute_sql_scripts(db, sql_file)

    except Exception as e:
        raise cappa.Exit(e.msg if isinstance(e, BaseExceptionError) else str(e), code=1)


async def remove_plugin(plugin: str | None) -> None:
    if settings.ENVIRONMENT != 'dev':
        raise cappa.Exit('Plugin removal is only available in the dev environment', code=1)

    async def remove() -> None:
        plugin_dir = PLUGIN_DIR / plugin
        if not plugin_dir.exists():
            raise cappa.Exit(f'Plugin {plugin} does not exist', code=1)

        console.print(f'Uninstalling dependencies for plugin {plugin}...', style='white')
        await uninstall_requirements_async(plugin)

        console.print(f'Backing up plugin {plugin}...', style='white')
        backup_file = PLUGIN_DIR / f'{plugin}.{timezone.now().strftime("%Y%m%d%H%M%S")}.backup.zip'
        await run_in_threadpool(zip_plugin, plugin_dir, backup_file)
        await run_in_threadpool(_remove_plugin, plugin_dir)

        console.print(f'Backup file: {backup_file}', style='white')
        console.print(f'Plugin {plugin} removed successfully', style='bold green')
        console.print(
            '\nPlease remove related configuration per the plugin README.md and restart the service', style='yellow'
        )

    plugins = get_plugins()
    if not plugins:
        raise cappa.Exit('No plugins are currently installed', code=1)

    if not plugin:
        table = Table(show_header=True, header_style='bold magenta')
        table.add_column('No.', style='cyan', no_wrap=True, justify='center')
        table.add_column('Plugin name', style='green', no_wrap=True)

        for idx, name in enumerate(plugins, 1):
            table.add_row(str(idx), name)

        console.print(table)
        choice = IntPrompt.ask(
            'Select the number of the plugin to remove', choices=[str(i) for i in range(1, len(plugins) + 1)]
        )
        plugin = plugins[choice - 1]
    else:
        if plugin not in plugins:
            raise cappa.Exit(f'Plugin {plugin} does not exist', code=1)

    try:
        await remove()
    except Exception as e:
        raise cappa.Exit(f'Plugin removal failed: {e}', code=1)


async def get_sql_scripts() -> list[str]:
    sql_scripts = []
    db_script_dir = MYSQL_SCRIPT_DIR if DataBaseType.mysql == settings.DATABASE_TYPE else POSTGRESQL_SCRIPT_DIR
    main_sql_file = (
        db_script_dir / 'init_test_data.sql'
        if PrimaryKeyType.autoincrement == settings.DATABASE_PK_MODE
        else db_script_dir / 'init_snowflake_test_data.sql'
    )

    main_sql_path = anyio.Path(main_sql_file)
    if await main_sql_path.exists():
        sql_scripts.append(str(main_sql_file))

    skip_names = {'init_test_data.sql', 'init_snowflake_test_data.sql'}
    db_script_async_dir = anyio.Path(db_script_dir)
    async for child in db_script_async_dir.iterdir():
        name = child.name
        if (
            name.endswith('.sql')
            and name.startswith('init_')
            and name not in skip_names
            and str(child) not in sql_scripts
        ):
            sql_scripts.append(str(child))

    plugins = get_plugins()
    for plugin in plugins:
        plugin_sql = await get_plugin_sql(plugin, settings.DATABASE_TYPE, settings.DATABASE_PK_MODE)
        if plugin_sql:
            sql_scripts.append(str(plugin_sql))

    return sql_scripts


async def execute_sql_scripts(db: AsyncSession, sql_scripts: str, *, is_init: bool = False) -> None:
    try:
        stmts = await parse_sql_script(sql_scripts)
        for stmt in stmts:
            await db.execute(text(stmt))
    except Exception as e:
        raise cappa.Exit(f'SQL script execution failed: {e}', code=1)

    if not is_init:
        console.print('SQL script execution completed', style='bold green')


async def import_table(
    app: str,
    table_schema: str,
    table_name: str,
) -> None:
    if settings.ENVIRONMENT != 'dev':
        raise cappa.Exit('Code generation is only available in the dev environment', code=1)

    from backend.plugin.code_generator.schema.gen import ImportParam
    from backend.plugin.code_generator.service.gen_service import gen_service

    try:
        obj = ImportParam(app=app, table_schema=table_schema, table_name=table_name)
        async with async_db_session.begin() as db:
            await gen_service.import_business_and_model(db=db, obj=obj)
        console.log('Code generation business and model columns imported successfully', style='bold green')
        console.log('\nGive [bold cyan]fba codegen[/bold cyan] a try to generate code~')
    except Exception as e:
        raise cappa.Exit(e.msg if isinstance(e, BaseExceptionError) else str(e), code=1)


async def generate(*, preview: bool = False) -> None:
    if settings.ENVIRONMENT != 'dev':
        raise cappa.Exit('Code generation is only available in the dev environment', code=1)

    from backend.plugin.code_generator.service.business_service import gen_business_service
    from backend.plugin.code_generator.service.gen_service import gen_service

    try:
        ids = []
        async with async_db_session() as db:
            results = await gen_business_service.get_all(db=db)

        if not results:
            raise cappa.Exit(
                '[red]No code generation business is available yet! Import one first with the import command![/]'
            )

        table = Table(show_header=True, header_style='bold magenta')
        table.add_column('Business ID', style='cyan', no_wrap=True, justify='center')
        table.add_column('App name', style='green', no_wrap=True)
        table.add_column('Generation path', style='yellow')
        table.add_column('Remark', style='blue')

        for result in results:
            ids.append(result.id)
            table.add_row(
                str(result.id),
                result.app_name,
                result.gen_path or f'App {result.app_name} root path',
                result.remark or '',
            )

        console.print(table)
        business = IntPrompt.ask('Choose a business ID from the list', choices=[str(id_) for id_ in ids])

        # Preview
        async with async_db_session() as db:
            preview_data = await gen_service.preview(db=db, pk=business)

        console.print('\n[bold yellow]The following files will be generated:[/]')
        file_table = Table(show_header=True, header_style='bold cyan')
        file_table.add_column('File path', style='white')
        file_table.add_column('Size', style='green', justify='right')

        for filepath, content in sorted(preview_data.items()):
            size = len(content)
            size_str = f'{size} B' if size < 1024 else f'{size / 1024:.1f} KB'
            file_table.add_row(filepath, size_str)

        console.print(file_table)

        if preview:
            console.print('\n[bold cyan]Preview mode: no actual generation was performed[/]')
            return

        # Generate
        console.print(
            '\n[bold red]Warning: code generation will write (overwrite) files on disk, '
            'never use this in production![/]'
        )
        ok = Prompt.ask('\nConfirm you want to continue generating the code?', choices=['y', 'n'], default='n')

        if ok.lower() == 'y':
            async with async_db_session.begin() as db:
                gen_path = await gen_service.generate(db=db, pk=business)

            console.print('\nCode generated successfully', style='bold green')
            console.print(Text('\nSee details at: '), Text(str(gen_path), style='bold white'))

    except Exception as e:
        raise cappa.Exit(e.msg if isinstance(e, BaseExceptionError) else str(e), code=1)


def run_alembic(*args: str) -> None:
    """Run an alembic command"""
    try:
        subprocess.run(['alembic', *args], cwd=BASE_PATH.parent, check=True)
    except subprocess.CalledProcessError as e:
        raise cappa.Exit('Alembic command execution failed', code=e.returncode)


@cappa.command(help='Initialize the fba project', default_long=True)
@dataclass
class Init:
    auto: Annotated[
        bool,
        cappa.Arg(
            default=False,
            help='Automated initialization mode: automatically create .env, install dependencies, create the '
            'database and initialize the table structure',
        ),
    ]

    async def __call__(self) -> None:
        if self.auto:
            await auto_init()
        else:
            async with async_db_session.begin() as db:
                await init(db, redis_client)


@cappa.command(help='Run the API service', default_long=True)
@dataclass
class Run:
    host: Annotated[
        str,
        cappa.Arg(
            default='127.0.0.1',
            help='The host IP address to serve on; for local development use `127.0.0.1`. '
            'To enable public access, e.g. on a LAN, use `0.0.0.0`',
        ),
    ]
    port: Annotated[
        int,
        cappa.Arg(default=28000, help='The host port number to serve on'),
    ]
    no_reload: Annotated[
        bool,
        cappa.Arg(default=False, help='Disable automatically reloading the server on (code) file changes'),
    ]
    workers: Annotated[
        int,
        cappa.Arg(default=1, help='Use multiple worker processes, must be used together with `--no-reload`'),
    ]

    def __call__(self) -> None:
        run(host=self.host, port=self.port, reload=self.no_reload, workers=self.workers)


@cappa.command(help='Add a plugin', default_long=True)
@dataclass
class Add:
    path: Annotated[
        str | None,
        cappa.Arg(help='The local full path of the ZIP plugin'),
    ]
    repo_url: Annotated[
        str | None,
        cappa.Arg(help='The repository URL of the Git plugin'),
    ]
    no_sql: Annotated[
        bool,
        cappa.Arg(default=False, help='Disable automatically running the plugin SQL script'),
    ]
    db_type: Annotated[
        DataBaseType,
        cappa.Arg(default='postgresql', help='The database type used to run the plugin SQL script'),
    ]
    pk_type: Annotated[
        PrimaryKeyType,
        cappa.Arg(default='autoincrement', help='The database primary key type used to run the plugin SQL script'),
    ]

    async def __call__(self) -> None:
        await install_plugin(self.path, self.repo_url, self.no_sql, self.db_type, self.pk_type)


@cappa.command(help='Remove a plugin')
@dataclass
class Remove:
    plugin: Annotated[
        str | None,
        cappa.Arg(default=None, help='The name of the plugin to remove'),
    ]

    async def __call__(self) -> None:
        await remove_plugin(self.plugin)


@cappa.command(help='Format code')
@dataclass
class Format:
    def __call__(self) -> None:
        try:
            subprocess.run(['prek', 'run', '--all-files'], cwd=BASE_PATH.parent, check=False)
        except FileNotFoundError:
            raise cappa.Exit('prek is not installed, please install the project dependencies first', code=1)
        except KeyboardInterrupt:
            pass


@cappa.command(help='Start the Celery worker service from this host', default_long=True)
@dataclass
class Worker:
    log_level: Annotated[
        Literal['info', 'debug'],
        cappa.Arg(short='-l', default='info', help='Log output level'),
    ]

    def __call__(self) -> None:
        run_celery_worker(log_level=self.log_level)


@cappa.command(help='Start the Celery beat service from this host', default_long=True)
@dataclass
class Beat:
    log_level: Annotated[
        Literal['info', 'debug'],
        cappa.Arg(short='-l', default='info', help='Log output level'),
    ]

    def __call__(self) -> None:
        run_celery_beat(log_level=self.log_level)


@cappa.command(help='Start the Celery flower service from this host', default_long=True)
@dataclass
class Flower:
    port: Annotated[
        int,
        cappa.Arg(default=8555, help='The host port number to serve on'),
    ]
    basic_auth: Annotated[
        str,
        cappa.Arg(default='admin:123456', help='The username and password for logging into the page'),
    ]

    def __call__(self) -> None:
        run_celery_flower(port=self.port, basic_auth=self.basic_auth)


@cappa.command(help='Run the Celery service')
@dataclass
class Celery:
    subcmd: cappa.Subcommands[Worker | Beat | Flower]


@cappa.command(help='Import code generation business and model columns', default_long=True)
@dataclass
class Import:
    app: Annotated[
        str,
        cappa.Arg(help='App name, used to generate code into the specified app'),
    ]
    table_schema: Annotated[
        str,
        cappa.Arg(short='tc', default='fba', help='Database name'),
    ]
    table_name: Annotated[
        str,
        cappa.Arg(short='tn', help='Database table name'),
    ]

    def __post_init__(self) -> None:
        try:
            import_module_cached('backend.plugin.code_generator')
        except ImportError:
            raise cappa.Exit('The code generator plugin does not exist, please install this plugin first')

    async def __call__(self) -> None:
        await import_table(self.app, self.table_schema, self.table_name)


@cappa.command(
    name='codegen',
    help='Code generation (for the full experience, deploy the fba vben frontend yourself)',
    default_long=True,
)
@dataclass
class CodeGenerator:
    preview: Annotated[
        bool,
        cappa.Arg(
            short='-p',
            default=False,
            help='Only preview the files that would be generated, without actually generating them',
        ),
    ]
    subcmd: cappa.Subcommands[Import | None] = None

    def __post_init__(self) -> None:
        try:
            import_module_cached('backend.plugin.code_generator')
        except ImportError:
            raise cappa.Exit('The code generator plugin does not exist, please install this plugin first')

    async def __call__(self) -> None:
        await generate(preview=self.preview)


@cappa.command(help='Generate a database migration file', default_long=True)
@dataclass
class Revision:
    autogenerate: Annotated[
        bool,
        cappa.Arg(default=True, help='Automatically detect model changes and generate a migration script'),
    ]
    message: Annotated[
        str,
        cappa.Arg(short='-m', default='', help='Description for the migration file'),
    ]

    def __call__(self) -> None:
        args = ['revision']
        if self.autogenerate:
            args.append('--autogenerate')
        if self.message:
            args.extend(['-m', self.message])
        run_alembic(*args)
        console.print('Migration file generated successfully', style='bold green')


@cappa.command(help='Upgrade the database to the specified version', default_long=True)
@dataclass
class Upgrade:
    revision: Annotated[
        str,
        cappa.Arg(default='head', help='Target version, defaults to the latest version'),
    ]

    def __call__(self) -> None:
        run_alembic('upgrade', self.revision)
        console.print(f'Database upgraded to: {self.revision}', style='bold green')


@cappa.command(help='Downgrade the database to the specified version', default_long=True)
@dataclass
class Downgrade:
    revision: Annotated[
        str,
        cappa.Arg(default='-1', help='Target version, defaults to rolling back one version'),
    ]

    def __call__(self) -> None:
        run_alembic('downgrade', self.revision)
        console.print(f'Database downgraded to: {self.revision}', style='bold green')


@cappa.command(help="Show the database's current migration version")
@dataclass
class Current:
    verbose: Annotated[
        bool,
        cappa.Arg(short='-v', default=False, help='Show detailed information'),
    ]

    def __call__(self) -> None:
        args = ['current']
        if self.verbose:
            args.append('-v')
        run_alembic(*args)


@cappa.command(help='Show the migration history', default_long=True)
@dataclass
class History:
    verbose: Annotated[
        bool,
        cappa.Arg(short='-v', default=False, help='Show detailed information'),
    ]
    range: Annotated[
        str,
        cappa.Arg(short='-r', default='', help='Show history within the specified range, e.g. -r base:head'),
    ]

    def __call__(self) -> None:
        args = ['history']
        if self.verbose:
            args.append('-v')
        if self.range:
            args.extend(['-r', self.range])
        run_alembic(*args)


@cappa.command(help='Show all head revisions')
@dataclass
class Heads:
    verbose: Annotated[
        bool,
        cappa.Arg(short='-v', default=False, help='Show detailed information'),
    ]

    def __call__(self) -> None:
        args = ['heads']
        if self.verbose:
            args.append('-v')
        run_alembic(*args)


@cappa.command(help='Database migration management')
@dataclass
class Alembic:
    subcmd: cappa.Subcommands[Revision | Upgrade | Downgrade | Current | History | Heads]


@cappa.command(help='An efficient fba command-line interface', default_long=True)
@dataclass
class FbaCli:
    sql: Annotated[
        str,
        cappa.Arg(value_name='PATH', default='', show_default=False, help='Run a SQL script within a transaction'),
    ]
    subcmd: cappa.Subcommands[Init | Run | Add | Remove | Format | Celery | CodeGenerator | Alembic | None] = None

    async def __call__(self) -> None:
        if self.sql:
            async with async_db_session.begin() as db:
                await execute_sql_scripts(db, self.sql)


def main() -> None:
    output = cappa.Output(error_format=f'{error_format}\n{output_help}')
    asyncio.run(cappa.invoke_async(FbaCli, version=__version__, output=output))
