from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Sum
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
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
from .serializers import (
    ChildSerializer,
    ProfileSerializer,
    RegisterSerializer,
    SpecialistDescriptionSerializer,
    SpecialistSerializer,
    PublicSpecialistSerializer,
    PublicSpecialistAvatarSerializer,
)


def _choices_list(enum_class):
    return [{'value': c.value, 'label': c.label} for c in enum_class]

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


# TODO: вернусь позже, пока не актуально.
# @extend_schema(
#     tags=['public-parent-specialists'],
#     summary='Список специалистов для родителей',
#     description=(
#         'Используется для вкладки "Специалисты" на стороне родителя.\n\n'
#         '- Поиск по имени специалиста (`q`)\n'
#         '- Фильтр по городу, формату работы, специализациям\n'
#         '- Возвращает средний рейтинг и количество курсов специалиста.'
#     ),
#     parameters=[
#         OpenApiParameter(
#             name='q',
#             type=OpenApiTypes.STR,
#             location=OpenApiParameter.QUERY,
#             required=False,
#             description='Поиск по имени/фамилии специалиста (частичное совпадение).',
#         ),
#         OpenApiParameter(
#             name='city',
#             type=OpenApiTypes.STR,
#             location=OpenApiParameter.QUERY,
#             required=False,
#             description='Фильтр по городу (поле description.city).',
#         ),
#         OpenApiParameter(
#             name='work_format',
#             type=OpenApiTypes.STR,
#             location=OpenApiParameter.QUERY,
#             required=False,
#             description='Фильтр по формату работы: online/offline (значения из `accounts.enums.WorkFormat`).',
#         ),
#         OpenApiParameter(
#             name='specialization',
#             type=OpenApiTypes.STR,
#             location=OpenApiParameter.QUERY,
#             required=False,
#             description='Фильтр по специализации (значение из `accounts.enums.Specialization` в description.specializations).',
#         ),
#         OpenApiParameter(
#             name='min_rating',
#             type=OpenApiTypes.NUMBER,
#             location=OpenApiParameter.QUERY,
#             required=False,
#             description='Минимальный средний рейтинг специалиста (1–5).',
#         ),
#     ],
# )
# class ParentSpecialistListAPIView(ListAPIView):
#
#     serializer_class = PublicSpecialistSerializer
#     permission_classes = (IsAuthenticated,)
#
#     def get_queryset(self):
#         queryset = (
#             Specialist.objects.all()
#             .select_related('description')
#             .annotate(
#                 average_rating=Avg('courses__reviews__rating'),
#                 total_courses=Count('courses', distinct=True),
#             )
#         )
#
#         query = self.request.query_params.get('q')
#         city = self.request.query_params.get('city')
#         work_format = self.request.query_params.get('work_format')
#         specialization = self.request.query_params.get('specialization')
#         min_rating = self.request.query_params.get('min_rating')
#
#         if query:
#             queryset = queryset.filter(full_name__icontains=query)
#         if city:
#             queryset = queryset.filter(description__city__icontains=city)
#         if work_format:
#             queryset = queryset.filter(description__work_format=work_format)
#         if specialization:
#             queryset = queryset.filter(description__specializations__contains=[specialization])
#         if min_rating:
#             queryset = queryset.filter(average_rating__gte=min_rating)
#
#         return queryset
#
#
# @extend_schema(
#     tags=['public-parent-specialists'],
#     summary='Аватары специалистов (только изображения)',
#     description='Отдаёт только список специалистов и их `avatar` (id + ссылка на картинку).',
# )
# class ParentSpecialistAvatarListAPIView(ListAPIView):
#     serializer_class = PublicSpecialistAvatarSerializer
#     permission_classes = (IsAuthenticated,)
#
#     def get_queryset(self):
#         return Specialist.objects.exclude(avatar__isnull=True).exclude(avatar='').only('id', 'avatar')
