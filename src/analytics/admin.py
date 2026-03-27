from django.contrib import admin

from .models import MoodTracking


@admin.register(MoodTracking)
class MoodTrackingAdmin(admin.ModelAdmin):
    list_display = ('id', 'child', 'overall_feeling', 'sleep_quality', 'appetite_quality', 'created_at')
    list_filter = ('overall_feeling', 'sleep_quality', 'appetite_quality')
    search_fields = ('child__name', 'note')
