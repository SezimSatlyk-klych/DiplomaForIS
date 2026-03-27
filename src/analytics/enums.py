from django.db import models


class OverallFeeling(models.TextChoices):
    GOOD = 'good', 'Хорошо'
    NORMAL = 'normal', 'Нормально'
    HARD = 'hard', 'Сложно'
    VERY_HARD = 'very_hard', 'Очень тяжело'


class Emotion(models.TextChoices):
    JOYFUL = 'joyful', 'Радостный'
    CALM = 'calm', 'Спокойный'
    ANXIOUS = 'anxious', 'Тревожный'
    IRRITATED = 'irritated', 'Раздраженный'
    TIRED = 'tired', 'Уставший'
    SAD = 'sad', 'Грустный'


class Observation(models.TextChoices):
    CONTACTFUL = 'contactful', 'Был контактным'
    AVOIDED_COMMUNICATION = 'avoided_communication', 'Избегал общения'
    FOCUSED = 'focused', 'Был сосредоточен'
    REPETITIVE_BEHAVIOR = 'repetitive_behavior', 'Повторяющееся поведение'
    PLAYED_CALMLY = 'played_calmly', 'Играл спокойно'
    HAD_MELTDOWNS = 'had_meltdowns', 'Были истерики'


class SleepQuality(models.TextChoices):
    GOOD = 'good', 'Хороший'
    NORMAL = 'normal', 'Обычный'
    BAD = 'bad', 'Плохой'


class AppetiteQuality(models.TextChoices):
    GOOD = 'good', 'Хороший'
    NORMAL = 'normal', 'Обычный'
    BAD = 'bad', 'Плохой'


EMOTION_VALUES = {choice.value for choice in Emotion}
OBSERVATION_VALUES = {choice.value for choice in Observation}
