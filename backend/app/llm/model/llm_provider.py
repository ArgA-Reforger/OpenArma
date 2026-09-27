import sqlalchemy as sa

from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, id_key


class LLMProvider(Base, SoftDeleteMixin):
    """LLM providers table"""

    __tablename__ = 'oa_llm_provider'

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, comment='User ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='Provider name')
    provider_type: Mapped[str] = mapped_column(sa.String(32), comment='Provider type')
    api_base: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='API base URL')
    api_key_encrypted: Mapped[str | None] = mapped_column(sa.String(1024), default=None, comment='Encrypted API key')
    models: Mapped[list | None] = mapped_column(sa.JSON(), default=None, comment='Available model list')
    rpm_limit: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='RPM limit (null = unlimited)')
    tpm_limit: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='TPM limit (null = unlimited)')
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, comment='Whether enabled')
    visibility: Mapped[str] = mapped_column(sa.String(16), default='private', comment='Visibility private/public/official')
