from rest_framework import serializers

from .models import Course, CourseModule, CoursePurchase, CourseReview


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


class PublicCoursePreviewSerializer(serializers.ModelSerializer):

    class Meta:
        model = Course
        fields = ('id', 'preview_image')
        read_only_fields = fields


class PublicCourseCardSerializer(serializers.ModelSerializer):
    """
    Компактный сериализатор для карточек курсов.
    """

    specialist_name = serializers.CharField(source='specialist.full_name', read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    purchased = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            'id',
            'title',
            'level',
            'specialist_name',
            'price',
            'average_rating',
            'purchased',
            'preview_image',
        )
        read_only_fields = fields

    def get_purchased(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not getattr(user, 'is_authenticated', False):
            return False
        return obj.purchases.filter(user=user).exists()


class CourseReviewSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = CourseReview
        fields = ('id', 'rating', 'comment', 'created_at', 'author_email')
        read_only_fields = ('id', 'created_at', 'author_email')

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Оценка должна быть от 1 до 5.')
        return value


class CoursePurchaseSerializer(serializers.ModelSerializer):
    course_id = serializers.IntegerField(source='course.id', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = CoursePurchase
        fields = ('id', 'course_id', 'course_title', 'created_at')
        read_only_fields = ('id', 'course_id', 'course_title', 'created_at')