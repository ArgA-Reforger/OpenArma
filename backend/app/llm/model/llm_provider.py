import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, id_key


class LLMProvider(Base, SoftDeleteMixin):
    """LLM 服务商表"""

    __tablename__ = 'oa_llm_provider'

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, comment='用户 ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='服务商名称')
    provider_type: Mapped[str] = mapped_column(sa.String(32), comment='服务商类型')
    api_base: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='API 基础地址')
    api_key_encrypted: Mapped[str | None] = mapped_column(sa.String(1024), default=None, comment='加密后的 API Key')
    models: Mapped[list | None] = mapped_column(sa.JSON(), default=None, comment='可用模型列表')
    rpm_limit: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='每分钟请求数上限（null=不限制）')
    tpm_limit: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='每分钟 Token 数上限（null=不限制）')
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, comment='是否启用')
    visibility: Mapped[str] = mapped_column(sa.String(16), default='private', comment='可见性 private/public/official')
