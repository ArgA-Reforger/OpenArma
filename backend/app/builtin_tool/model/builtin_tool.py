import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, id_key


class BuiltinTool(Base, SoftDeleteMixin):
    """内置工具表"""

    __tablename__ = 'oa_builtin_tool'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(64), unique=True, comment='工具标识名')
    display_name: Mapped[str] = mapped_column(sa.String(128), comment='显示名称')
    description: Mapped[str] = mapped_column(sa.String(1024), comment='工具描述（给 LLM 看）')
    input_schema: Mapped[dict] = mapped_column(sa.JSON(), default=dict, comment='输入参数 JSON Schema')
    handler_type: Mapped[str] = mapped_column(sa.String(32), default='python_builtin', comment='执行器类型 python_builtin/http_webhook')
    handler_config: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='执行器配置')
    category: Mapped[str] = mapped_column(sa.String(32), default='general', comment='工具分类 general/arma/...')
    is_system: Mapped[bool] = mapped_column(sa.Boolean, default=False, comment='是否系统预置（不可删除）')
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, comment='是否启用')
