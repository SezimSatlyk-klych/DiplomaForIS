from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Min, Q, Sum
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.generics import (
    GenericAPIView,
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .enums import (
    BehaviorNotice,
    ComfortableDuration,
    CommunicationStyle,
    DevelopmentType,
    Interest,
    Language,
    Method,
    Motivator,
    MotorDifficulty,
    Sensitivity,
    SpecialistDevelopmentType,
    Specialization,
    UnderstandsInstructions,
    WorkFormat,
)
from .models import Child, Specialist, SpecialistDescription, UserProfile
from courses.models import Course, CoursePurchase, CourseReview
from courses.serializers import PublicCourseCardSerializer
from .serializers import (
    ChildSerializer,
    ProfileSerializer,
    RegisterSerializer,
    SpecialistDescriptionSerializer,
    SpecialistSerializer,
    PublicSpecialistCardSerializer,
)


def _choices_list(enum_class):
    return [{'value': c.value, 'label': c.label} for c in enum_class]


def _specialization_values_matching_label_substring(text: str) -> list[str]:
    """Коды enum, у которых label содержит подстроку (для текстового поиска по специализации)."""
    needle = (text or '').strip().lower()
    if not needle:
        return []
    return [c.value for c in Specialization if needle in c.label.lower()]


def _public_specialist_cards_query_docs() -> str:
    """Текст для OpenAPI: параметры и соответствие value ↔ label для фронта."""
    pairs = '\n'.join(f'- `{c.value}` — «{c.label}»' for c in Specialization)
    return (
        '**Эндпоинт:** `GET /api/auth/public/specialists/cards/` (JWT).\n\n'
        '**Ответ:** список карточек с полями `id`, `full_name`, `specialization` (label первой '
        'специализации в профиле), `avatar`, `average_rating`, `reviews_count`, `years_experience`, '
        '`price_from`, `currency`, `short_description`.\n\n'
        '**Query-параметры** (все необязательны; если передать оба, условия объединяются по **И**):\n\n'
        '| Параметр | Тип | Назначение |\n'
        '|----------|-----|------------|\n'
        '| `q` | string | Поиск по **имени** специалиста (`full_name`, частичное совпадение, регистр не важен). |\n'
        '| `specialization_search` | string | Поиск по **специализации**: текст ищется как подстрока '
        'в **подписях** (`label`) из справочника ниже. Регистр не важен. Если подстрока не входит '
        'ни в один label — вернётся пустой список. |\n\n'
        'Коды (`value`) ниже — для справки и совпадения с '
        '`GET /api/auth/specialist/description/choices/` → `specializations`; в запросе передаётся '
        'только произвольная строка в `specialization_search`.\n\n'
        '**Подписи для `specialization_search` (подстрока ищется в «label»):**\n'
        f'{pairs}'
    )


User = get_user_model()


@extend_schema(tags=['auth'])
class RegisterAPIView(GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {'message': 'Пользователь успешно зарегистрирован.', 'user_id': user.id},
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=['profile'])
class ProfileAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return UserProfile.objects.get(user=self.request.user)

    def get(self, request, *args, **kwargs):
        """Получить свой профиль (пользователь определяется по JWT, email из регистрации)."""
        try:
            instance = self.get_object()
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': 'Профиль не найден. Создайте его через POST.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """Создать профиль: full_name, relationship (mom|dad|guardian|other), relationship_other при other."""
        if UserProfile.objects.filter(user=request.user).exists():
            return Response(
                {'detail': 'Профиль уже создан. Используйте PUT или PATCH для изменения.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, *args, **kwargs):
        """Обновить профиль полностью."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        """Обновить профиль частично."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        """Удалить свой профиль."""
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['specialist'])
class SpecialistAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = SpecialistSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return Specialist.objects.get(user=self.request.user)

    def get(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
        except Specialist.DoesNotExist:
            return Response(
                {'detail': 'Профиль специалиста не найден. Создайте его через POST.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if Specialist.objects.filter(user=request.user).exists():
            return Response(
                {'detail': 'Профиль специалиста уже создан. Используйте PUT или PATCH для изменения.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['specialist'])
class SpecialistDashboardAPIView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            specialist = request.user.specialist
        except Specialist.DoesNotExist:
            return Response(
                {'detail': 'Сначала создайте профиль специалиста (POST /api/auth/specialist/).'},
                status=status.HTTP_403_FORBIDDEN,
            )
        total_courses = Course.objects.filter(specialist=specialist).count()
        purchases_qs = CoursePurchase.objects.filter(course__specialist=specialist)
        total_purchases = purchases_qs.count()
        total_profit_result = purchases_qs.aggregate(s=Sum('course__price'))
        total_profit = total_profit_result['s'] or 0
        avg_rating_result = CourseReview.objects.filter(course__specialist=specialist).aggregate(a=Avg('rating'))
        average_rating = avg_rating_result['a']
        if average_rating is not None:
            average_rating = round(float(average_rating), 1)
        return Response({
            'full_name': specialist.full_name,
            'total_courses': total_courses,
            'total_purchases': total_purchases,
            'total_profit': str(total_profit),
            'average_rating': average_rating,
        })


@extend_schema(tags=['specialist-description'])
class SpecialistDescriptionAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = SpecialistDescriptionSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return SpecialistDescription.objects.get(specialist__user=self.request.user)

    def get(self, request, *args, **kwargs):
        try:
            request.user.specialist
        except Specialist.DoesNotExist:
            return Response(
                {'detail': 'Сначала создайте профиль специалиста (POST /api/auth/specialist/).'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            instance = self.get_object()
        except SpecialistDescription.DoesNotExist:
            return Response(
                {'detail': 'Описание не найдено. Создайте его через POST.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        try:
            specialist = request.user.specialist
        except Specialist.DoesNotExist:
            return Response(
                {'detail': 'Сначала создайте профиль специалиста (POST /api/auth/specialist/).'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if SpecialistDescription.objects.filter(specialist=specialist).exists():
            return Response(
                {'detail': 'Описание уже создано. Используйте PUT или PATCH для изменения.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['specialist-description'])
class SpecialistDescriptionChoicesAPIView(GenericAPIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        """Варианты для полей создания/редактирования описания специалиста. Мультивыбор: в теле передавать массив value."""
        return Response({
            'specializations': _choices_list(Specialization),
            'methods': _choices_list(Method),
            'work_format': _choices_list(WorkFormat),
            'languages': _choices_list(Language),
            'development_types': _choices_list(SpecialistDevelopmentType),
        })


@extend_schema(tags=['children'])
class ChildChoicesAPIView(GenericAPIView):
    permission_classes = (AllowAny,)

    def get(self, request):
        """Варианты для полей создания/редактирования ребёнка. Мультивыбор: в теле запроса передавать массив value."""
        return Response({
            'development_type': _choices_list(DevelopmentType),
            'communication_style': _choices_list(CommunicationStyle),
            'understands_instructions': _choices_list(UnderstandsInstructions),
            'comfortable_duration': _choices_list(ComfortableDuration),
            'sensory_sensitivities': _choices_list(Sensitivity),
            'motor_difficulties': _choices_list(MotorDifficulty),
            'behavior_notices': _choices_list(BehaviorNotice),
            'motivators': _choices_list(Motivator),
            'interests': _choices_list(Interest),
        })


@extend_schema(tags=['children'])
class ChildListCreateAPIView(ListCreateAPIView):
    serializer_class = ChildSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Child.objects.filter(parent__user=self.request.user)


@extend_schema(tags=['children'])
class ChildDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = ChildSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return Child.objects.filter(parent__user=self.request.user)


@extend_schema(
    tags=['public-parent-specialists'],
    summary='Карточки специалистов',
    description=_public_specialist_cards_query_docs(),
    parameters=[
        OpenApiParameter(
            name='q',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description='Поиск по ФИО специалиста (icontains).',
            examples=[OpenApiExample('По части имени', value='алина')],
        ),
        OpenApiParameter(
            name='specialization_search',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description=(
                'Текстовый поиск по специализации: подстрока без учёта регистра в **label** '
                '(список value ↔ label в описании эндпоинта).'
            ),
            examples=[
                OpenApiExample('Как в UI «Логопед»', value='логопед'),
                OpenApiExample('Часть названия', value='нейро'),
            ],
        ),
    ],
)
class PublicSpecialistCardsListAPIView(ListAPIView):
    serializer_class = PublicSpecialistCardSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = (
            Specialist.objects.all()
            .select_related('description')
            .annotate(
                average_rating=Avg('courses__reviews__rating'),
                reviews_count=Count('courses__reviews'),
                price_from=Min('courses__price'),
            )
        )

        q = self.request.query_params.get('q')
        specialization_search = self.request.query_params.get('specialization_search')

        if q:
            queryset = queryset.filter(full_name__icontains=q)
        if specialization_search and specialization_search.strip():
            codes = _specialization_values_matching_label_substring(specialization_search)
            if not codes:
                queryset = queryset.none()
            else:
                spec_q = Q()
                for code in codes:
                    spec_q |= Q(description__specializations__contains=[code])
                queryset = queryset.filter(spec_q)

        return queryset.order_by('full_name')


@extend_schema(
    tags=['public-parent-specialists'],
    summary='Курсы специалиста',
    description=(
        'Список курсов по `specialist_id`. Формат элементов как у `GET /api/courses/public/cards/`. '
        '**404**, если специалиста нет.'
    ),
)
class PublicSpecialistCoursesListAPIView(ListAPIView):
    serializer_class = PublicCourseCardSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        specialist_id = self.kwargs['specialist_id']
        if not Specialist.objects.filter(pk=specialist_id).exists():
            raise NotFound('Специалист не найден.')
        return (
            Course.objects.filter(specialist_id=specialist_id)
            .select_related('specialist')
            .annotate(average_rating=Avg('reviews__rating'))
            .order_by('id')
        )


@extend_schema(
    tags=['public-parent-specialists'],
    summary='Карточка специалиста по ID',
    description='Та же компактная карточка, что и в списке: одна запись по `specialist_id`.',
)
class PublicSpecialistCardRetrieveAPIView(RetrieveAPIView):
    serializer_class = PublicSpecialistCardSerializer
    permission_classes = (IsAuthenticated,)
    lookup_url_kwarg = 'specialist_id'

    def get_queryset(self):
        return (
            Specialist.objects.all()
            .select_related('description')
            .annotate(
                average_rating=Avg('courses__reviews__rating'),
                reviews_count=Count('courses__reviews'),
                price_from=Min('courses__price'),
            )
        )
