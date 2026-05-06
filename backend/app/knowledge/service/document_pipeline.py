"""文档处理管线：解析 → 分块 → Embedding → 写入 Qdrant。

同步函数，设计为 Celery task 调用。当 Celery 不可用时直接在后台线程执行。
"""

import hashlib
import logging
import threading
from typing import Any

import litellm

from backend.common.minio_client import download_file
from backend.common.qdrant_client import delete_vectors_by_filter, ensure_collection, upsert_vectors

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {'.txt', '.md', '.pdf', '.docx', '.html', '.csv', '.json'}


def _collection_name(kb_id: int) -> str:
    return f'kb_{kb_id}'


def _extract_text(file_path: str | None, content: str | None, source_type: str) -> str:
    """从文件或文本中提取纯文本内容。"""
    if source_type == 'text' or source_type == 'url':
        return content or ''

    if not file_path:
        return content or ''

    file_data = download_file(file_path)
    ext = file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else ''

    if ext in ('txt', 'md', 'csv', 'json'):
        return file_data.decode('utf-8', errors='replace')
    if ext == 'html':
        try:
            from html.parser import HTMLParser
            from io import StringIO

            class _HTMLStripper(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.result = StringIO()

                def handle_data(self, d):
                    self.result.write(d)

            stripper = _HTMLStripper()
            stripper.feed(file_data.decode('utf-8', errors='replace'))
            return stripper.result.getvalue()
        except Exception:
            return file_data.decode('utf-8', errors='replace')
    if ext == 'pdf':
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=file_data, filetype='pdf')
            return '\n'.join(page.get_text() for page in doc)
        except ImportError:
            log.warning('PyMuPDF not installed, skipping PDF extraction')
            return ''
    if ext == 'docx':
        try:
            from io import BytesIO
            from zipfile import ZipFile

            from xml.etree.ElementTree import fromstring

            zf = ZipFile(BytesIO(file_data))
            xml_content = zf.read('word/document.xml')
            tree = fromstring(xml_content)
            ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            return '\n'.join(node.text for node in tree.iter(f'{ns}t') if node.text)
        except Exception:
            return ''

    return file_data.decode('utf-8', errors='replace')


def _chunk_text(text: str, chunk_size: int = 512, chunk_overlap: int = 64) -> list[str]:
    """按字符数分块，保留重叠。"""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - chunk_overlap
    return chunks


def _embed_chunks(chunks: list[str], model: str = 'text-embedding-3-small', **kwargs) -> list[list[float]]:
    """调用 LiteLLM embedding 接口获取向量。"""
    if not chunks:
        return []
    response = litellm.embedding(model=model, input=chunks, **kwargs)
    return [item['embedding'] for item in response.data]


def _process_document(doc_id: int, kb_id: int) -> None:
    """同步处理单个文档的完整管线。"""
    import asyncio

    from backend.app.knowledge.crud.crud_knowledge_document import knowledge_document_dao
    from backend.database.db import async_db_session

    async def _run():
        async with async_db_session() as db:
            doc = await knowledge_document_dao.get(db, doc_id)
            if not doc:
                return

            await knowledge_document_dao.update_status(db, doc_id, 'processing')
            await db.commit()

            kb = None
            from backend.app.knowledge.crud.crud_knowledge_base import knowledge_base_dao

            kb = await knowledge_base_dao.get(db, doc.knowledge_base_id)

        try:
            text = _extract_text(doc.file_path, doc.content, doc.source_type)
            if not text.strip():
                async with async_db_session() as db:
                    await knowledge_document_dao.update_status(db, doc_id, 'error', '文档内容为空')
                    await db.commit()
                return

            chunk_size = kb.chunk_size if kb else 512
            chunk_overlap = kb.chunk_overlap if kb else 64
            chunks = _chunk_text(text, chunk_size, chunk_overlap)

            embedding_model = kb.embedding_model if kb else 'text-embedding-3-small'
            embed_kwargs: dict[str, Any] = {}
            if kb and kb.embedding_provider_id:
                from backend.app.llm.crud.crud_llm_provider import llm_provider_dao
                from backend.app.llm.service.llm_provider_service import _decrypt_api_key

                async with async_db_session() as db:
                    provider = await llm_provider_dao.get(db, kb.embedding_provider_id)
                if provider:
                    if provider.api_key_encrypted:
                        embed_kwargs['api_key'] = _decrypt_api_key(provider.api_key_encrypted)
                    if provider.api_base:
                        embed_kwargs['api_base'] = provider.api_base

            vectors = _embed_chunks(chunks, model=embedding_model, **embed_kwargs)

            collection = _collection_name(kb_id)
            vector_size = len(vectors[0]) if vectors else 1536
            ensure_collection(collection, vector_size)

            from qdrant_client import models as qmodels

            delete_vectors_by_filter(
                collection,
                qmodels.Filter(
                    must=[qmodels.FieldCondition(key='doc_id', match=qmodels.MatchValue(value=doc_id))]
                ),
            )

            ids = [
                hashlib.md5(f'{doc_id}_{i}'.encode()).hexdigest()
                for i in range(len(chunks))
            ]
            payloads = [
                {
                    'doc_id': doc_id,
                    'kb_id': kb_id,
                    'chunk_index': i,
                    'text': chunk,
                    'title': doc.title,
                }
                for i, chunk in enumerate(chunks)
            ]
            upsert_vectors(collection, ids, vectors, payloads)

            async with async_db_session() as db:
                await knowledge_document_dao.update_status(db, doc_id, 'ready')
                await knowledge_document_dao.update_model(db, doc_id, {'chunk_count': len(chunks)})
                await db.commit()

        except Exception as e:
            log.exception(f'Document {doc_id} processing failed')
            async with async_db_session() as db:
                await knowledge_document_dao.update_status(db, doc_id, 'error', str(e)[:1000])
                await db.commit()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()


def trigger_vectorize(doc_id: int, kb_id: int) -> None:
    """触发文档向量化。优先使用 Celery，不可用时用后台线程。"""
    try:
        from backend.app.task.tasks.knowledge.tasks import process_document_task

        process_document_task.delay(doc_id, kb_id)
        log.info(f'Queued document {doc_id} for Celery processing')
    except Exception:
        log.info(f'Celery unavailable, processing document {doc_id} in background thread')
        thread = threading.Thread(target=_process_document, args=(doc_id, kb_id), daemon=True)
        thread.start()
