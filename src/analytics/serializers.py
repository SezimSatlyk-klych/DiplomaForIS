from rest_framework import serializers

from .enums import EMOTION_VALUES, OBSERVATION_VALUES
from .models import MoodTracking


class MoodTrackingSerializer(serializers.ModelSerializer):
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

    def validate_child(self, value):
        request = self.context.get('request')
        if request is None:
            return value

        if value.parent.user_id != request.user.id:
            raise serializers.ValidationError('Нельзя создавать запись для чужого ребёнка.')
        return value

    def validate_emotions(self, value):
        invalid = [item for item in value if item not in EMOTION_VALUES]
        if invalid:
            raise serializers.ValidationError(
                f'Недопустимые эмоции: {", ".join(invalid)}.'
            )
        return value

    def validate_observations(self, value):
        invalid = [item for item in value if item not in OBSERVATION_VALUES]
        if invalid:
            raise serializers.ValidationError(
                f'Недопустимые наблюдения: {", ".join(invalid)}.'
            )
        return value

