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