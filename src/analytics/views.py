from collections import defaultdict
from datetime import date, datetime, time, timedelta

from django.utils import timezone
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .enums import AppetiteQuality, Emotion, Observation, OverallFeeling, SleepQuality
from .models import MoodTracking
from .serializers import MoodTrackingSerializer


def _choices_list(enum_class):
    return [{'value': c.value, 'label': c.label} for c in enum_class]


def _parse_anchor_date(value: str | None) -> date:
    if not value:
        return timezone.localdate()
    return date.fromisoformat(value)


def _period_bounds(period: str, anchor: date) -> tuple[datetime, datetime]:
    if period == 'day':
        start_date = anchor
        end_date = anchor
    elif period == 'week':
        start_date = anchor - timedelta(days=anchor.weekday())
        end_date = start_date + timedelta(days=6)
    elif period == 'month':
        start_date = anchor.replace(day=1)
        if start_date.month == 12:
            next_month = start_date.replace(year=start_date.year + 1, month=1, day=1)
        else:
            next_month = start_date.replace(month=start_date.month + 1, day=1)
        end_date = next_month - timedelta(days=1)
    else:
        raise ValueError('period должен быть одним из: day, week, month.')

    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start_date, time.min), tz)
    end_dt = timezone.make_aware(datetime.combine(end_date, time.max), tz)
    return start_dt, end_dt


def _previous_period_date_range(period: str, anchor: date) -> tuple[date, date] | None:
    """Календарные границы предыдущего периода того же типа (для сравнения трендов)."""
    if period == 'day':
        d = anchor - timedelta(days=1)
        return d, d
    if period == 'week':
        start_current = anchor - timedelta(days=anchor.weekday())
        end_prev = start_current - timedelta(days=1)
        start_prev = end_prev - timedelta(days=6)
        return start_prev, end_prev
    if period == 'month':
        first_this = anchor.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        start_prev = last_prev.replace(day=1)
        return start_prev, last_prev
    return None


def _date_range_to_dt_bounds(start_d: date, end_d: date) -> tuple[datetime, datetime]:
    tz = timezone.get_current_timezone()
    start_dt = timezone.make_aware(datetime.combine(start_d, time.min), tz)
    end_dt = timezone.make_aware(datetime.combine(end_d, time.max), tz)
    return start_dt, end_dt


# Шкала 1–5 для полоски дней (фронт мапит на 5 эмодзи).
FEELING_SCORE = {
    OverallFeeling.VERY_HARD: 1,
    OverallFeeling.HARD: 2,
    OverallFeeling.NORMAL: 3,
    OverallFeeling.GOOD: 5,
}

QUALITY_SCORE = {
    'good': 3.0,
    'normal': 2.0,
    'bad': 1.0,
}

WEEKDAY_SHORT_RU = ('ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС')


def _iter_dates(start_d: date, end_d: date):
    d = start_d
    while d <= end_d:
        yield d
        d += timedelta(days=1)


def _group_feeling_scores_by_day(queryset):
    by_day = defaultdict(list)
    for row in queryset.values('created_at', 'overall_feeling'):
        local_dt = timezone.localtime(row['created_at'])
        feeling = row['overall_feeling']
        score = FEELING_SCORE.get(feeling)
        if score is not None:
            by_day[local_dt.date()].append(score)
    return by_day


def _day_mood_score(by_day: dict, d: date) -> int | None:
    scores = by_day.get(d)
    if not scores:
        return None
    return max(1, min(5, int(round(sum(scores) / len(scores)))))


def _avg_quality_score(queryset, field_name: str) -> float | None:
    counts = {
        'good': queryset.filter(**{field_name: 'good'}).count(),
        'normal': queryset.filter(**{field_name: 'normal'}).count(),
        'bad': queryset.filter(**{field_name: 'bad'}).count(),
    }
    n = sum(counts.values())
    if n == 0:
        return None
    total = sum(QUALITY_SCORE[k] * counts[k] for k in counts)
    return total / n


