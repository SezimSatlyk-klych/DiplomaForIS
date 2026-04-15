import logging

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Min, Q, Sum
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiTypes, extend_schema, extend_schema_view
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
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

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
from .models import Child, ParentAddress, Specialist, SpecialistDescription, UserProfile
from courses.models import Course, CoursePurchase, CourseReview
from courses.serializers import PublicCourseCardSerializer
from .auth_utils import resolve_user_type
from .password_reset import RESEND_SECONDS, request_reset_code, reset_password_with_token, verify_code
from .serializers import (
    ChangePasswordSerializer,
    ChildSerializer,
    ParentAddressSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
    ProfileSerializer,
    RegisterSerializer,
    SpecialistDescriptionSerializer,
    SpecialistSerializer,
    SpecialistSettingsSerializer,
    PublicSpecialistCardSerializer,
    PublicSpecialistDetailSerializer,
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

_PARENT_AVATAR_NOTE = (
    'Поле **`avatar`** (файл): при загрузке используйте **multipart/form-data** вместе с остальными полями '
    'или только `avatar` для смены фото. В ответах `avatar` — абсолютный URL либо `null`.'
)

_SPECIALIST_AVATAR_NOTE = (
    'Поле **`avatar`**: как у родителя — **multipart/form-data** для загрузки; в JSON-запросах без файла '
    'поле не передаётся. Ответ: абсолютный URL или `null`.'
)


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


@extend_schema(
    tags=['auth'],
    summary='Вход (JWT)',
    description=(
        'Тело: `username` — **email**, как при регистрации; `password`.\n\n'
        'В ответе: `access`, `refresh` и **`user_type`** — `parent` (профиль родителя), '
        '`specialist`, `both` (оба профиля) или `none` (ещё ни родитель, ни специалист). '
        'То же значение добавлено в claims access-токена (`user_type`).'
    ),
)
class LoginAPIView(TokenObtainPairView):
    pass


@extend_schema(
    tags=['password-reset'],
    summary='Запросить код на почту',
    description=(
        'Шаг 1 (как в макете «Забыли пароль»): передать `email`. '
        'Если аккаунт с такой почтой есть, на неё уйдёт **4-значный код**. '
        'Ответ одинаковый, зарегистрирована почта или нет — чтобы не раскрывать наличие пользователя.\n\n'
        'Повторная отправка на ту же почту раньше чем через `resend_after_seconds` секунд вернёт **429** '
        'и поле `retry_after_seconds` для таймера «Отправить код ещё раз».'
    ),
)
class PasswordResetRequestAPIView(GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            ok, retry_after = request_reset_code(email)
        except Exception:
            logging.exception('password_reset: send mail failed for %s', email)
            return Response(
                {'detail': 'Не удалось отправить письмо. Проверьте настройки SMTP или попробуйте позже.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if not ok:
            return Response(
                {
                    'detail': 'Повторная отправка возможна позже.',
                    'retry_after_seconds': retry_after,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        return Response(
            {
                'detail': 'Если указанная почта зарегистрирована, мы отправили на неё код.',
                'resend_after_seconds': RESEND_SECONDS,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=['password-reset'],
    summary='Проверить код из письма',
    description=(
        'Шаг 2: `email` и `code` (4 цифры). При успехе вернётся `reset_token` — передайте его на шаг 3. '
        'Токен ограничен по времени (см. настройки сервера).'
    ),
)
class PasswordResetVerifyAPIView(GenericAPIView):
    serializer_class = PasswordResetVerifySerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token, err = verify_code(
            serializer.validated_data['email'],
            serializer.validated_data['code'],
        )
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'reset_token': token}, status=status.HTTP_200_OK)


@extend_schema(
    tags=['password-reset'],
    summary='Новый пароль и вход',
    description=(
        'Шаг 3: `reset_token` с шага проверки кода, `new_password` и `new_password_confirm`. '
        'Требования к паролю как в приложении: не короче 8 символов и хотя бы одна цифра.\n\n'
        'В ответе — JWT `access`, `refresh` и **`user_type`** (как после логина).'
    ),
)
class PasswordResetConfirmAPIView(GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = (AllowAny,)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, err = reset_password_with_token(
            serializer.validated_data['reset_token'],
            serializer.validated_data['new_password'],
        )
        if err:
            return Response({'detail': err}, status=status.HTTP_400_BAD_REQUEST)
        refresh = RefreshToken.for_user(user)
        ut = resolve_user_type(user)
        refresh.access_token['user_type'] = ut
        return Response(
            {
                'detail': 'Пароль обновлён.',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user_type': ut,
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    get=extend_schema(
        tags=['profile'],
        summary='Профиль родителя: получить',
        description='Данные профиля текущего пользователя-родителя, включая `avatar` (URL или null).',
    ),
    post=extend_schema(
        tags=['profile'],
        summary='Профиль родителя: создать',
        description=(
            'Тело: `full_name`, `relationship` (mom|dad|guardian|other), при other — `relationship_other`. '
            'Опционально файл **`avatar`**. ' + _PARENT_AVATAR_NOTE
        ),
    ),
    put=extend_schema(
        tags=['profile'],
        summary='Профиль родителя: полное обновление (PUT)',
        description='Все обязательные поля профиля; опционально **`avatar`**. ' + _PARENT_AVATAR_NOTE,
    ),
    patch=extend_schema(
        tags=['profile'],
        summary='Профиль родителя: частичное обновление (PATCH)',
        description='Любое подмножество полей, в том числе только **`avatar`**. ' + _PARENT_AVATAR_NOTE,
    ),
    delete=extend_schema(tags=['profile'], summary='Профиль родителя: удалить'),
)
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
        if Specialist.objects.filter(user=request.user).exists():
            return Response(
                {'detail': 'Вы зарегистрированы как специалист. Специалист не может быть родителем.'},
                status=status.HTTP_403_FORBIDDEN,
            )
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


@extend_schema_view(
    get=extend_schema(
        tags=['specialist'],
        summary='Профиль специалиста: получить',
        description='Включая **`avatar`** (абсолютный URL или null).',
    ),
    post=extend_schema(
        tags=['specialist'],
        summary='Профиль специалиста: создать',
        description=(
            'Поля: `full_name`, опционально `approach_description`, опционально файл **`avatar`**. '
            + _SPECIALIST_AVATAR_NOTE
        ),
    ),
    put=extend_schema(
        tags=['specialist'],
        summary='Профиль специалиста: полное обновление (PUT)',
        description='Все поля сериализатора; опционально **`avatar`**. ' + _SPECIALIST_AVATAR_NOTE,
    ),
    patch=extend_schema(
        tags=['specialist'],
        summary='Профиль специалиста: частичное обновление (PATCH)',
        description='Любое подмножество полей, в том числе только **`avatar`**. ' + _SPECIALIST_AVATAR_NOTE,
    ),
    delete=extend_schema(tags=['specialist'], summary='Профиль специалиста: удалить'),
)
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
        if UserProfile.objects.filter(user=request.user).exists():
            return Response(
                {'detail': 'Вы зарегистрированы как родитель. Родитель не может быть специалистом.'},
                status=status.HTTP_403_FORBIDDEN,
            )
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
        return Child.objects.filter(parent__user=self.request.user).order_by('id')

    def list(self, request, *args, **kwargs):
        first = self.get_queryset().first()
        if first is None:
            return Response([])
        serializer = self.get_serializer(first)
        return Response([serializer.data])

    def create(self, request, *args, **kwargs):
        try:
            parent = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': 'Сначала создайте профиль родителя (POST /api/auth/profile/).'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if parent.children.exists():
            return Response(
                {'detail': 'Можно добавить только одного ребёнка.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)


@extend_schema(tags=['children'])
class ChildDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = ChildSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        first = (
            Child.objects.filter(parent__user=self.request.user)
            .order_by('id')
            .values_list('pk', flat=True)
            .first()
        )
        if first is None:
            return Child.objects.none()
        return Child.objects.filter(pk=first)


@extend_schema_view(
    get=extend_schema(
        tags=['settings'],
        summary='Профиль родителя (настройки): GET',
        description='Те же поля, что и `GET /api/auth/profile/`, включая **`avatar`**.',
    ),
    put=extend_schema(
        tags=['settings'],
        summary='Профиль родителя (настройки): PUT',
        description=(
            'Частичное обновление: передайте только изменяемые поля (`full_name`, `relationship`, '
            '`relationship_other`, файл **`avatar`**). ' + _PARENT_AVATAR_NOTE
        ),
    ),
    patch=extend_schema(
        tags=['settings'],
        summary='Профиль родителя (настройки): PATCH',
        description='Синоним PUT для экрана настроек (частичное обновление). ' + _PARENT_AVATAR_NOTE,
    ),
)
class ParentSettingsProfileAPIView(GenericAPIView):
    serializer_class = ProfileSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': 'Профиль родителя не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    def put(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': 'Профиль родителя не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        return self.put(request)


@extend_schema(
    tags=['settings'],
    summary='Ребёнок родителя (настройки)',
    description='GET — получить данные ребёнка. PUT — обновить.',
)
class ParentSettingsChildAPIView(GenericAPIView):
    serializer_class = ChildSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': 'Профиль родителя не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        child = Child.objects.filter(parent=profile).order_by('id').first()
        if child is None:
            return Response(
                {'detail': 'Ребёнок не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(child)
        return Response(serializer.data)

    def put(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': 'Профиль родителя не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        child = Child.objects.filter(parent=profile).order_by('id').first()
        if child is None:
            return Response(
                {'detail': 'Ребёнок не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(child, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema(
    tags=['settings'],
    summary='Профиль специалиста (настройки)',
    description=(
        'GET — полный профиль: аккаунт + информация + работа + **`avatar`** (URL).\n\n'
        'PUT — любое подмножество полей: `full_name`, '
        '`approach_description`, **`avatar`** (файл, multipart), `specializations`, `years_experience`, '
        '`methods`, `age_range`, `work_format`, `time_zone`, `city`.\n\n'
        'Если нужны и JSON-массивы (`specializations`, `methods`), и фото в одном запросе — '
        'используйте **multipart** и передавайте массивы JSON-строками в полях формы; '
        'либо обновите текстовые поля JSON-запросом, а фото отдельным multipart.\n\n'
        + _SPECIALIST_AVATAR_NOTE
        + '\n\nПодсказки по формату:\n'
        '- `approach_description`: свободный текст (обычно 3-5 предложений о подходе).\n'
        '- `specializations`: массив кодов из `GET /api/auth/specialist/description/choices/` -> '
        '`specializations[].value`, например `["speech_therapist", "aba"]`.\n'
        '- `methods`: массив кодов из `GET /api/auth/specialist/description/choices/` -> '
        '`methods[].value`, например `["aba", "dir_floortime"]`.\n'
        '- `work_format`: один код из choices (`online` или `offline`) либо `null`.\n'
        '- `years_experience`: целое число лет опыта (можно `null`).\n'
        '- `age_range`, `time_zone`, `city`: строки.\n\n'
        'Пример тела PUT:\n'
        '{\n'
        '  "full_name": "Алина Захарова",\n'
        '  "approach_description": "Работаю с детьми 3-10 лет, делаю упор на речь и коммуникацию.",\n'
        '  "specializations": ["speech_therapist", "neuropsychologist"],\n'
        '  "years_experience": 7,\n'
        '  "methods": ["aba", "dir_floortime"],\n'
        '  "age_range": "3-10",\n'
        '  "work_format": "online",\n'
        '  "time_zone": "Asia/Almaty",\n'
        '  "city": "Алматы"\n'
        '}'
    ),
)
class SpecialistSettingsProfileAPIView(GenericAPIView):
    serializer_class = SpecialistSettingsSerializer
    permission_classes = (IsAuthenticated,)

    def _get_specialist(self, request):
        try:
            return Specialist.objects.select_related('description').get(user=request.user)
        except Specialist.DoesNotExist:
            return None

    def get(self, request):
        specialist = self._get_specialist(request)
        if specialist is None:
            return Response(
                {'detail': 'Профиль специалиста не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(specialist)
        return Response(serializer.data)

    def put(self, request):
        specialist = self._get_specialist(request)
        if specialist is None:
            return Response(
                {'detail': 'Профиль специалиста не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(specialist, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(self.get_serializer(specialist).data)


@extend_schema(
    tags=['settings'],
    summary='Адрес родителя',
    description='GET — получить адрес. POST — сохранить адрес (можно один раз, потом PUT для изменения).',
)
class ParentSettingsAddressAPIView(GenericAPIView):
    serializer_class = ParentAddressSerializer
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': 'Профиль родителя не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            addr = profile.address_info
        except ParentAddress.DoesNotExist:
            return Response(
                {'detail': 'Адрес не указан.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(addr)
        return Response(serializer.data)

    def post(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': 'Сначала создайте профиль родителя.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if ParentAddress.objects.filter(profile=profile).exists():
            return Response(
                {'detail': 'Адрес уже указан. Используйте PUT для изменения.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request):
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {'detail': 'Профиль родителя не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            addr = profile.address_info
        except ParentAddress.DoesNotExist:
            return Response(
                {'detail': 'Адрес не найден. Сначала создайте через POST.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(addr, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema(
    tags=['settings'],
    summary='Смена пароля',
    description='PUT — сменить пароль. Требуется старый пароль и новый с подтверждением.',
)
class ChangePasswordAPIView(GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'detail': 'Пароль успешно изменён.'})


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
    description='Детальная информация о специалисте для экрана профиля по `specialist_id`.',
)
class PublicSpecialistCardRetrieveAPIView(RetrieveAPIView):
    serializer_class = PublicSpecialistDetailSerializer
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
