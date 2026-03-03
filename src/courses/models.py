from django.db import models

from accounts.models import Specialist
from .enums import Category, Level, MaterialType


class Course(models.Model):
    specialist = models.ForeignKey(Specialist, on_delete=models.CASCADE, related_name='courses')
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=255, choices=Category.choices)
    level = models.CharField(max_length=255, choices=Level.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField(help_text='Продолжительность курса в часах')
    preview_image = models.ImageField(upload_to='courses/previews/')

    def __str__(self) -> str:
        return self.title


class CourseModule(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    material_type = models.CharField(max_length=20, choices=MaterialType.choices)
    file = models.FileField(upload_to='courses/materials/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'{self.course.title} — {self.title}'

