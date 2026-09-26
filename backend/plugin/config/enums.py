from backend.common.enums import StrEnum


class ConfigType(StrEnum):
    """Config type"""

    email = 'EMAIL'
    user_security = 'USER_SECURITY'
    login = 'LOGIN'
