"""Arma command dispatch service.

Integrates message queue + battle state evaluation before dispatching to Celery.
"""

import logging

log = logging.getLogger(__name__)


class CommandService:
    @staticmethod
    async def process_situation_report(
        project_id: int,
        conversation_id: str,
        request_id: int,
        situation_data: dict,
        priority: str = 'normal',
    ) -> None:
        """Evaluate battle state, enqueue, and dispatch processing task."""
        from backend.app.open.service.battle_state import evaluate
        from backend.app.open.service.message_queue import acquire_lock, enqueue_situation

        assessment = await evaluate(conversation_id, situation_data)
        effective_priority = assessment['priority'] if assessment['priority'] == 'critical' else priority

        if assessment.get('transition'):
            log.info('Battle state transition: %s (conv=%s)', assessment['transition'], conversation_id)

        locked = await acquire_lock(conversation_id)
        if not locked:
            await enqueue_situation(conversation_id, request_id, situation_data, effective_priority)
            log.info(
                'AI processing in progress, situation #%s queued: conv=%s, priority=%s',
                request_id, conversation_id, effective_priority,
            )
            return

        from backend.app.open.service.message_queue import release_lock
        await release_lock(conversation_id)

        from backend.app.task.tasks.open.tasks import process_situation_task

        process_situation_task.delay(
            project_id=project_id,
            conversation_id=conversation_id,
            request_id=request_id,
            situation_data=situation_data,
            priority=effective_priority,
        )
        log.info(
            'Situation dispatched: project=%s, conv=%s, request=%s, priority=%s, battle_state=%s',
            project_id, conversation_id, request_id, effective_priority, assessment['state'],
        )
