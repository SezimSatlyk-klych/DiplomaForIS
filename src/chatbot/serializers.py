from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(help_text='Сообщение пользователя для GPT.')
    session_id = serializers.IntegerField(
        required=False,
        help_text='ID существующей сессии. Если не передан, будет создана новая.',
    )


class ChatResponseSerializer(serializers.Serializer):
    session_id = serializers.IntegerField(help_text='ID сессии чата.')
    reply = serializers.CharField(help_text='Ответ модели GPT.')
    model = serializers.CharField(help_text='Имя использованной модели.')
