from django.db import models


class Category(models.TextChoices):
    AUTISM = 'autism', 'Autism'
    SPEECH_THERAPY = 'speech_therapy', 'Speech Therapy'
    ADHD = 'adhd', 'ADHD'
    SENSORY_PROCESSING = 'sensory_processing', 'Sensory Processing'
    SOCIAL_DEVELOPMENT = 'social_development', 'Social Development'
    PHYSICAL_THERAPY = 'physical_therapy', 'Physical Therapy'
    BEHAVIORAL_SUPPORT = 'behavioral_support', 'Behavioral Support'
    LEARNING_DISABILITIES = 'learning_disabilities', 'Learning Disabilities'


class Level(models.TextChoices):
    BEGINNER = 'beginner', 'Начинающий'
    INTERMEDIATE = 'intermediate', 'Средний'
    ADVANCED = 'advanced', 'Продвинутый'


class MaterialType(models.TextChoices):
    ARTICLE = 'article', 'Статья'
    PDF = 'pdf', 'PDF'
    VIDEO = 'video', 'Видео'


class CourseTag(models.TextChoices):
    """Тэги курса (мультивыбор на форме создания)."""

    TO_PARENTS = 'to_parents', 'РОДИТЕЛЯМ'
    SELF_REGULATION = 'self_regulation', 'САМОРЕГУЛЯЦИЯ'
    LOGICAL_THINKING = 'logical_thinking', 'ЛОГИЧЕСКОЕ МЫШЛЕНИЕ'
    LEARNING_THROUGH_PLAY = 'learning_through_play', 'ОБУЧЕНИЕ ЧЕРЕЗ ИГРУ'
    FOR_CHILDREN = 'for_children', 'ДЕТЯМ'
    EASY_START = 'easy_start', 'ЛЕГКИЙ СТАРТ'
    SPEECH_THERAPY_WORK = 'speech_therapy_work', 'ЛОГОПЕДИЧЕСКАЯ РАБОТА'
    SOCIAL_SKILLS_START = 'social_skills_start', 'СОЦИАЛЬНЫЕ НАВЫКИ СТАРТ'
    WITH_PARENT_PARTICIPATION = 'with_parent_participation', 'С УЧАСТИЕМ РОДИТЕЛЯ'
    SPEECH_UNDERSTANDING = 'speech_understanding', 'ПОНИМАНИЕ РЕЧИ'
    GRADUAL_DEVELOPMENT = 'gradual_development', 'ПОСТЕПЕННОЕ РАЗВИТИЕ'
    STRUCTURED_CLASSES = 'structured_classes', 'СТРУКТУРИРОВАННЫЕ ЗАНЯТИЯ'
    MEMORY = 'memory', 'ПАМЯТЬ'
    INTENSIVE_COURSE = 'intensive_course', 'ИНТЕНСИВНЫЙ КУРС'