def _sleep_appetite_card(current_avg: float | None, prev_avg: float | None, kind: str) -> dict:
    """
    kind: 'sleep' | 'appetite' — чуть разные формулировки под макет.
    """
    trend = 'stable'
    if current_avg is not None and prev_avg is not None:
        diff = current_avg - prev_avg
        if diff > 0.15:
            trend = 'up'
        elif diff < -0.15:
            trend = 'down'

    if current_avg is None:
        return {
            'score_avg': None,
            'trend': trend,
            'summary_key': 'no_data',
            'summary_ru': 'Нет данных за период',
        }

    if current_avg >= 2.6:
        quality = 'good'
    elif current_avg >= 1.9:
        quality = 'mixed'
    else:
        quality = 'low'

    if kind == 'sleep':
        if quality == 'good':
            if trend == 'up':
                summary_key, summary_ru = 'stable_good_up', 'стабильно хороший ↑'
            elif trend == 'down':
                summary_key, summary_ru = 'good_weakening', 'хороший, но снижается'
            else:
                summary_key, summary_ru = 'stable_good', 'стабильно хороший'
        elif quality == 'mixed':
            summary_key, summary_ru = 'unstable', 'нестабильно'
        elif trend == 'up':
            summary_key, summary_ru = 'improving', 'улучшается'
        elif trend == 'down':
            summary_key, summary_ru = 'worsening', 'ухудшается'
        else:
            summary_key, summary_ru = 'low_stable', 'ниже нормы'
    else:
        if trend == 'stable' or prev_avg is None:
            summary_key, summary_ru = 'unchanged', 'без изменений'
        elif trend == 'up':
            summary_key, summary_ru = 'improving', 'лучше чем раньше'
        elif trend == 'down':
            summary_key, summary_ru = 'worsening', 'хуже чем раньше'
        else:
            summary_key, summary_ru = 'unchanged', 'без изменений'

    return {
        'score_avg': round(current_avg, 2),
        'trend': trend,
        'summary_key': summary_key,
        'summary_ru': summary_ru,
    }


def _period_verdict(good: int, medium: int, low: int) -> dict:
    total = good + medium + low
    if total == 0:
        return {'key': 'no_data', 'label_ru': 'Нет записей за период'}
    if good >= low and good >= medium:
        if good > low + medium:
            return {'key': 'mostly_good', 'label_ru': 'В основном хороший период'}
        return {'key': 'mixed_leans_good', 'label_ru': 'Смешанно, ближе к хорошему'}
    if low > good and low >= medium:
        return {'key': 'mostly_hard', 'label_ru': 'В основном тяжёлый период'}
    if medium >= good and medium >= low:
        return {'key': 'mostly_average', 'label_ru': 'В основном средний уровень'}
    return {'key': 'mixed', 'label_ru': 'Разный уровень по дням'}


def _donut_pct(good: int, medium: int, low: int) -> dict:
    total = good + medium + low
    if total == 0:
        return {'good_pct': 0, 'medium_pct': 0, 'low_pct': 0}
    return {
        'good_pct': round(100 * good / total),
        'medium_pct': round(100 * medium / total),
        'low_pct': round(100 * low / total),
    }


@extend_schema(
    tags=['analytics'],
    summary='Справочник значений mood tracking',
    description=(
        'Возвращает варианты значений для формы ежедневного опроса.\n\n'
        '- `overall_feeling`: общее самочувствие\n'
        '- `emotions`: эмоции (мультивыбор)\n'
        '- `observations`: наблюдения (мультивыбор)\n'
        '- `sleep_quality`: качество сна\n'
        '- `appetite_quality`: качество аппетита'
    ),
)
class MoodTrackingChoicesAPIView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(
            {
                'overall_feeling': _choices_list(OverallFeeling),
                'emotions': _choices_list(Emotion),
                'observations': _choices_list(Observation),
                'sleep_quality': _choices_list(SleepQuality),
                'appetite_quality': _choices_list(AppetiteQuality),
            }
        )


