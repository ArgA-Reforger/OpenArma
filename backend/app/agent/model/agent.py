import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from backend.common.model import Base, SoftDeleteMixin, UniversalText, id_key


class Agent(Base, SoftDeleteMixin):
    __tablename__ = 'oa_agent'

    id: Mapped[id_key] = mapped_column(init=False)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, comment='所有者 ID')
    name: Mapped[str] = mapped_column(sa.String(128), comment='Agent 名称')
    description: Mapped[str | None] = mapped_column(sa.String(512), default=None, comment='描述')
    system_prompt: Mapped[str | None] = mapped_column(UniversalText, default=None, comment='系统提示词')
    rules: Mapped[dict | list | None] = mapped_column(sa.JSON(), default=None, comment='规则')
    skills: Mapped[dict | list | None] = mapped_column(sa.JSON(), default=None, comment='技能')
    llm_provider_id: Mapped[int | None] = mapped_column(sa.BigInteger, default=None, comment='LLM 提供商 ID')
    model_name: Mapped[str | None] = mapped_column(sa.String(128), default=None, comment='模型名称')
    temperature: Mapped[float] = mapped_column(sa.Float, default=0.7, comment='温度')
    top_p: Mapped[float | None] = mapped_column(sa.Float, default=None, comment='Top P')
    max_tokens: Mapped[int | None] = mapped_column(sa.Integer, default=None, comment='最大 token 数')
    presence_penalty: Mapped[float | None] = mapped_column(sa.Float, default=None, comment='存在惩罚')
    frequency_penalty: Mapped[float | None] = mapped_column(sa.Float, default=None, comment='频率惩罚')
    is_default: Mapped[bool] = mapped_column(sa.Boolean, default=False, comment='是否为用户默认 Agent')
    sort_order: Mapped[int] = mapped_column(sa.Integer, default=0, comment='排序')
    visibility: Mapped[str] = mapped_column(sa.String(16), default='private', comment='可见性 private/public/official')
    builtin_tools: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='内置工具配置')
    enable_sub_agents: Mapped[bool] = mapped_column(sa.Boolean, default=False, comment='允许动态生成子代理')
