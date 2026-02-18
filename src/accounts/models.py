from django.conf import settings
from django.db import models

from .enums import (
    ComfortableDuration,
    CommunicationStyle,
    DevelopmentType,
    Language,
    Method,
    ParentRelationship,
    Specialization,
    UnderstandsInstructions,
    WorkFormat,
)


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=20, choices=ParentRelationship.choices)
    relationship_other = models.CharField(max_length=255, blank=True)


class Specialist(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='specialist')
    full_name = models.CharField('Имя и Фамилия', max_length=255)
    approach_description = models.TextField('О подходе (3–5 предложений)', blank=True)


class SpecialistDescription(models.Model):
    specialist = models.OneToOneField(Specialist, on_delete=models.CASCADE, related_name='description')
    specializations = models.JSONField(default=list, blank=True)
    years_experience = models.PositiveSmallIntegerField('Стаж работы', null=True, blank=True)
    methods = models.JSONField(default=list, blank=True)
    age_range = models.CharField('Возраст детей', max_length=255, blank=True)
    development_types = models.JSONField(default=list, blank=True)
    work_format = models.CharField(max_length=20, choices=WorkFormat.choices, null=True, blank=True)
    languages = models.JSONField(default=list, blank=True)
    time_zone = models.CharField('Часовой пояс', max_length=63, blank=True)
    city = models.CharField('Город', max_length=255, blank=True)
    provide_individual_consultations = models.BooleanField('Индивидуальные консультации', default=False)
    work_with_child_through_parent = models.BooleanField('Работа с ребёнком через родителя', default=False)
    provide_recommendations_and_plans = models.BooleanField('Рекомендации и планы занятий', default=False)
    track_progress_and_analytics = models.BooleanField('Прогресс и аналитика', default=False)


class Child(models.Model):
    parent = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='children')
    name = models.CharField('Имя ребёнка', max_length=255)
    age = models.PositiveSmallIntegerField('Возраст', null=True, blank=True)
    development_type = models.CharField(max_length=20, choices=DevelopmentType.choices, null=True, blank=True)
    communication_style = models.CharField(max_length=30, choices=CommunicationStyle.choices, null=True, blank=True)
    understands_instructions = models.CharField(max_length=30, choices=UnderstandsInstructions.choices, null=True, blank=True)
    sensory_sensitivities = models.JSONField(default=list, blank=True, help_text='Чувствительность к: громкие звуки, яркий свет, анимации и т.д.')
    motor_difficulties = models.JSONField(default=list, blank=True, help_text='Сложности: маленькие кнопки, удержание пальца, drag&drop.')
    behavior_notices = models.JSONField(default=list, blank=True, help_text='Что замечаете чаще: устаёт, расстраивается при ошибке и т.д.')
    motivators = models.JSONField(default=list, blank=True, help_text='Что радует: звёзды, аплодисменты, наклейки, мультик после занятия.')
    interests = models.JSONField(default=list, blank=True)
    comfortable_duration = models.CharField(max_length=20, choices=ComfortableDuration.choices, null=True, blank=True)
