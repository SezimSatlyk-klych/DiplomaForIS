from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ChatMessage, ChatSession
from .serializers import ChatRequestSerializer, ChatResponseSerializer
from .services import ChatbotServiceError, ask_gpt


@extend_schema(
    tags=['chatbot'],
    summary='Чат с GPT',
    description='Отправляет сообщение пользователя в GPT и возвращает ответ.',
    request=ChatRequestSerializer,
    responses={200: ChatResponseSerializer},
    examples=[
        OpenApiExample(
            'Пример запроса',
            value={'message': 'Ребенок избегает общения в школе. Как мягко помочь?', 'session_id': 1},
            request_only=True,
        ),
        OpenApiExample(
            'Пример ответа',
            value={
                'session_id': 1,
                'reply': 'Попробуйте начать с коротких ролевых игр дома...',
                'model': 'gpt-4o-mini',
            },
            response_only=True,
        ),
    ],
)
class ChatAPIView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ChatRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_message = serializer.validated_data['message']
        session_id = serializer.validated_data.get('session_id')

        if session_id:
            session = ChatSession.objects.filter(id=session_id, user=request.user).first()
            if not session:
                return Response(
                    {'detail': 'Сессия не найдена или не принадлежит текущему пользователю.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            session = ChatSession.objects.create(
                user=request.user,
                title=(user_message[:80] if user_message else ''),
            )

        last_messages = list(session.messages.order_by('-created_at')[:20])
        last_messages.reverse()

        prompt_messages = [
            {
                'role': 'system',
                'content': (
                    'Ты помощник для родителей детей с особыми потребностями. '
                    'Отвечай кратко, безопасно и поддерживающе. '
                    'Не ставь диагнозы и не назначай лечение.'
                ),
            }
        ]
        for msg in last_messages:
            prompt_messages.append({'role': msg.role, 'content': msg.content})
        prompt_messages.append({'role': 'user', 'content': user_message})

        try:
            data = ask_gpt(prompt_messages)
        except ChatbotServiceError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=user_message,
        )
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=data['reply'],
        )

        data['session_id'] = session.id
        return Response(data, status=status.HTTP_200_OK)
