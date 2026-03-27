from datetime import datetime, time, timedelta
import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Child
from analytics.enums import AppetiteQuality, Emotion, Observation, OverallFeeling, SleepQuality
from analytics.models import MoodTracking


class Command(BaseCommand):
    help = 'Создает mock-данные mood tracking за последние 30 дней.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='Сколько дней заполнять (по умолчанию 30).')
        parser.add_argument(
            '--per-child-max',
            type=int,
            default=1,
            help='Максимум записей в день на ребенка (по умолчанию 1).',
        )

    def handle(self, *args, **options):
        days = max(1, int(options['days']))
        per_child_max = max(1, int(options['per_child_max']))

        children = list(Child.objects.select_related('parent', 'parent__user').all())
        if not children:
            self.stdout.write(self.style.WARNING('Нет детей в базе. Сначала создайте детей.'))
            return

        created = 0
        today = timezone.localdate()

        emotions_pool = [choice.value for choice in Emotion]
        observations_pool = [choice.value for choice in Observation]
        overall_pool = [choice.value for choice in OverallFeeling]
        sleep_pool = [choice.value for choice in SleepQuality]
        appetite_pool = [choice.value for choice in AppetiteQuality]

        for child in children:
            for day_offset in range(days):
                current_date = today - timedelta(days=day_offset)
                entries_for_day = random.randint(0, per_child_max)

                for _ in range(entries_for_day):
                    created_at = timezone.make_aware(
                        datetime.combine(current_date, time.min)
                    ) + timedelta(
                        hours=random.randint(8, 21),
                        minutes=random.randint(0, 59),
                    )

                    emotions_count = random.randint(1, min(3, len(emotions_pool)))
                    observations_count = random.randint(1, min(3, len(observations_pool)))

                    mood = MoodTracking.objects.create(
                        child=child,
                        overall_feeling=random.choice(overall_pool),
                        emotions=random.sample(emotions_pool, emotions_count),
                        observations=random.sample(observations_pool, observations_count),
                        sleep_quality=random.choice(sleep_pool),
                        appetite_quality=random.choice(appetite_pool),
                        note='Mock запись для аналитики.',
                    )
                    MoodTracking.objects.filter(pk=mood.pk).update(created_at=created_at)
                    created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Готово. Создано {created} mood tracking записей для {len(children)} детей.'
            )
        )
