from pydantic import Field

from backend.common.schema import SchemaBase


class GetCaptchaDetail(SchemaBase):
    """Captcha detail"""

    is_enabled: bool = Field(description='Whether enabled')
    expire_seconds: int = Field(description='Expiry in seconds')
    uuid: str = Field(description='Unique image identifier')
    image: str = Field(description='Image content')
