from typing import Annotated

from fastapi import APIRouter, File, Form, Path, Request, UploadFile

from backend.app.knowledge.schema.knowledge_document import GetKnowledgeDocumentDetail
from backend.app.knowledge.service.knowledge_document_service import knowledge_document_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.post('/{kb_id}/documents', summary='Upload document', dependencies=[DependsJwtAuth])
async def upload_document(
    db: CurrentSessionTransaction,
    request: Request,
    kb_id: Annotated[int, Path(description='Knowledge base ID')],
    file: Annotated[UploadFile | None, File(description='Upload file')] = None,
    title: Annotated[str | None, Form(description='Document title')] = None,
    source_type: Annotated[str, Form(description='Source type upload/url/text')] = 'upload',
    content: Annotated[str | None, Form(description='Text content (for text type)')] = None,
    url: Annotated[str | None, Form(description='URL address (for url type)')] = None,
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
    summary='Document list',
    dependencies=[
        DependsJwtAuth,
        DependsPagination,
    ],
)
async def get_documents(
    db: CurrentSession,
    request: Request,
    kb_id: Annotated[int, Path(description='Knowledge base ID')],
) -> ResponseSchemaModel[PageData[GetKnowledgeDocumentDetail]]:
    page_data = await knowledge_document_service.get_list(db=db, kb_id=kb_id, owner_id=request.user.id)
    return response_base.success(data=page_data)


@router.get('/{kb_id}/documents/{doc_id}', summary='Document details', dependencies=[DependsJwtAuth])
async def get_document(
    db: CurrentSession,
    request: Request,
    kb_id: Annotated[int, Path(description='Knowledge base ID')],
    doc_id: Annotated[int, Path(description='Document ID')],
) -> ResponseSchemaModel[GetKnowledgeDocumentDetail]:
    data = await knowledge_document_service.get(db=db, kb_id=kb_id, doc_id=doc_id, owner_id=request.user.id)
    return response_base.success(data=data)


@router.delete('/{kb_id}/documents/{doc_id}', summary='Delete document', dependencies=[DependsJwtAuth])
async def delete_document(
    db: CurrentSessionTransaction,
    request: Request,
    kb_id: Annotated[int, Path(description='Knowledge base ID')],
    doc_id: Annotated[int, Path(description='Document ID')],
) -> ResponseModel:
    count = await knowledge_document_service.delete(db=db, kb_id=kb_id, doc_id=doc_id, owner_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/{kb_id}/documents/{doc_id}/reprocess', summary='Reprocess document', dependencies=[DependsJwtAuth])
async def reprocess_document(
    db: CurrentSessionTransaction,
    request: Request,
    kb_id: Annotated[int, Path(description='Knowledge base ID')],
    doc_id: Annotated[int, Path(description='Document ID')],
) -> ResponseModel:
    count = await knowledge_document_service.reprocess(db=db, kb_id=kb_id, doc_id=doc_id, owner_id=request.user.id)
    if count > 0:
        return response_base.success()
    return response_base.fail()
