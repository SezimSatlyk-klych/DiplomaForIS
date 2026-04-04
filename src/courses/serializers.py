from rest_framework import serializers

from .enums import CourseTag
from .models import Course, CourseModule, CoursePurchase, CourseReview


class CourseModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseModule
        fields = ('id', 'title', 'description', 'material_type', 'file', 'created_at')
        read_only_fields = ('id', 'created_at')
        extra_kwargs = {
            'title': {'help_text': 'Название модуля.'},
            'description': {'help_text': 'Описание модуля. Можно пустым.', 'required': False, 'allow_blank': True},
            'material_type': {
                'help_text': 'Тип материала: article, pdf или video (см. GET /api/courses/choices/ → material_type).',
            },
            'file': {'help_text': 'Файл модуля; при вложении в курс удобно отправлять тем же multipart, что и курс.'},
        }


class CourseSerializer(serializers.ModelSerializer):
    modules = CourseModuleSerializer(
        many=True,
        required=False,
        help_text=(
            'Опционально: модули курса при создании/обновлении. '
            'При PUT/PATCH, если передать `modules`, старые модули удаляются и создаются заново из массива.'
        ),
    )
    tags = serializers.ListField(
        child=serializers.ChoiceField(choices=CourseTag.choices),
        required=False,
        allow_empty=True,
        help_text=(
            'Список кодов тэгов (`value` из ответа GET /api/courses/choices/ → `course_tag`). '
            'Дубликаты в массиве лучше не передавать.'
        ),
    )

    class Meta:
        model = Course
        fields = (
            'id',
            'title',
            'description',
            'learning_outcomes',
            'tags',
            'category',
            'level',
            'price',
            'duration',
            'preview_image',
            'modules',
        )
        read_only_fields = ('id',)
        extra_kwargs = {
            'title': {'help_text': 'Название курса.'},
            'description': {'help_text': 'Описание курса.'},
            'learning_outcomes': {
                'help_text': 'Чему научатся пользователи (многострочный текст). Необязательно.',
                'required': False,
                'allow_blank': True,
            },
            'category': {
                'help_text': (
                    'Категория курса, **обязательное поле**. Код из GET /api/courses/choices/ → `category` '
                    '(поле `value`): autism, speech_therapy, adhd, sensory_processing, social_development, '
                    'physical_therapy, behavioral_support, learning_disabilities.'
                ),
            },
            'level': {
                'help_text': (
                    'Уровень сложности. Код из GET /api/courses/choices/ → `level`: beginner, intermediate, advanced.'
                ),
            },
            'price': {'help_text': 'Цена курса (число, до двух знаков после запятой).'},
            'duration': {'help_text': 'Продолжительность курса в часах (целое число).'},
            'preview_image': {
                'help_text': (
                    'Превью-картинка курса. При отправке с файлом используйте **multipart/form-data** '
                    '(то же имя полей, что в JSON + файл в `preview_image`).'
                ),
            },
        }

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