from backend.common.enums import StrEnum


class UserSocialType(StrEnum):
    """User social type"""

    github = 'Github'
    google = 'Google'


class UserSocialAuthType(StrEnum):
    """User social auth type"""

    login = 'login'
    binding = 'binding'
