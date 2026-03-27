from datetime import date, datetime, time, timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
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
    summary='Сводная аналитика по периоду',
    description=(
        'Возвращает агрегированную аналитику mood tracking по периоду (`day`, `week`, `month`).\n\n'
        'В ответе:\n'
        '- `overall_state`: количество good/medium/low\n'
        '- `sleep`: распределение качества сна\n'
        '- `appetite`: распределение аппетита\n'
        '- `by_days`: разбивка по дням для построения графиков\n\n'
        'Если `child_id` не передан, агрегируется по всем детям текущего родителя.'
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

        queryset = MoodTracking.objects.filter(
            child__parent__user=request.user,
            created_at__range=(start_dt, end_dt),
        )
        if child_id:
            queryset = queryset.filter(child_id=child_id)

        total = queryset.count()
        overall_good = queryset.filter(overall_feeling=OverallFeeling.GOOD).count()
        overall_medium = queryset.filter(overall_feeling=OverallFeeling.NORMAL).count()
        overall_low = queryset.filter(overall_feeling__in=[OverallFeeling.HARD, OverallFeeling.VERY_HARD]).count()

        by_days = list(
            queryset.annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(
                total=Count('id'),
                good=Count('id', filter=Q(overall_feeling=OverallFeeling.GOOD)),
                medium=Count('id', filter=Q(overall_feeling=OverallFeeling.NORMAL)),
                low=Count('id', filter=Q(overall_feeling__in=[OverallFeeling.HARD, OverallFeeling.VERY_HARD])),
            )
            .order_by('day')
        )
        for row in by_days:
            row['day'] = row['day'].isoformat()

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

        return Response(
            {
                'period': period,
                'date': anchor.isoformat(),
                'range': {
                    'start': start_dt.date().isoformat(),
                    'end': end_dt.date().isoformat(),
                },
                'total_entries': total,
                'overall_state': {
                    'good': overall_good,
                    'medium': overall_medium,
                    'low': overall_low,
                },
                'sleep': sleep_counts,
                'appetite': appetite_counts,
                'by_days': by_days,
            }
        )
