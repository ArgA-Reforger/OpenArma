from pathlib import Path

# Project root directory
BASE_PATH = Path(__file__).resolve().parent.parent

# Environment variable file
ENV_FILE_PATH = BASE_PATH / '.env'

# Environment variable example file
ENV_EXAMPLE_FILE_PATH = BASE_PATH / '.env.example'

# alembic migration file directory
ALEMBIC_VERSION_DIR = BASE_PATH / 'alembic' / 'versions'

# Log file path
LOG_DIR = BASE_PATH / 'log'

# Static resource directory
STATIC_DIR = BASE_PATH / 'static'

# Upload file directory
UPLOAD_DIR = STATIC_DIR / 'upload'

# Plugin directory
PLUGIN_DIR = BASE_PATH / 'plugin'

# Internationalization file directory
LOCALE_DIR = BASE_PATH / 'locale'

# MySQL script directory
MYSQL_SCRIPT_DIR = BASE_PATH / 'sql' / 'mysql'

# PostgreSQL script directory
POSTGRESQL_SCRIPT_DIR = BASE_PATH / 'sql' / 'postgresql'

# Hot reload lock file
RELOAD_LOCK_FILE = BASE_PATH / '.reload.lock'
