"""UI language helpers — English default, Swahili on user choice."""
from django.conf import settings

SUPPORTED_LANGS = ('en', 'sw')
DEFAULT_LANG = 'en'


def normalize_lang(lang):
    if lang in SUPPORTED_LANGS:
        return lang
    code = getattr(settings, 'LANGUAGE_CODE', DEFAULT_LANG)
    return code if code in SUPPORTED_LANGS else DEFAULT_LANG


def get_request_lang(request):
    """Resolve language from session, then cookie, then site default."""
    lang = request.session.get('lang')
    if not lang:
        lang = request.COOKIES.get('django_language')
    return normalize_lang(lang)
