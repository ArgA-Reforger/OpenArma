from typing import Annotated

from fastapi import APIRouter, Path, Request
from pydantic import BaseModel, Field

from backend.app.conversation.engine.graph_builder import validate_topology
from backend.common.response.response_schema import ResponseModel, response_base
from backend.common.security.jwt import DependsJwtAuth

router = APIRouter()


class TopologyPayload(BaseModel):
    topology: dict = Field(description='DAG topology JSON')


@router.post(
    '/topologies/validate',
    summary='验证拓扑配置',
    dependencies=[DependsJwtAuth],
)
async def validate_topology_endpoint(
    request: Request,
    body: TopologyPayload,
) -> ResponseModel:
    validation_errors = validate_topology(body.topology)
    return response_base.success(data={'valid': len(validation_errors) == 0, 'errors': validation_errors})
