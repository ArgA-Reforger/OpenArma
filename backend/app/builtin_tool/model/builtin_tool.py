import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from backend.common.model import Base, SoftDeleteMixin, id_key


class BuiltinTool(Base, SoftDeleteMixin):
    """Builtin tools table"""

    __tablename__ = 'oa_builtin_tool'

    id: Mapped[id_key] = mapped_column(init=False)
    name: Mapped[str] = mapped_column(sa.String(64), unique=True, comment='Tool identifier name')
    display_name: Mapped[str] = mapped_column(sa.String(128), comment='Display name')
    description: Mapped[str] = mapped_column(sa.String(1024), comment='Tool description (for LLM)')
    input_schema: Mapped[dict] = mapped_column(sa.JSON(), default=dict, comment='Input parameters JSON Schema')
    handler_type: Mapped[str] = mapped_column(
        sa.String(32), default='python_builtin', comment='Handler type python_builtin/http_webhook'
    )
    handler_config: Mapped[dict | None] = mapped_column(sa.JSON(), default=None, comment='Handler config')
    category: Mapped[str] = mapped_column(sa.String(32), default='general', comment='Tool category general/arma/...')
    is_system: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, comment='Whether system preset (cannot be deleted)'
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, comment='Whether enabled')
