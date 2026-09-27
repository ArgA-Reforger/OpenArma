import shutil

from functools import cache
from re import Pattern
from typing import Any, Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from backend.core.path_conf import ENV_EXAMPLE_FILE_PATH, ENV_FILE_PATH
from backend.plugin.settings_source import PluginSettingsSource


class Settings(BaseSettings):
    """Global configuration"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE_PATH,
        env_file_encoding='utf-8',
        extra='allow',
        case_sensitive=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize the configuration source priority"""
        return env_settings, dotenv_settings, PluginSettingsSource(settings_cls)

    # .env current environment
    ENVIRONMENT: Literal['dev', 'prod']

    # FastAPI
    FASTAPI_API_V1_PATH: str = '/api/v1'
    FASTAPI_TITLE: str = 'fba'
    FASTAPI_DESCRIPTION: str = 'FastAPI Best Architecture'
    FASTAPI_DOCS_URL: str = '/docs'
    FASTAPI_REDOC_URL: str = '/redoc'
    FASTAPI_OPENAPI_URL: str | None = '/openapi'
    FASTAPI_STATIC_FILES: bool = True

    # .env database
    DATABASE_TYPE: Literal['mysql', 'postgresql']
    DATABASE_HOST: str
    DATABASE_PORT: int
    DATABASE_USER: str
    DATABASE_PASSWORD: str

    # Database
    DATABASE_ECHO: bool | Literal['debug'] = False
    DATABASE_POOL_ECHO: bool | Literal['debug'] = False
    DATABASE_SCHEMA: str = 'openarma'
    DATABASE_CHARSET: str = 'utf8mb4'
    DATABASE_PK_MODE: Literal['autoincrement', 'snowflake'] = 'snowflake'

    # .env Redis
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str
    REDIS_DATABASE: int

    # Redis
    REDIS_TIMEOUT: int = 5

    # Cache
    CACHE_LOCAL_ENABLED: bool = True
    CACHE_LOCAL_MAXSIZE: int = 100000
    CACHE_LOCAL_TTL: int = 60 * 60 * 2  # 2 hours
    CACHE_REDIS_TTL: int = 60 * 60 * 2  # 2 hours
    CACHE_CONFIG_REDIS_PREFIX: str = 'fba:cache:config'
    CACHE_DICT_REDIS_PREFIX: str = 'fba:cache:dict'
    CACHE_PUBSUB_CHANNEL: str = 'fba:cache:invalidate'
    CACHE_PUBSUB_RECONNECT_DELAY: int = 5  # reconnect delay (seconds)
    CACHE_PUBSUB_MAX_RECONNECT_ATTEMPTS: int = 10  # maximum reconnect attempts

    # .env Snowflake
    SNOWFLAKE_DATACENTER_ID: int | None = None
    SNOWFLAKE_WORKER_ID: int | None = None

    # Snowflake
    SNOWFLAKE_REDIS_PREFIX: str = 'fba:snowflake'
    SNOWFLAKE_HEARTBEAT_INTERVAL_SECONDS: int = 30
    SNOWFLAKE_NODE_TTL_SECONDS: int = 60

    # .env Token
    TOKEN_SECRET_KEY: str  # secret key secrets.token_urlsafe(32)

    # Token
    TOKEN_ALGORITHM: str = 'HS256'
    TOKEN_EXPIRE_SECONDS: int = 60 * 60 * 24  # 1 day
    TOKEN_REFRESH_EXPIRE_SECONDS: int = 60 * 60 * 24 * 7  # 7 days
    TOKEN_REDIS_PREFIX: str = 'fba:token'
    TOKEN_EXTRA_INFO_REDIS_PREFIX: str = 'fba:token_extra_info'
    TOKEN_ONLINE_REDIS_PREFIX: str = 'fba:token_online'
    TOKEN_REFRESH_REDIS_PREFIX: str = 'fba:refresh_token'
    TOKEN_REQUEST_PATH_EXCLUDE: list[str] = [  # JWT / RBAC route whitelist
        f'{FASTAPI_API_V1_PATH}/auth/login',
    ]
    TOKEN_REQUEST_PATH_EXCLUDE_PATTERN: list[Pattern[str]] = [  # JWT / RBAC route whitelist (regex)
        rf'^{FASTAPI_API_V1_PATH}/monitors/(redis|server)$',
        rf'^{FASTAPI_API_V1_PATH}/open/command$',
    ]

    # User security
    USER_LOCK_REDIS_PREFIX: str = 'fba:user:lock'
    USER_LOCK_THRESHOLD: int = 5  # User password failure lock threshold, 0 disables locking
    USER_LOCK_SECONDS: int = 60 * 5  # 5 minutes
    USER_PASSWORD_EXPIRY_DAYS: int = 365  # User password validity period, 0 means never expires
    USER_PASSWORD_REMINDER_DAYS: int = 7  # User password expiry reminder, 0 means no reminder
    USER_PASSWORD_HISTORY_CHECK_COUNT: int = 3
    USER_PASSWORD_MIN_LENGTH: int = 6
    USER_PASSWORD_MAX_LENGTH: int = 32
    USER_PASSWORD_REQUIRE_SPECIAL_CHAR: bool = False

    # Login
    LOGIN_CAPTCHA_ENABLED: bool = True
    LOGIN_CAPTCHA_REDIS_PREFIX: str = 'fba:login:captcha'
    LOGIN_CAPTCHA_EXPIRE_SECONDS: int = 60 * 5  # 5 minutes
    LOGIN_FAILURE_PREFIX: str = 'fba:login:failure'

    # JWT
    JWT_USER_REDIS_PREFIX: str = 'fba:user'

    # RBAC
    RBAC_ROLE_MENU_MODE: bool = True
    RBAC_ROLE_MENU_EXCLUDE: list[str] = [
        'sys:monitor:redis',
        'sys:monitor:server',
    ]

    # Cookie
    COOKIE_REFRESH_TOKEN_KEY: str = 'fba_refresh_token'
    COOKIE_REFRESH_TOKEN_EXPIRE_SECONDS: int = 60 * 60 * 24 * 7  # 7 days

    # Data permissions
    DATA_PERMISSION_MODEL_EXCLUDE: list[str] = [  # SQLA models excluded from data filtering
        'DataScope',
        'DataRule',
        'sys_role_data_scope',
        'sys_data_scope_rule',
    ]
    DATA_PERMISSION_COLUMN_EXCLUDE: list[str] = [  # SQLA model columns excluded from data filtering
        'id',
        'sort',
        'del_flag',
        'created_time',
        'updated_time',
    ]
    # Template variables available for data rule models
    DATA_PERMISSION_MODEL_TEMPLATE_VARIABLES: list[dict[str, str]] = [
        {'key': '__ALL__', 'comment': 'All models'},
    ]
    # Template variables available for data rule columns
    DATA_PERMISSION_COLUMN_TEMPLATE_VARIABLES: list[dict[str, str]] = [
        {'key': '__dept_id__', 'comment': 'Department ID'},
        {'key': '__created_by__', 'comment': 'Creator'},
    ]
    DATA_PERMISSION_TEMPLATE_VARIABLES: list[dict[str, str]] = [  # Template variables available for data rule values
        {'key': '${user_id}', 'comment': 'Current logged-in user ID'},
        {'key': '${dept_id}', 'comment': "Current logged-in user's department ID"},
        {'key': '${now}', 'comment': 'Current time'},
    ]

    # Socket.IO
    WS_NO_AUTH_MARKER: str = 'internal'

    # CORS
    CORS_ALLOWED_ORIGINS: list[str] = [  # No trailing slash
        'http://127.0.0.1',
        'http://localhost:3000',
        'http://localhost:23000',
        'http://127.0.0.1:23000',
        'http://localhost:5173',
        'https://openarma.com',
        'http://openarma.com',
    ]
    CORS_EXPOSE_HEADERS: list[str] = [
        'X-Request-ID',
    ]

    # Middleware configuration
    MIDDLEWARE_CORS: bool = True

    # Request limiter configuration
    REQUEST_LIMITER_REDIS_PREFIX: str = 'fba:limiter'

    # Time configuration
    DATETIME_TIMEZONE: str = 'Asia/Shanghai'
    DATETIME_FORMAT: str = '%Y-%m-%d %H:%M:%S'

    # File upload
    UPLOAD_READ_SIZE: int = 1024
    UPLOAD_IMAGE_EXT_INCLUDE: list[str] = ['jpg', 'jpeg', 'png', 'gif', 'webp']
    UPLOAD_IMAGE_SIZE_MAX: int = 5 * 1024 * 1024  # 5 MB
    UPLOAD_VIDEO_EXT_INCLUDE: list[str] = ['mp4', 'mov', 'avi', 'flv']
    UPLOAD_VIDEO_SIZE_MAX: int = 20 * 1024 * 1024  # 20 MB

    # Demo mode configuration
    DEMO_MODE: bool = False
    DEMO_MODE_EXCLUDE: set[tuple[str, str]] = {
        ('POST', f'{FASTAPI_API_V1_PATH}/auth/login'),
        ('POST', f'{FASTAPI_API_V1_PATH}/auth/logout'),
        ('GET', f'{FASTAPI_API_V1_PATH}/auth/captcha'),
        ('POST', f'{FASTAPI_API_V1_PATH}/auth/refresh'),
    }

    # IP location configuration
    # 'online' queries ip-api.com (Spanish place names) over plain HTTP, so client IPs
    # leave the server; the free tier is rate-limited (~45 req/min). 'offline' uses the
    # bundled ip2region database, which only returns Chinese names. 'false' disables it.
    IP_LOCATION_PARSE: Literal['online', 'offline', 'false'] = 'online'
    IP_LOCATION_REDIS_PREFIX: str = 'fba:ip:location'
    IP_LOCATION_EXPIRE_SECONDS: int = 60 * 60 * 24  # 1 day
    IP_LOCATION_FAILURE_EXPIRE_SECONDS: int = 60 * 5  # failed online lookups are retried after 5 minutes

    # Trace ID
    TRACE_ID_REQUEST_HEADER_KEY: str = 'X-Request-ID'
    TRACE_ID_LOG_LENGTH: int = 32  # UUID length, must be <= 32
    TRACE_ID_LOG_DEFAULT_VALUE: str = '-'

    # Log
    LOG_FORMAT: str = (
        '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</> | <lvl>{level: <8}</> | <cyan>{request_id}</> | <lvl>{message}</>'
    )

    # Log (console)
    LOG_STD_LEVEL: str = 'INFO'

    # Log (file)
    LOG_FILE_ACCESS_LEVEL: str = 'INFO'
    LOG_FILE_ERROR_LEVEL: str = 'ERROR'
    LOG_ACCESS_FILENAME: str = 'fba_access.log'
    LOG_ERROR_FILENAME: str = 'fba_error.log'

    # Operation log
    OPERA_LOG_PATH_EXCLUDE: list[str] = [
        '/favicon.ico',
        '/docs',
        '/redoc',
        '/openapi',
        f'{FASTAPI_API_V1_PATH}/auth/login/swagger',
        f'{FASTAPI_API_V1_PATH}/oauth2/github/callback',
        f'{FASTAPI_API_V1_PATH}/oauth2/google/callback',
    ]
    OPERA_LOG_REDACT_KEYS: list[str] = [
        'password',
        'old_password',
        'new_password',
        'confirm_password',
    ]
    OPERA_LOG_QUEUE_MAXSIZE: int = 100000
    OPERA_LOG_QUEUE_BATCH_CONSUME_SIZE: int = 100
    OPERA_LOG_QUEUE_TIMEOUT: int = 60  # 1 minute

    # Plugin configuration
    PLUGIN_PIP_CHINA: bool = False  # When True, plugin installs use PLUGIN_PIP_INDEX_URL as the package index
    PLUGIN_PIP_INDEX_URL: str = 'https://pypi.org/simple/'
    PLUGIN_PIP_MAX_RETRY: int = 3
    PLUGIN_REDIS_PREFIX: str = 'fba:plugin'

    # I18n configuration
    I18N_DEFAULT_LANGUAGE: str = 'es-ES'

    # Grafana
    GRAFANA_METRICS_ENABLE: bool = False
    GRAFANA_OTLP_GRPC_ENDPOINT: str = 'fba_alloy:4317'

    ##################################################
    # [ OpenArma ] Qdrant
    ##################################################
    QDRANT_HOST: str = '127.0.0.1'
    QDRANT_PORT: int = 6333
    QDRANT_API_KEY: str = ''

    ##################################################
    # [ OpenArma ] MinIO
    ##################################################
    MINIO_ENDPOINT: str = '127.0.0.1:9000'
    MINIO_ACCESS_KEY: str = 'minioadmin'
    MINIO_SECRET_KEY: str = 'minioadmin'
    MINIO_BUCKET: str = 'openarma'
    MINIO_SECURE: bool = False

    ##################################################
    # [ OpenArma ] Built-in Tools
    ##################################################
    TAVILY_API_KEY: str = ''
    WEB_SEARCH_PROVIDER: str = 'auto'

    ##################################################
    # [ App ] task
    ##################################################
    # .env Redis
    CELERY_BROKER_REDIS_DATABASE: int

    # .env RabbitMQ
    # docker run -d --hostname fba-mq --name fba-mq  -p 5672:5672 -p 15672:15672 rabbitmq:latest
    CELERY_RABBITMQ_HOST: str
    CELERY_RABBITMQ_PORT: int
    CELERY_RABBITMQ_USERNAME: str
    CELERY_RABBITMQ_PASSWORD: str

    # Base configuration
    CELERY_BROKER: Literal['rabbitmq', 'redis'] = 'redis'
    CELERY_RABBITMQ_VHOST: str = ''
    CELERY_REDIS_PREFIX: str = 'fba:celery'
    CELERY_TASK_MAX_RETRIES: int = 5

    ##################################################
    # [ Plugin ] code_generator
    ##################################################
    CODE_GENERATOR_DOWNLOAD_ZIP_FILENAME: str

    ##################################################
    # [ Plugin ] oauth2
    ##################################################
    # .env
    OAUTH2_GITHUB_CLIENT_ID: str
    OAUTH2_GITHUB_CLIENT_SECRET: str
    OAUTH2_GOOGLE_CLIENT_ID: str
    OAUTH2_GOOGLE_CLIENT_SECRET: str

    # Base configuration (in plugin.toml)
    OAUTH2_STATE_REDIS_PREFIX: str
    OAUTH2_STATE_EXPIRE_SECONDS: int
    OAUTH2_GITHUB_REDIRECT_URI: str
    OAUTH2_GOOGLE_REDIRECT_URI: str
    OAUTH2_FRONTEND_LOGIN_REDIRECT_URI: str
    OAUTH2_FRONTEND_BINDING_REDIRECT_URI: str

    ##################################################
    # [ Plugin ] email
    ##################################################
    # .env
    EMAIL_USERNAME: str
    EMAIL_PASSWORD: str

    # Base configuration (in plugin.toml)
    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_SSL: bool
    EMAIL_CAPTCHA_REDIS_PREFIX: str
    EMAIL_CAPTCHA_EXPIRE_SECONDS: int

    @model_validator(mode='before')
    @classmethod
    def check_env(cls, values: Any) -> Any:
        """Check environment variables"""
        if values.get('ENVIRONMENT') == 'prod':
            # FastAPI
            values['FASTAPI_OPENAPI_URL'] = None
            values['FASTAPI_STATIC_FILES'] = False

            # task
            values['CELERY_BROKER'] = 'rabbitmq'

            # Grafana
            values['GRAFANA_METRICS_ENABLE'] = True

        return values


@cache
def get_settings() -> Settings:
    """Get the global configuration singleton"""
    if not ENV_FILE_PATH.exists():
        shutil.copy(ENV_EXAMPLE_FILE_PATH, ENV_FILE_PATH)
    return Settings()


# Create the global configuration instance
settings = get_settings()
