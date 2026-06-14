"""OpenRouter API client for AMCOS AI."""
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

from .knowledge_base import build_system_prompt, get_response as keyword_fallback

logger = logging.getLogger(__name__)

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'


def _user_context(user):
    if not user or not user.is_authenticated:
        return ''
    parts = [
        f'role={getattr(user, "role", "guest")}',
        f'cooperative_id={getattr(user, "cooperative_id", "") or "none"}',
    ]
    name = user.get_full_name() if hasattr(user, 'get_full_name') else ''
    if name:
        parts.append(f'name={name}')
    return ', '.join(parts)


def ask_openrouter(question, lang='sw', user=None, guest=False):
    """
    Call OpenRouter chat completions. Falls back to keyword knowledge on failure.
    Returns (answer: str, source: 'openrouter' | 'fallback').
    """
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '') or ''
    if not api_key:
        return keyword_fallback(question, lang, guest=guest), 'fallback'

    model = getattr(settings, 'OPENROUTER_MODEL', 'openai/gpt-4o-mini')
    site_url = getattr(settings, 'OPENROUTER_SITE_URL', 'http://127.0.0.1:8000')
    site_name = getattr(settings, 'OPENROUTER_SITE_NAME', 'AMCOS AI')

    lang_name = 'Swahili' if lang == 'sw' else 'English'
    system_prompt = build_system_prompt(lang, guest=guest)
    user_message = question.strip()
    if not guest and user:
        user_block = _user_context(user)
        if user_block:
            user_message = f'[User context: {user_block}]\n\n{user_message}'

    if guest:
        user_instruction = (
            f'Reply only in {lang_name}. Visitor is NOT logged in — give only general public information '
            f'about MGOWELO AMCOS (what it is, how to join, how to login). '
            f'Do not give staff workflows or pretend to know their account. '
            f'For personal balances or approvals, tell them to sign in first.\n\n'
        )
    else:
        user_instruction = (
            f'Reply only in {lang_name}. User is logged in — keep answers practical and specific to their role.\n\n'
        )

    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {
                'role': 'user',
                'content': f'{user_instruction}{user_message}',
            },
        ],
        'temperature': 0.35,
        'max_tokens': 800,
    }

    req = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': site_url,
            'X-Title': site_name,
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = json.loads(resp.read().decode('utf-8'))
        choices = body.get('choices') or []
        if not choices:
            raise ValueError('empty choices')
        content = (choices[0].get('message') or {}).get('content', '').strip()
        if not content:
            raise ValueError('empty content')
        return content, 'openrouter'
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        logger.warning('OpenRouter request failed: %s', exc)
        return keyword_fallback(question, lang, guest=guest), 'fallback'
