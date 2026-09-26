from backend.app.conversation.service.chat_service import TITLE_SYSTEM_PROMPT


def test_title_prompt_follows_conversation_language() -> None:
    assert 'same language as the conversation' in TITLE_SYSTEM_PROMPT


def test_title_prompt_limits_length_in_words() -> None:
    assert 'no more than 6 words' in TITLE_SYSTEM_PROMPT
