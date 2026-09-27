from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from backend.app.agent.crud.crud_agent import agent_dao
from backend.app.agent.crud.crud_project_agent import project_agent_dao
from backend.app.agent.schema.agent import GetAgentDetail
from backend.app.project.crud.crud_project import project_dao
from backend.common.exception import errors
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/{pid}/agents', summary='List of agents bound to project', dependencies=[DependsJwtAuth])
async def get_project_agents(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
) -> ResponseSchemaModel[list[GetAgentDetail]]:
    project = await project_dao.get(db, pid)
    if not project or project.owner_id != request.user.id:
        raise errors.NotFoundError(msg='Project does not exist')
    bindings = await project_agent_dao.get_by_project(db, pid)
    items = []
    for b in bindings:
        agent = await agent_dao.get(db, b.agent_id)
        if agent:
            detail = GetAgentDetail.model_validate(agent)
            items.append(detail)
    return response_base.success(data=items)


@router.post('/{pid}/agents', summary='Bind agent to project', dependencies=[DependsJwtAuth])
async def bind_agent(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    agent_id: Annotated[int, Query(description='Agent ID')],
) -> ResponseModel:
    project = await project_dao.get(db, pid)
    if not project or project.owner_id != request.user.id:
        raise errors.NotFoundError(msg='Project does not exist')
    agent = await agent_dao.get(db, agent_id)
    if not agent or agent.user_id != request.user.id:
        raise errors.NotFoundError(msg='Agent does not exist')
    existing = await project_agent_dao.get_binding(db, pid, agent_id)
    if existing:
        return response_base.success()
    await project_agent_dao.create(db, project_id=pid, agent_id=agent_id)
    return response_base.success()


@router.delete('/{pid}/agents/{agent_id}', summary='Unbind agent', dependencies=[DependsJwtAuth])
async def unbind_agent(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='Project ID')],
    agent_id: Annotated[int, Path(description='Agent ID')],
) -> ResponseModel:
    project = await project_dao.get(db, pid)
    if not project or project.owner_id != request.user.id:
        raise errors.NotFoundError(msg='Project does not exist')
    count = await project_agent_dao.delete_binding(db, project_id=pid, agent_id=agent_id)
    if count > 0:
        return response_base.success()
    return response_base.fail()
