from django.db import models

class ParentRelationship(models.TextChoices):
    MOM = 'mom', 'Мама'
    DAD = 'dad', 'Папа'
    GUARDIAN = 'guardian', 'Опекун'
    OTHER = 'other', 'Другое'


class DevelopmentType(models.TextChoices):
    AUTISM = 'autism', 'Аутизм (РАС)'
    DOWN_SYNDROME = 'down_syndrome', 'Синдром Дауна'
    ZPR = 'zpr', 'ЗПР'
    UNKNOWN = 'unknown', 'Пока не знаем / не уверены'


class CommunicationStyle(models.TextChoices):
    NO_SPEECH = 'no_speech', 'Не говорит'
    SINGLE_WORDS = 'single_words', 'Говорит отдельные слова'
    PHRASES = 'phrases', 'Говорит фразами'
    FLUENT = 'fluent', 'Говорит свободно'


class UnderstandsInstructions(models.TextChoices):
    GESTURES_PICTURES = 'gestures_pictures', 'Только жесты / картинки'
    SHORT_INSTRUCTIONS = 'short_instructions', 'Короткие инструкции'
    UNDERSTANDS_EXPLANATIONS = 'understands_explanations', 'Понимает объяснения'


class ComfortableDuration(models.TextChoices):
    MIN_5 = '5_min', '5 минут'
    MIN_10 = '10_min', '10 минут'
    MIN_15 = '15_min', '15 минут'
    FLEXIBLE = 'flexible', 'Свободно'


class Sensitivity(models.TextChoices):
    LOUD_SOUNDS = 'loud_sounds', 'Громкие звуки'
    BRIGHT_LIGHT = 'bright_light', 'Яркий свет'
    ANIMATIONS = 'animations', 'Анимации'
    VIBRATIONS = 'vibrations', 'Вибрации'
    CHARACTERS_FACES = 'characters_faces', 'Лицо персонажей'

SENSITIVITY_VALUES = {'loud_sounds', 'bright_light', 'animations', 'vibrations', 'characters_faces'}
MOTOR_DIFFICULTY_VALUES = {'small_buttons', 'hold_finger', 'drag_drop'}
BEHAVIOR_NOTICES_VALUES = {'gets_tired_quickly', 'upset_by_mistakes', 'afraid_of_new', 'likes_repetitions'}
MOTIVATOR_VALUES = {'stars', 'applause', 'stickers', 'cartoon_after'}
INTEREST_VALUES = {'cars', 'food', 'space', 'music', 'letters', 'numbers', 'animals'}
