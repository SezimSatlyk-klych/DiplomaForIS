from django.db.models import Avg
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .enums import Category, CourseTag, Level, MaterialType
from .models import Course, CourseModule, CoursePurchase, CourseReview
from .serializers import (
    CourseSerializer,
    CourseModuleSerializer,
    CourseReviewSerializer,
    CoursePurchaseSerializer,
    PublicCoursePreviewSerializer,
    PublicCourseCardSerializer,
    PublicCourseDescriptionSerializer,
    PublicCourseContentSerializer,
    PublicCourseSpecialistSerializer,
)


def _choices_list(enum_class):
    return [{'value': c.value, 'label': c.label} for c in enum_class]


_COURSE_REQUEST_BODY_GUIDE = (
    '### Что отправлять при создании/обновлении курса\n\n'
    '- **Справочники** (подписи для UI): `GET /api/courses/choices/` — там `category`, `level`, `course_tag` '
    '(массивы объектов `{ "value", "label" }`). В теле курса передавайте только **`value`**.\n'
    '- **Обязательно** при создании: `title`, `description`, `category`, `level`, `price`, `duration`, '
    '`preview_image` (файл).\n'
    '- **Необязательно**: `learning_outcomes`, `tags` (массив кодов из `course_tag`), `modules` (вложенные модули).\n'
    '- **Формат**: если есть `preview_image`, удобнее **multipart/form-data** (текстовые поля + файл). '
    'Чистый JSON без файла для создания курса обычно не подходит — превью обязательно.\n'
    '- **`id` и `specialist`**: не передавайте — `id` только в ответе, специалист берётся из авторизованного пользователя.\n'
    '- **Обновление (PUT/PATCH)**: те же поля; если передать `modules`, список модулей **полностью заменяется**.\n'
)


@extend_schema(
    tags=['courses'],
    summary='Справочники для формы курса',
    description=(
        'Подсказки для фронта: допустимые `value` для полей курса и модулей.\n\n'
        '- `category`, `level` — для тела POST/PUT/PATCH `/api/courses/`.\n'
        '- `course_tag` — коды для массива `tags`.\n'
        '- `material_type` — для модулей (`/api/courses/{id}/modules/`).'
    ),
)
class CourseChoicesAPIView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({
            'category': _choices_list(Category),
            'level': _choices_list(Level),
            'material_type': _choices_list(MaterialType),
            'course_tag': _choices_list(CourseTag),
        })


@extend_schema_view(
    get=extend_schema(
        tags=['courses'],
        summary='Список курсов текущего специалиста',
        description='Возвращает курсы, принадлежащие профилю специалиста авторизованного пользователя.',
    ),
    post=extend_schema(
        tags=['courses'],
        summary='Создать курс',
        description=_COURSE_REQUEST_BODY_GUIDE,
        examples=[
            OpenApiExample(
                'Пример полей (multipart: те же ключи + файл preview_image)',
                value={
                    'title': 'Курс моторной сферы',
                    'description': 'Развиваем координацию и мелкую моторику.',
                    'learning_outcomes': 'Ребёнок освоит базовые упражнения и сможет повторять их дома.',
                    'tags': ['for_children', 'easy_start', 'memory'],
                    'category': 'autism',
                    'level': 'beginner',
                    'price': '12000.00',
                    'duration': 12,
                },
                request_only=True,
            ),
        ],
    ),
)
class CourseListCreateAPIView(ListCreateAPIView):
    serializer_class = CourseSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        specialist = getattr(user, 'specialist', None)
        if specialist is None:
            return Course.objects.none()
        return Course.objects.filter(specialist=specialist)


