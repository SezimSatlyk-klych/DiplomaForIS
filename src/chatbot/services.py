import json
from urllib import error, request

from django.conf import settings


class ChatbotServiceError(Exception):
    pass


def ask_gpt(messages: list[dict[str, str]]) -> dict[str, str]:
    api_key = getattr(settings, 'OPENAI_API_KEY', '')
    model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')

    if not api_key:
        raise ChatbotServiceError('OPENAI_API_KEY не задан в .env.')

    payload = {
        'model': model,
        'messages': messages,
        'temperature': 0.7,
    }

    req = request.Request(
        url='https://api.openai.com/v1/chat/completions',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read().decode('utf-8'))
    except error.HTTPError as exc:
        error_body = exc.read().decode('utf-8', errors='ignore')
        raise ChatbotServiceError(f'OpenAI API HTTP {exc.code}: {error_body}') from exc
    except Exception as exc:
        raise ChatbotServiceError(f'Ошибка запроса к OpenAI API: {exc}') from exc

    try:
        reply_text = body['choices'][0]['message']['content'].strip()
    except (KeyError, IndexError, AttributeError) as exc:
        raise ChatbotServiceError('OpenAI API вернул неожиданный формат ответа.') from exc

    return {'reply': reply_text, 'model': model}
