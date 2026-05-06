from typing import Annotated

from fastapi import APIRouter, File, Form, Path, Request, UploadFile

from backend.app.knowledge.schema.knowledge_document import GetKnowledgeDocumentDetail
from backend.app.knowledge.service.knowledge_document_service import knowledge_document_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.post('/{kb_id}/documents', summary='上传文档', dependencies=[DependsJwtAuth])
async def upload_document(
    db: CurrentSessionTransaction,
    request: Request,
    kb_id: Annotated[int, Path(description='知识库 ID')],
    file: Annotated[UploadFile | None, File(description='上传文件')] = None,
    title: Annotated[str | None, Form(description='文档标题')] = None,
    source_type: Annotated[str, Form(description='来源类型 upload/url/text')] = 'upload',
    content: Annotated[str | None, Form(description='文本内容(text类型)')] = None,
    url: Annotated[str | None, Form(description='URL 地址(url类型)')] = None,
) -> ResponseSchemaModel[GetKnowledgeDocumentDetail]:
    data = await knowledge_document_service.upload(
        db=db,
        kb_id=kb_id,
        owner_id=request.user.id,
        file=file,
        title=title,
        source_type=source_type,
        content=content,
        url=url,
    )
    return response_base.success(data=data)


@router.get(
    '/{kb_id}/documents',
    summary='文档列表',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_documents(
    db: CurrentSession,
    request: Request,
    kb_id: Annotated[int, Path(description='知识库 ID')],
) -> ResponseSchemaModel[PageData[GetKnowledgeDocumentDetail]]:
    page_data = await knowledge_document_service.get_list(db=db, kb_id=kb_id, owner_id=request.user.id)
    return response_base.success(data=page_data)


@router.get('/{kb_id}/documents/{doc_id}', summary='文档详情', dependencies=[DependsJwtAuth])
async def get_document(
    db: CurrentSession,
    request: Request,
    kb_id: Annotated[int, Path(description='知识库 ID')],
    doc_id: Annotated[int, Path(description='文档 ID')],
) -> ResponseSchemaModel[GetKnowledgeDocumentDetail]:
    data = await knowledge_document_service.get(db=db, kb_id=kb_id, doc_id=doc_id, owner_id=request.user.id)
    return response_base.success(data=data)


@router.delete('/{kb_id}/documents/{doc_id}', summary='删除文档', dependencies=[DependsJwtAuth])
async def delete_document(
    db: CurrentSessionTransaction,
    request: Request,
    kb_id: Annotated[int, Path(description='知识库 ID')],
    doc_id: Annotated[int, Path(description='文档 ID')],
) -> ResponseModel:
    count = await knowledge_document_service.delete(db=db, kb_id=kb_id, doc_id=doc_id, owner_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/{kb_id}/documents/{doc_id}/reprocess', summary='重新处理文档', dependencies=[DependsJwtAuth])
async def reprocess_document(
    db: CurrentSessionTransaction,
    request: Request,
    kb_id: Annotated[int, Path(description='知识库 ID')],
    doc_id: Annotated[int, Path(description='文档 ID')],
) -> ResponseModel:
    count = await knowledge_document_service.reprocess(db=db, kb_id=kb_id, doc_id=doc_id, owner_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()
