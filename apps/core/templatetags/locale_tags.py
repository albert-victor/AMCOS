"""Single-language UI strings from session language (sw / en)."""
from django import template
from django.utils.html import escape

register = template.Library()


def _pick(context, sw, en=None):
    lang = context.get('current_lang', 'en')
    if lang == 'en':
        return en if en is not None else sw
    return sw


@register.simple_tag(takes_context=True)
def t(context, sw, en=None):
    """
    Usage: {% t "Jumla" "Total" %}
    Shows Swahili or English only, per language settings.
    """
    return _pick(context, sw, en)


@register.simple_tag(takes_context=True)
def te(context, sw, en=None):
    """Escaped variant for attributes: title="{% te 'Angalia' 'View' %}" """
    return escape(_pick(context, sw, en))
