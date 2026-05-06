"""滑动窗口 + 自动摘要上下文管理器 (ADR-32b)。

当对话消息数超过阈值时，自动将早期消息压缩为一条摘要，
避免上下文无限膨胀。摘要存为 Message(role='system', metadata={type: 'context_summary'})。

两条消费路径：
- Web Chat (ChatService) — 通过 build_history() 获取 history list[dict]
- Arma Task (tasks.py) — 同上
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.conversation.crud.crud_message import message_dao

log = logging.getLogger(__name__)

SUMMARY_THRESHOLD_RATIO = 2.0
SUMMARY_PROMPT = (
    'Summarize the following conversation history into a concise context summary. '
    'Preserve: key decisions made, important facts mentioned, current state of discussion, '
    'and any unresolved questions. Be factual and brief (under 500 words). '
    'Write in the same language as the conversation.'
)
ARMA_SUMMARY_PROMPT = (
    'Summarize the following battlefield conversation history into a concise tactical summary. '
    'Preserve: key tactical decisions, troop movements ordered, enemy contact history, '
    'casualties reported, mission objective progress, and current battlefield state. '
    'Be factual, use military terminology, and stay under 500 words. Write in English.'
)


async def build_history(
    db: AsyncSession,
    conversation_id: int,
    *,
    context_window: int = 20,
    llm_config: dict | None = None,
    is_arma: bool = False,
) -> list[dict]:
    """Build optimized history with sliding window + auto-summary.

    1. Count total messages in conversation
    2. If total <= context_window * THRESHOLD_RATIO: just return recent N (no summary needed)
    3. If total > threshold: check for existing summary, or generate one
    4. Return: [summary_msg (if any)] + recent N messages

    :param db: async database session
    :param conversation_id: target conversation
    :param context_window: number of recent messages to keep in full
    :param llm_config: dict with provider_type/api_base/api_key_encrypted/model_name for summary LLM
    :param is_arma: use Arma-specific summary prompt
    :return: list of message dicts ready for LLM consumption
    """
    total = await message_dao.count_messages(db, conversation_id)
    threshold = int(context_window * SUMMARY_THRESHOLD_RATIO)

    recent_messages = await message_dao.get_recent(db, conversation_id, limit=context_window)

    history: list[dict] = []

    if total > threshold:
        existing_summary = _find_latest_summary(recent_messages)

        if existing_summary:
            pass
        elif llm_config and total > threshold:
            summary_text = await _generate_summary(
                db, conversation_id, context_window, llm_config, is_arma,
            )
            if summary_text:
                await _save_summary(db, conversation_id, summary_text, total - context_window)
                history.append({'role': 'system', 'content': summary_text})

    for msg in recent_messages:
        if not msg.content or msg.del_flag:
            continue
        meta = msg.metadata_ or {}
        if meta.get('type') == 'context_summary':
            history.append({'role': 'system', 'content': msg.content})
        else:
            history.append({'role': msg.role, 'content': msg.content})

    return history


def _find_latest_summary(messages: list) -> bool:
    """Check if any message in the window is already a context summary."""
    for msg in messages:
        meta = msg.metadata_ or {}
        if meta.get('type') == 'context_summary':
            return True
    return False


async def _generate_summary(
    db: AsyncSession,
    conversation_id: int,
    context_window: int,
    llm_config: dict,
    is_arma: bool,
) -> str | None:
    """Generate a summary of messages outside the current window."""
    from backend.app.conversation.engine.llm import acompletion

    total = await message_dao.count_messages(db, conversation_id)
    older_count = total - context_window
    if older_count <= 0:
        return None

    fetch_limit = min(older_count, 40)
    all_messages = await message_dao.get_recent(db, conversation_id, limit=total)
    older_messages = all_messages[:fetch_limit]

    if not older_messages:
        return None

    conversation_text_parts: list[str] = []
    for msg in older_messages:
        if not msg.content or msg.del_flag:
            continue
        meta = msg.metadata_ or {}
        if meta.get('type') == 'context_summary':
            conversation_text_parts.append(f'[Previous Summary]: {msg.content[:500]}')
        elif meta.get('type') == 'situation_report':
            conversation_text_parts.append(f'[Situation Report]: {msg.content[:300]}')
        else:
            conversation_text_parts.append(f'{msg.role}: {msg.content[:500]}')

    if not conversation_text_parts:
        return None

    conversation_text = '\n'.join(conversation_text_parts)

    prompt = ARMA_SUMMARY_PROMPT if is_arma else SUMMARY_PROMPT
    messages = [
        {'role': 'system', 'content': prompt},
        {'role': 'user', 'content': conversation_text},
    ]

    try:
        response = await acompletion(
            provider_type=llm_config['provider_type'],
            api_base=llm_config.get('api_base'),
            api_key_encrypted=llm_config.get('api_key_encrypted'),
            model_name=llm_config['model_name'],
            messages=messages,
            temperature=0.3,
            max_tokens=600,
        )
        summary = (response.choices[0].message.content or '').strip()
        if summary:
            log.info(
                'Generated context summary for conv=%s (%s older msgs → %s chars)',
                conversation_id, len(older_messages), len(summary),
            )
        return summary or None
    except Exception:
        log.warning('Failed to generate context summary for conv=%s', conversation_id, exc_info=True)
        return None


async def _save_summary(
    db: AsyncSession,
    conversation_id: int,
    summary_text: str,
    summarized_count: int,
) -> None:
    """Persist the summary as a system message with context_summary metadata."""
    from backend.app.conversation.model.message import Message

    db.add(Message(
        conversation_id=conversation_id,
        role='system',
        content=summary_text,
        metadata_={
            'type': 'context_summary',
            'summarized_count': summarized_count,
        },
    ))
    await db.flush()