@extend_schema(
    tags=['public-parent-courses'],
    summary='Превью изображений курсов',
    description=(
        'Отдаёт только список курсов и их `preview_image`.\n\n'
        'Используется фронтом, когда нужно быстро загрузить карточки без дополнительных полей.'
    ),
)
class PublicCoursePreviewListAPIView(ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PublicCoursePreviewSerializer

    def get_queryset(self):
        # Временно отключаем фильтрацию: возвращаем все доступные превью.
        queryset = Course.objects.exclude(preview_image='')
        return queryset.only('id', 'preview_image')


@extend_schema(
    tags=['public-parent-courses'],
    summary='Карточки курсов для родителей',
    description=(
        'Отдаёт компактный список для карточек: id, title, level, specialist_name, price, '
        'average_rating, purchased, preview_image.\n\n'
        'Параметры запроса (все опциональны):\n'
        '- `title`: поиск по названию курса (частичное совпадение).\n'
        '- `rating_min`: минимальный средний рейтинг (например, `4` или `4.5`).\n'
        '- `price_min`: минимальная цена курса.\n'
        '- `price_max`: максимальная цена курса.\n'
        '- `level`: уровень курса (`beginner`, `intermediate`, `advanced`).\n\n'
        'Пример:\n'
        '`/api/courses/public/cards/?title=аутизм&rating_min=4&price_min=5000&price_max=15000&level=beginner`'
    ),
    parameters=[
        OpenApiParameter(
            name='title',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Поиск по названию курса (частичное совпадение). Пример: `аутизм`.',
        ),
        OpenApiParameter(
            name='rating_min',
            type=OpenApiTypes.NUMBER,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Минимальный средний рейтинг курса. Примеры: `3`, `4`, `4.5`.',
        ),
        OpenApiParameter(
            name='price_min',
            type=OpenApiTypes.NUMBER,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Минимальная цена курса. Пример: `5000`.',
        ),
        OpenApiParameter(
            name='price_max',
            type=OpenApiTypes.NUMBER,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Максимальная цена курса. Пример: `15000`.',
        ),
        OpenApiParameter(
            name='level',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Уровень курса: `beginner`, `intermediate`, `advanced`.',
        ),
    ],
)
class PublicCourseCardsListAPIView(ListAPIView):
    serializer_class = PublicCourseCardSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = (
            Course.objects.all()
            .select_related('specialist')
            .annotate(average_rating=Avg('reviews__rating'))
        )
        rating_min = self.request.query_params.get('rating_min')
        price_min = self.request.query_params.get('price_min')
        price_max = self.request.query_params.get('price_max')
        level = self.request.query_params.get('level')
        title = self.request.query_params.get('title')

        if title:
            queryset = queryset.filter(title__icontains=title)
        if rating_min:
            queryset = queryset.filter(average_rating__gte=rating_min)
        if price_min:
            queryset = queryset.filter(price__gte=price_min)
        if price_max:
            queryset = queryset.filter(price__lte=price_max)
        if level:
            queryset = queryset.filter(level=level)
        return queryset


@extend_schema(
    tags=['public-parent-courses'],
    summary='Карточка курса по ID',
    description='Возвращает одну карточку курса для указанного `course_id`.',
)
class PublicCourseCardRetrieveAPIView(RetrieveAPIView):
    serializer_class = PublicCourseCardSerializer
    permission_classes = (IsAuthenticated,)
    lookup_url_kwarg = 'course_id'

    def get_queryset(self):
        return (
            Course.objects.all()
            .select_related('specialist')
            .annotate(average_rating=Avg('reviews__rating'))
        )


@extend_schema(
    tags=['public-parent-courses'],
    summary='Описание курса (вкладка «Описание»)',
    description=(
        'Возвращает описание курса, результаты обучения (`learning_outcomes`) '
        'и тэги с `value`/`label` для указанного `course_id`.'
    ),
)
class PublicCourseDescriptionAPIView(RetrieveAPIView):
    serializer_class = PublicCourseDescriptionSerializer
    permission_classes = (IsAuthenticated,)
    lookup_url_kwarg = 'course_id'
    queryset = Course.objects.all()


@extend_schema(
    tags=['public-parent-courses'],
    summary='Содержание курса (вкладка «Содержание»)',
    description=(
        'Возвращает список модулей курса (название, тип материала), '
        'общее кол-во модулей и продолжительность курса.'
    ),
)
class PublicCourseContentAPIView(RetrieveAPIView):
    serializer_class = PublicCourseContentSerializer
    permission_classes = (IsAuthenticated,)
    lookup_url_kwarg = 'course_id'

    def get_queryset(self):
        return Course.objects.prefetch_related('modules')


@extend_schema(
    tags=['public-parent-courses'],
    summary='Специалист курса (вкладка «Специалист»)',
    description=(
        'Возвращает данные специалиста курса: имя, аватар, специализации, '
        'стаж и описание подхода.'
    ),
)
class PublicCourseSpecialistAPIView(GenericAPIView):
    serializer_class = PublicCourseSpecialistSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request, course_id):
        course = get_object_or_404(
            Course.objects.select_related('specialist', 'specialist__description'),
            pk=course_id,
        )
        serializer = self.get_serializer(course.specialist)
        return Response(serializer.data)


