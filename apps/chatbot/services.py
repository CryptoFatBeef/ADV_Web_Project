"""
Chatbot service — Phase 1 FAQ bot.
Calls Claude via OpenRouter using the OpenAI-compatible SDK.
No n8n. Django-native openai client pointed at OpenRouter base_url.
"""
import openai
from django.conf import settings


def build_faq_context() -> str:
    """Load active FAQ entries and format as system prompt context."""
    from apps.chatbot.models import FAQEntry
    entries = FAQEntry.objects.filter(is_active=True).order_by('category', 'order')
    if not entries.exists():
        return 'No FAQ entries available.'
    lines = ['You are a helpful assistant for 技擊跆拳道會 (Advanced Taekwondo Club).']
    lines.append('Answer questions based on the following FAQ:')
    lines.append('')
    current_category = None
    for entry in entries:
        if entry.category != current_category:
            lines.append(f'## {entry.get_category_display()}')
            current_category = entry.category
        lines.append(f'Q: {entry.question}')
        lines.append(f'A: {entry.answer}')
        lines.append('')
    lines.append('If a question is not covered by the FAQ, politely say you cannot help with that topic.')
    return '\n'.join(lines)


def get_chat_response(session, user_message: str) -> str:
    """
    Send user_message to Claude via OpenRouter with full session history.
    Saves ChatMessage records for both user turn and assistant reply.
    Returns assistant reply text.
    """
    from apps.chatbot.models import ChatMessage

    # Save user message first
    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.USER,
        content=user_message,
    )

    # Build message history for API call (system prompt + conversation turns)
    history = session.messages.order_by('created_at').values('role', 'content')
    messages = [{'role': 'system', 'content': build_faq_context()}]
    messages += [{'role': m['role'], 'content': m['content']} for m in history]

    client = openai.OpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
    )
    response = client.chat.completions.create(
        model=settings.OPENROUTER_MODEL,
        max_tokens=1000,
        messages=messages,
    )

    reply_text    = response.choices[0].message.content
    input_tokens  = response.usage.prompt_tokens
    output_tokens = response.usage.completion_tokens

    # Save assistant reply with token counts
    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.ASSISTANT,
        content=reply_text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    return reply_text
