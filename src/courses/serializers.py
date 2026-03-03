from rest_framework import serializers

from .models import Course, CourseModule


class CourseModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseModule
        fields = ('id', 'title', 'description', 'material_type', 'file', 'created_at')
        read_only_fields = ('id', 'created_at')


class CourseSerializer(serializers.ModelSerializer):
    modules = CourseModuleSerializer(many=True, required=False)

    class Meta:
        model = Course
        fields = (
            'id',
            'title',
            'description',
            'category',
            'level',
            'price',
            'duration',
            'preview_image',
            'modules',
        )
        read_only_fields = ('id',)

    def _get_specialist(self):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        specialist = getattr(user, 'specialist', None)
        if specialist is None:
            raise serializers.ValidationError(
                {'non_field_errors': ['Сначала создайте профиль специалиста, чтобы добавлять курсы.']}
            )
        return specialist

    def create(self, validated_data):
        modules_data = validated_data.pop('modules', [])
        specialist = self._get_specialist()
        course = Course.objects.create(specialist=specialist, **validated_data)
        for module_data in modules_data:
            CourseModule.objects.create(course=course, **module_data)
        return course

    def update(self, instance, validated_data):
        modules_data = validated_data.pop('modules', None)
        course = super().update(instance, validated_data)
        if modules_data is not None:
            course.modules.all().delete()
            for module_data in modules_data:
                CourseModule.objects.create(course=course, **module_data)
        return course

