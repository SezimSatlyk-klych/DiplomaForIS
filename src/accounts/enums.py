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


class Specialization(models.TextChoices):
    ABA = 'aba', 'АВА-терапия'
    SPEECH_THERAPIST = 'speech_therapist', 'Логопед'
    NEUROPSYCHOLOGIST = 'neuropsychologist', 'Нейропсихолог'
    OCCUPATIONAL_THERAPY = 'occupational_therapy', 'Эрготерапия'
    ART_THERAPY = 'art_therapy', 'Арт-терапия'
    SENSORY_THERAPY = 'sensory_therapy', 'Сенсорная терапия'
    SPECIAL_EDUCATOR = 'special_educator', 'Спецпедагог'
    OTHER = 'other', 'Другое'


class Method(models.TextChoices):
    ABA = 'aba', 'ABA'
    PECS = 'pecs', 'PECS'
    DIR_FLOORTIME = 'dir_floortime', 'DIR / Floortime'
    SENSORY_INTEGRATION = 'sensory_integration', 'Сенсорная интеграция'
    OTHER = 'other', 'Другое'


class WorkFormat(models.TextChoices):
    OFFLINE = 'offline', 'Офлайн'
    ONLINE = 'online', 'Онлайн'


class Language(models.TextChoices):
    RU = 'ru', 'Русский'
    KZ = 'kz', 'Казахский'
    EN = 'en', 'Английский'


class SpecialistDevelopmentType(models.TextChoices):
    """Типы развития для фильтра специалиста (отдельный enum, не трогаем DevelopmentType)."""
    AUTISM = 'autism', 'Аутизм (РАС)'
    DOWN_SYNDROME = 'down_syndrome', 'Синдром Дауна'
    ZPR = 'zpr', 'ЗПР'
    MIXED = 'mixed', 'Смешанные случаи'
    OTHER = 'other', 'Другое'


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


class MotorDifficulty(models.TextChoices):
    SMALL_BUTTONS = 'small_buttons', 'Нажимать маленькие кнопки'
    HOLD_FINGER = 'hold_finger', 'Удерживать палец'
    DRAG_DROP = 'drag_drop', 'Делать drag & drop'


class BehaviorNotice(models.TextChoices):
    GETS_TIRED_QUICKLY = 'gets_tired_quickly', 'Быстро устаёт'
    UPSET_BY_MISTAKES = 'upset_by_mistakes', 'Расстраивается при ошибке'
    AFRAID_OF_NEW = 'afraid_of_new', 'Боится нового'
    LIKES_REPETITIONS = 'likes_repetitions', 'Любит повторения'


class Motivator(models.TextChoices):
    STARS = 'stars', 'Звёзды'
    APPLAUSE = 'applause', 'Аплодисменты'
    STICKERS = 'stickers', 'Наклейки'
    CARTOON_AFTER = 'cartoon_after', 'Мультик после занятия'


class Interest(models.TextChoices):
    CARS = 'cars', 'Машины'
    FOOD = 'food', 'Еда'
    SPACE = 'space', 'Космос'
    MUSIC = 'music', 'Музыка'
    LETTERS = 'letters', 'Буквы'
    NUMBERS = 'numbers', 'Цифры'
    ANIMALS = 'animals', 'Животные'


# Множества допустимых значений (для валидации списков в JSON)
SENSITIVITY_VALUES = {c.value for c in Sensitivity}
MOTOR_DIFFICULTY_VALUES = {c.value for c in MotorDifficulty}
BEHAVIOR_NOTICES_VALUES = {c.value for c in BehaviorNotice}
MOTIVATOR_VALUES = {c.value for c in Motivator}
INTEREST_VALUES = {c.value for c in Interest}
