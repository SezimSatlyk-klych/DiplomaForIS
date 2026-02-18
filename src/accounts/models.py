from django.conf import settings
from django.db import models

from .enums import ParentRelationship


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=20, choices=ParentRelationship.choices)
    relationship_other = models.CharField(max_length=255, blank=True)

