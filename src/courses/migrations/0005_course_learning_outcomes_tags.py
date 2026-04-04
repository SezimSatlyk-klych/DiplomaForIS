# Generated manually for course form fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0004_remove_coursepurchase_unique_course_purchase_per_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='learning_outcomes',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Опишите, чему смогут научиться пользователи после курса.',
                verbose_name='Чему научатся пользователи?',
            ),
        ),
        migrations.AddField(
            model_name='course',
            name='tags',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Список кодов тэгов (см. CourseTag).',
            ),
        ),
    ]