@extend_schema_view(
    get=extend_schema(
        tags=['courses'],
        summary='Получить курс',
        description='Один курс специалиста по `pk` (только свои курсы).',
    ),
    put=extend_schema(
        tags=['courses'],
        summary='Полное обновление курса',
        description=_COURSE_REQUEST_BODY_GUIDE,
        examples=[
            OpenApiExample(
                'Пример полей (multipart при смене превью)',
                value={
                    'title': 'Курс моторной сферы',
                    'description': 'Обновлённое описание.',
                    'learning_outcomes': 'Новые формулировки результатов обучения.',
                    'tags': ['structured_classes', 'gradual_development'],
                    'category': 'speech_therapy',
                    'level': 'intermediate',
                    'price': '15000.00',
                    'duration': 20,
                },
                request_only=True,
            ),
        ],
    ),
    patch=extend_schema(
        tags=['courses'],
        summary='Частичное обновление курса',
        description=_COURSE_REQUEST_BODY_GUIDE + '\n\nПередайте только изменяемые поля.',
    ),
    delete=extend_schema(
        tags=['courses'],
        summary='Удалить курс',
    ),
)
class CourseRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = CourseSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        specialist = getattr(user, 'specialist', None)
        if specialist is None:
            return Course.objects.none()
        return Course.objects.filter(specialist=specialist)


@extend_schema(tags=['course-modules'])
class CourseModuleListCreateAPIView(ListCreateAPIView):
    serializer_class = CourseModuleSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        specialist = getattr(user, 'specialist', None)
        if specialist is None:
            return CourseModule.objects.none()
        return CourseModule.objects.filter(course__specialist=specialist, course_id=self.kwargs['course_id'])

    def perform_create(self, serializer):
        user = self.request.user
        specialist = getattr(user, 'specialist', None)
        course = Course.objects.get(pk=self.kwargs['course_id'], specialist=specialist)
        serializer.save(course=course)


@extend_schema(tags=['course-modules'])
class CourseModuleRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = CourseModuleSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        specialist = getattr(user, 'specialist', None)
        if specialist is None:
            return CourseModule.objects.none()
        return CourseModule.objects.filter(course__specialist=specialist, course_id=self.kwargs['course_id'])


@extend_schema(tags=['course-reviews'])
class CourseReviewListCreateAPIView(ListCreateAPIView):
    serializer_class = CourseReviewSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        get_object_or_404(Course, pk=course_id)
        return CourseReview.objects.filter(course_id=course_id)

    def perform_create(self, serializer):
        course = get_object_or_404(Course, pk=self.kwargs['course_id'])
        serializer.save(course=course, user=self.request.user)


@extend_schema(tags=['courses'])
class CoursePurchaseCreateAPIView(GenericAPIView):
    serializer_class = CoursePurchaseSerializer
    permission_classes = (IsAuthenticated,)

    def post(self, request, course_id):
        course = get_object_or_404(Course, pk=course_id)
        if CoursePurchase.objects.filter(course=course, user=request.user).exists():
            return Response(
                {'detail': 'Вы уже приобрели этот курс.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        purchase = CoursePurchase.objects.create(course=course, user=request.user)
        serializer = self.get_serializer(purchase)
        return Response(serializer.data, status=status.HTTP_201_CREATED)