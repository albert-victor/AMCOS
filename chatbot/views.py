from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json

from .openrouter_client import ask_openrouter
from .knowledge_base import get_response


@csrf_exempt
def chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        question = (data.get('question') or '').strip()
        lang = data.get('lang', 'sw')
        if lang not in ('sw', 'en'):
            lang = 'sw'
    except (json.JSONDecodeError, AttributeError):
        question = ''
        lang = 'sw'

    if not question:
        msg = 'Tafadhali ingiza swali.' if lang == 'sw' else 'Please enter a question.'
        return JsonResponse({'answer': msg, 'source': 'local'})

    user = request.user if request.user.is_authenticated else None
    guest = user is None

    if getattr(settings, 'OPENROUTER_API_KEY', ''):
        answer, source = ask_openrouter(question, lang, user, guest=guest)
    else:
        answer = get_response(question, lang, guest=guest)
        source = 'local'

    return JsonResponse({'answer': answer, 'source': source})
