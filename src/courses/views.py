from drf_spectacular.utils import extend_schema
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .enums import Category, Level, MaterialType
from .models import Course, CourseModule
from .serializers import CourseSerializer, CourseModuleSerializer


def _choices_list(enum_class):
    return [{'value': c.value, 'label': c.label} for c in enum_class]


@extend_schema(tags=['courses'])
class CourseChoicesAPIView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({
            'category': _choices_list(Category),
            'level': _choices_list(Level),
            'material_type': _choices_list(MaterialType),
        })


@extend_schema(tags=['courses'])
class CourseListCreateAPIView(ListCreateAPIView):
    serializer_class = CourseSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        specialist = getattr(user, 'specialist', None)
        if specialist is None:
            return Course.objects.none()
        return Course.objects.filter(specialist=specialist)


@extend_schema(tags=['courses'])
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