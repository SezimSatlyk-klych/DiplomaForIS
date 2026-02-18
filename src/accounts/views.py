from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
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
from .serializers import (
    ChildSerializer,
    ProfileSerializer,
    RegisterSerializer,
    SpecialistDescriptionSerializer,
    SpecialistSerializer,
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
