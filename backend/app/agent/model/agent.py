import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from backend.common.model import Base, SoftDeleteMixin, UniversalText, id_key


class Agent(Base, SoftDeleteMixin):
    __tablename__ = 'oa_agent'

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, comment='Owner ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='Agent name')
    description: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='Description')
    system_prompt: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='System prompt')
    rules: Mapped[dict | list | None] = mapped_column(sa.JSON(), default=None, comment='Rules')
    skills: Mapped[dict | list | None] = mapped_column(sa.JSON(), default=None, comment='Skills')
    llm_provider_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='LLM provider ID')
    model_name: Mapped[str | None] = mapped_column(sa.String(128), default=None, comment='Model name')
    temperature: Mapped[float] = mapped_column(sa.Float, default=0.7, comment='Temperature')
    top_p: Mapped[float | None] = mapped_column(sa.Float, default=None, comment='Top P')
    max_tokens: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Max token count')
    presence_penalty: Mapped[float | None] = mapped_column(sa.Float, default=None, comment='Presence penalty')
    frequency_penalty: Mapped[float | None] = mapped_column(sa.Float, default=None, comment='Frequency penalty')
    is_default: Mapped[bool] = mapped_column(sa.Boolean, default=False, comment='Whether user default agent')
    sort_order: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Sort order')
    visibility: Mapped[str] = mapped_column(
        sa.String(16), default='private', comment='Visibility private/public/official'
    )
    builtin_tools: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='Builtin tools configuration')
    enable_sub_agents: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, comment='Allow dynamic sub-agent generation'
    )
