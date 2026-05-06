from fastapi import APIRouter

from backend.app.admin.api.router import v1 as admin_v1
from backend.app.agent.api.router import v1 as agent_v1
from backend.app.billing.api.router import v1 as billing_v1
from backend.app.builtin_tool.api.router import v1 as builtin_tool_v1
from backend.app.conversation.api.router import v1 as conversation_v1
from backend.app.knowledge.api.router import v1 as knowledge_v1
from backend.app.llm.api.router import v1 as llm_v1
from backend.app.map.api.router import v1 as map_v1
from backend.app.mcp.api.router import v1 as mcp_v1
from backend.app.open.api.router import v1 as open_v1
from backend.app.project.api.router import v1 as project_v1
from backend.app.showcase.api.router import v1 as showcase_v1
from backend.app.task.api.router import v1 as task_v1
from backend.app.topology.api.router import v1 as topology_v1

router = APIRouter()

router.include_router(admin_v1)
router.include_router(agent_v1)
router.include_router(billing_v1)
router.include_router(builtin_tool_v1)
router.include_router(conversation_v1)
router.include_router(knowledge_v1)
router.include_router(llm_v1)
router.include_router(map_v1)
router.include_router(mcp_v1)
router.include_router(open_v1)
router.include_router(project_v1)
router.include_router(showcase_v1)
router.include_router(task_v1)
router.include_router(topology_v1)
