from typing import Annotated

from fastapi import APIRouter, Path, Query, Request

from backend.app.knowledge.crud.crud_knowledge_base import knowledge_base_dao
from backend.app.knowledge.crud.crud_project_knowledge_base import project_knowledge_base_dao
from backend.app.knowledge.schema.knowledge_base import GetKnowledgeBaseDetail
from backend.app.project.crud.crud_project import project_dao
from backend.common.exception import errors
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/{pid}/knowledge-bases', summary='项目绑定的知识库列表', dependencies=[DependsJwtAuth])
async def get_project_knowledge_bases(
    db: CurrentSession,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
) -> ResponseSchemaModel[list[GetKnowledgeBaseDetail]]:
    project = await project_dao.get(db, pid)
    if not project or project.owner_id != request.user.id:
        raise errors.NotFoundError(msg='项目不存在')
    bindings = await project_knowledge_base_dao.get_by_project(db, pid)
    items = []
    for b in bindings:
        kb = await knowledge_base_dao.get(db, b.knowledge_base_id)
        if kb and kb.user_id == request.user.id:
            items.append(GetKnowledgeBaseDetail.model_validate(kb))
    return response_base.success(data=items)


@router.post('/{pid}/knowledge-bases', summary='绑定知识库到项目', dependencies=[DependsJwtAuth])
async def bind_knowledge_base(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    kb_id: Annotated[int, Query(description='知识库 ID')],
) -> ResponseModel:
    project = await project_dao.get(db, pid)
    if not project or project.owner_id != request.user.id:
        raise errors.NotFoundError(msg='项目不存在')
    kb = await knowledge_base_dao.get(db, kb_id)
    if not kb or kb.user_id != request.user.id:
        raise errors.NotFoundError(msg='知识库不存在')
    existing = await project_knowledge_base_dao.get_binding(db, pid, kb_id)
    if existing:
        return response_base.success()
    await project_knowledge_base_dao.create(db, project_id=pid, knowledge_base_id=kb_id)
    return response_base.success()


@router.delete('/{pid}/knowledge-bases/{kb_id}', summary='解绑知识库', dependencies=[DependsJwtAuth])
async def unbind_knowledge_base(
    db: CurrentSessionTransaction,
    request: Request,
    pid: Annotated[int, Path(description='项目 ID')],
    kb_id: Annotated[int, Path(description='知识库 ID')],
) -> ResponseModel:
    project = await project_dao.get(db, pid)
    if not project or project.owner_id != request.user.id:
        raise errors.NotFoundError(msg='项目不存在')
    count = await project_knowledge_base_dao.delete_binding(db, project_id=pid, knowledge_base_id=kb_id)
    if count > 0:
        return response_base.success()
    return response_base.fail()
