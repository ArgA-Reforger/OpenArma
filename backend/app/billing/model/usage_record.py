import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, id_key


class UsageRecord(Base):
    """用量记录表"""

    __tablename__ = 'oa_usage_record'

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, index=True, comment='用户 ID')
    provider_type: Mapped[str] = mapped_column(sa.String(32), comment='服务商类型 openai/deepseek/anthropic')
    model_name: Mapped[str] = mapped_column(sa.String(128), comment='模型名称')
    project_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, index=True, comment='项目 ID')
    conversation_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='对话 ID')
    agent_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='智能体 ID')
    llm_provider_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='LLM 服务商 ID')
    prompt_tokens: Mapped[int] = mapped_column(sa.Integer, default=0, comment='输入 token 数')
    completion_tokens: Mapped[int] = mapped_column(sa.Integer, default=0, comment='输出 token 数')
    total_tokens: Mapped[int] = mapped_column(sa.Integer, default=0, comment='总 token 数')
    cached_tokens: Mapped[int] = mapped_column(sa.Integer, default=0, comment='缓存命中 token 数')
    reasoning_tokens: Mapped[int] = mapped_column(sa.Integer, default=0, comment='推理 token 数')
    estimated_cost: Mapped[float] = mapped_column(sa.Float, default=0.0, comment='预估费用')
    call_type: Mapped[str] = mapped_column(sa.String(32), default='chat', comment='调用类型 chat/title_gen/rag_embed')
    status: Mapped[str] = mapped_column(sa.String(16), default='success', comment='调用状态 success/failed/partial')
    error_message: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='错误信息')
    duration_ms: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='调用耗时(毫秒)')
    metadata_: Mapped[dict | None] = mapped_column('metadata', sa.JSON(), default=None, comment='额外信息')