@extend_schema_view(
    get=extend_schema(
        tags=['analytics'],
        summary='Список mood tracking',
        description='Возвращает список записей текущего родителя (только его дети).',
        parameters=[
            OpenApiParameter(
                name='child_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                required=False,
                description='Фильтр списка по ID ребёнка.',
            ),
        ],
    ),
    post=extend_schema(
        tags=['analytics'],
        summary='Создать mood tracking',
        description=(
            'Создаёт новую запись mood tracking.\n\n'
            '- `child` передаётся только в `request body`.\n'
            '- `child_id` в query для POST не нужен.\n'
            '- `emotions` и `observations` передаются массивами значений.'
        ),
        examples=[
            OpenApiExample(
                'Пример создания',
                value={
                    'child': 1,
                    'overall_feeling': 'normal',
                    'emotions': ['calm', 'tired'],
                    'observations': ['focused', 'played_calmly'],
                    'sleep_quality': 'good',
                    'appetite_quality': 'normal',
                    'note': 'Спокойный день, без перегрузок.',
                },
                request_only=True,
            )
        ],
    ),
)
class MoodTrackingListCreateAPIView(ListCreateAPIView):
    serializer_class = MoodTrackingSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = MoodTracking.objects.filter(child__parent__user=self.request.user)
        child_id = self.request.query_params.get('child_id')
        if child_id:
            queryset = queryset.filter(child_id=child_id)
        return queryset


@extend_schema(
    tags=['analytics'],
    summary='Детальная запись mood tracking',
    description='GET/PUT/PATCH/DELETE для одной записи mood tracking по `pk`.',
)
class MoodTrackingRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = MoodTrackingSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return MoodTracking.objects.filter(child__parent__user=self.request.user)


