from django.db import models

from accounts.models import Child
from .enums import AppetiteQuality, OverallFeeling, SleepQuality


class MoodTracking(models.Model):
    child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name='mood_trackings')
    overall_feeling = models.CharField('Общее самочувствие', max_length=20, choices=OverallFeeling.choices)
    emotions = models.JSONField('Эмоции за день', default=list, blank=True)
    observations = models.JSONField('Наблюдения за день', default=list, blank=True)
    sleep_quality = models.CharField('Сон', max_length=10, choices=SleepQuality.choices)
    appetite_quality = models.CharField('Аппетит', max_length=10, choices=AppetiteQuality.choices)
    note = models.TextField('Заметка', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.child.name}: {self.created_at.date()}'
