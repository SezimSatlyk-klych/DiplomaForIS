from rest_framework import serializers

from accounts.models import Child
from .enums import AppetiteQuality, Emotion, Observation, OverallFeeling, SleepQuality
from .models import MoodTracking


class MoodTrackingSerializer(serializers.ModelSerializer):
    child = serializers.PrimaryKeyRelatedField(
        queryset=Child.objects.all(),
        help_text='ID ребёнка из ответа GET /api/auth/children/.',
    )
    overall_feeling = serializers.ChoiceField(
        choices=OverallFeeling.choices,
        help_text='Общее самочувствие (англ. value): good | normal | hard | very_hard.',
    )
    emotions = serializers.ListField(
        child=serializers.ChoiceField(choices=Emotion.choices),
        required=False,
        allow_empty=True,
        help_text=(
            'Мультивыбор эмоций (англ. value): joyful, calm, anxious, irritated, tired, sad.'
        ),
    )
    observations = serializers.ListField(
        child=serializers.ChoiceField(choices=Observation.choices),
        required=False,
        allow_empty=True,
        help_text=(
            'Мультивыбор наблюдений (англ. value): contactful, avoided_communication, '
            'focused, repetitive_behavior, played_calmly, had_meltdowns.'
        ),
    )
    sleep_quality = serializers.ChoiceField(
        choices=SleepQuality.choices,
        help_text='Сон (англ. value): good | normal | bad.',
    )
    appetite_quality = serializers.ChoiceField(
        choices=AppetiteQuality.choices,
        help_text='Аппетит (англ. value): good | normal | bad.',
    )

    class Meta:
        model = MoodTracking
        fields = (
            'id',
            'child',
            'overall_feeling',
            'emotions',
            'observations',
            'sleep_quality',
            'appetite_quality',
            'note',
            'created_at',
        )
        read_only_fields = ('created_at',)
        extra_kwargs = {
            'note': {
                'required': False,
                'allow_blank': True,
                'help_text': 'Заметка, опционально.',
            },
        }

    def validate_child(self, value):
        request = self.context.get('request')
        if request is None:
            return value

        if value.parent.user_id != request.user.id:
            raise serializers.ValidationError('Нельзя создавать запись для чужого ребёнка.')
        return value