@extend_schema(
    tags=['analytics'],
    summary='Сводная аналитика по периоду (макет: неделя / день / месяц)',
    description=(
        'Сводка за выбранный период относительно опорной `date`.\n\n'
        '- `calendar_days`: каждый день диапазона — `mood_score` от 1 до 5 (или `null`, если нет записей). '
        'Фронт мапит score на 5 эмодзи.\n'
        '  Маппинг одной записи: very_hard→1, hard→2, normal→3, good→5; при нескольких записях за день — среднее, округление.\n'
        '- `sleep` / `appetite`: готовые подписи и `trend` (сравнение с предыдущим таким же периодом).\n'
        '- `donut`: доли «хорошее / среднее / низкое» по `overall_feeling` для круговой диаграммы.\n'
        '- `period_mood`: вердикт периода текстом.\n\n'
        'Без `child_id` — агрегация по всем детям родителя.'
    ),
    parameters=[
        OpenApiParameter(
            name='child_id',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description='ID ребёнка. Если не передан, аналитика считается по всем детям родителя.',
        ),
        OpenApiParameter(
            name='period',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Период: day, week, month. По умолчанию week.',
        ),
        OpenApiParameter(
            name='date',
            type=OpenApiTypes.DATE,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Опорная дата (YYYY-MM-DD). По умолчанию сегодня.',
        ),
    ],
)
class MoodTrackingSummaryAPIView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        period = request.query_params.get('period', 'week')
        date_param = request.query_params.get('date')
        child_id = request.query_params.get('child_id')

        try:
            anchor = _parse_anchor_date(date_param)
            start_dt, end_dt = _period_bounds(period, anchor)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=400)

        base_filter = {'child__parent__user': request.user}

        queryset = MoodTracking.objects.filter(
            **base_filter,
            created_at__range=(start_dt, end_dt),
        )
        if child_id:
            queryset = queryset.filter(child_id=child_id)

        prev_queryset = MoodTracking.objects.none()
        prev_range_dates = _previous_period_date_range(period, anchor)
        if prev_range_dates:
            ps, pe = prev_range_dates
            p_start_dt, p_end_dt = _date_range_to_dt_bounds(ps, pe)
            prev_queryset = MoodTracking.objects.filter(
                **base_filter,
                created_at__range=(p_start_dt, p_end_dt),
            )
            if child_id:
                prev_queryset = prev_queryset.filter(child_id=child_id)

        total = queryset.count()
        overall_good = queryset.filter(overall_feeling=OverallFeeling.GOOD).count()
        overall_medium = queryset.filter(overall_feeling=OverallFeeling.NORMAL).count()
        overall_low = queryset.filter(overall_feeling__in=[OverallFeeling.HARD, OverallFeeling.VERY_HARD]).count()

        by_day_scores = _group_feeling_scores_by_day(queryset)
        start_d, end_d = start_dt.date(), end_dt.date()
        calendar_days = []
        for d in _iter_dates(start_d, end_d):
            mood_score = _day_mood_score(by_day_scores, d)
            calendar_days.append(
                {
                    'date': d.isoformat(),
                    'weekday_short_ru': WEEKDAY_SHORT_RU[d.weekday()],
                    'mood_score': mood_score,
                    'has_data': mood_score is not None,
                }
            )

        sleep_counts = {
            'good': queryset.filter(sleep_quality=SleepQuality.GOOD).count(),
            'normal': queryset.filter(sleep_quality=SleepQuality.NORMAL).count(),
            'bad': queryset.filter(sleep_quality=SleepQuality.BAD).count(),
        }
        appetite_counts = {
            'good': queryset.filter(appetite_quality=AppetiteQuality.GOOD).count(),
            'normal': queryset.filter(appetite_quality=AppetiteQuality.NORMAL).count(),
            'bad': queryset.filter(appetite_quality=AppetiteQuality.BAD).count(),
        }

        sleep_avg = _avg_quality_score(queryset, 'sleep_quality')
        sleep_prev = _avg_quality_score(prev_queryset, 'sleep_quality')
        appetite_avg = _avg_quality_score(queryset, 'appetite_quality')
        appetite_prev = _avg_quality_score(prev_queryset, 'appetite_quality')

        sleep_card = _sleep_appetite_card(sleep_avg, sleep_prev, 'sleep')
        sleep_card['breakdown'] = sleep_counts
        appetite_card = _sleep_appetite_card(appetite_avg, appetite_prev, 'appetite')
        appetite_card['breakdown'] = appetite_counts

        verdict = _period_verdict(overall_good, overall_medium, overall_low)
        donut = _donut_pct(overall_good, overall_medium, overall_low)

        return Response(
            {
                'period': period,
                'date': anchor.isoformat(),
                'range': {
                    'start': start_d.isoformat(),
                    'end': end_d.isoformat(),
                },
                'total_entries': total,
                'mood_scale': {
                    'min': 1,
                    'max': 5,
                    'single_entry_map': {
                        'very_hard': 1,
                        'hard': 2,
                        'normal': 3,
                        'good': 5,
                    },
                    'note_ru': (
                        'Одна запись за день даёт 1, 2, 3 или 5. Значение 4 возможно только при усреднении '
                        'нескольких записей за один день.'
                    ),
                },
                'calendar_days': calendar_days,
                'sleep': sleep_card,
                'appetite': appetite_card,
                'donut': {
                    **donut,
                    'counts': {
                        'good': overall_good,
                        'medium': overall_medium,
                        'low': overall_low,
                    },
                },
                'period_mood': {
                    'verdict_key': verdict['key'],
                    'verdict_ru': verdict['label_ru'],
                    'counts': {
                        'good': overall_good,
                        'medium': overall_medium,
                        'low': overall_low,
                    },
                },
            }
        )
