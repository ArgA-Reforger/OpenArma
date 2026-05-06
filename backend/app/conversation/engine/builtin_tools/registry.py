"""内置工具注册表：管理所有平台内置工具的定义和执行器。"""

import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

ToolHandler = Callable[..., Coroutine[Any, Any, str]]


@dataclass
class BuiltinToolDef:
    """内置工具的运行时定义。"""

    name: str
    description: str
    input_schema: dict
    handler: ToolHandler
    display_name: str = ''


class BuiltinToolRegistry:
    """
    内置工具注册表。

    系统启动时注册所有内置工具处理函数。
    运行时根据 Agent 的 builtin_tools 配置，
    筛选出启用的工具并构建 tools + handlers 供图引擎使用。
    """

    def __init__(self) -> None:
        self._tools: dict[str, BuiltinToolDef] = {}

    def register(
        self,
        name: str,
        *,
        description: str,
        input_schema: dict,
        display_name: str = '',
    ) -> Callable[[ToolHandler], ToolHandler]:
        """装饰器：注册一个内置工具处理函数。"""
        def decorator(func: ToolHandler) -> ToolHandler:
            self._tools[name] = BuiltinToolDef(
                name=name,
                description=description,
                input_schema=input_schema,
                handler=func,
                display_name=display_name or name,
            )
            return func
        return decorator

    def get_all(self) -> dict[str, BuiltinToolDef]:
        return dict(self._tools)

    def get(self, name: str) -> BuiltinToolDef | None:
        return self._tools.get(name)

    def build_tools_for_agent(
        self,
        builtin_tools_config: dict | None,
        *,
        context: dict | None = None,
    ) -> tuple[list[dict], dict[str, ToolHandler]]:
        """
        根据 Agent 的 builtin_tools 配置，构建 OpenAI tools 列表和 handler 映射。

        :param builtin_tools_config: Agent.builtin_tools JSON, e.g. {"web_search": {"enabled": true}, ...}
        :param context: 运行时上下文，供 ChatService 后续绑定具体参数
        :return: (tools_list, handlers_dict)
        """
        if not builtin_tools_config:
            return [], {}

        tools: list[dict] = []
        handlers: dict[str, ToolHandler] = {}

        for tool_name, tool_cfg in builtin_tools_config.items():
            if not isinstance(tool_cfg, dict) or not tool_cfg.get('enabled'):
                continue

            tool_def = self._tools.get(tool_name)
            if not tool_def:
                log.warning(f'Builtin tool not registered: {tool_name}')
                continue

            tools.append({
                'name': tool_def.name,
                'description': tool_def.description,
                'input_schema': tool_def.input_schema,
            })
            handlers[tool_def.name] = tool_def.handler

        return tools, handlers


builtin_registry = BuiltinToolRegistry()
