import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class UsageRecord(Base):
    """Usage records table"""

    __tablename__ = 'oa_usage_record'

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, index=True, comment='User ID')
    provider_type: Mapped[str] = mapped_column(sa.String(32), comment='Provider type openai/deepseek/anthropic')
    model_name: Mapped[str] = mapped_column(sa.String(128), comment='Model name')
    project_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, index=True, comment='Project ID')
    conversation_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='Conversation ID')
    agent_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='Agent ID')
    llm_provider_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='LLM provider ID')
    prompt_tokens: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Input token count')
    completion_tokens: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Output token count')
    total_tokens: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Total token count')
    cached_tokens: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Cache hit token count')
    reasoning_tokens: Mapped[int] = mapped_column(sa.Integer, default=0, comment='Reasoning token count')
    estimated_cost: Mapped[float] = mapped_column(sa.Float, default=0.0, comment='Estimated cost')
    call_type: Mapped[str] = mapped_column(sa.String(32), default='chat', comment='Call type chat/title_gen/rag_embed')
    status: Mapped[str] = mapped_column(sa.String(16), default='success', comment='Call status success/failed/partial')
    error_message: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='Error message')
    duration_ms: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='Call duration (ms)')
    metadata_: Mapped[dict | None] = mapped_column('metadata', sa.JSON(), default=None, comment='Extra metadata')
