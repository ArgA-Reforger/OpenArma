"""Celery task for knowledge base document vectorization."""

from backend.app.task.celery import celery_app


@celery_app.task(name='process_document', bind=True, max_retries=3)
def process_document_task(self, doc_id: int, kb_id: int) -> str:
    from backend.app.knowledge.service.document_pipeline import _process_document

    try:
        _process_document(doc_id, kb_id)
        return f'Document {doc_id} processed successfully'
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
