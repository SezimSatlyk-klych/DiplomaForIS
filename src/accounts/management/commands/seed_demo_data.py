import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from PIL import Image

from accounts.enums import (
    ComfortableDuration,
    CommunicationStyle,
    DevelopmentType,
    Language,
    Method,
    ParentRelationship,
    Specialization,
    UnderstandsInstructions,
    WorkFormat,
)
from accounts.models import Child, Specialist, SpecialistDescription, UserProfile
from courses.enums import Category, CourseTag, Level, MaterialType
from courses.models import Course, CourseModule, CoursePurchase, CourseReview


class Command(BaseCommand):
    help = 'Создаёт демо-данные для разработки (пользователи, специалисты, дети, курсы и т.д.).'

    def handle(self, *args, **options):
        User = get_user_model()

        def ensure_sample_png(relative_path: str) -> None:
            """
            Создаёт маленькую PNG-заглушку в MEDIA_ROOT, чтобы ImageField мог отдать URL.
            """
            target_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            if os.path.exists(target_path):
                return
            img = Image.new('RGB', (64, 64), color=(140, 180, 240))
            img.save(target_path, format='PNG')

        course_preview_path = 'courses/previews/sample.png'
        specialist_avatar_path = 'specialists/avatars/sample.png'

        ensure_sample_png(course_preview_path)
        ensure_sample_png(specialist_avatar_path)

        # Родители
        parents = []
        for i in range(1, 6):
            email = f'parent{i}@example.com'
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'is_active': True,
                },
            )
            if not user.password:
                user.set_password('password123')
                user.save(update_fields=['password'])

            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': f'Родитель {i}',
                    'relationship': ParentRelationship.MOM,
                },
            )

            Child.objects.get_or_create(
                parent=profile,
                name=f'Ребёнок {i}',
                defaults={
                    'age': 5 + i,
                    'development_type': DevelopmentType.AUTISM,
                    'communication_style': CommunicationStyle.SINGLE_WORDS,
                    'understands_instructions': UnderstandsInstructions.SHORT_INSTRUCTIONS,
                    'sensory_sensitivities': [],
                    'motor_difficulties': [],
                    'behavior_notices': [],
                    'motivators': [],
                    'interests': [],
                    'comfortable_duration': ComfortableDuration.MIN_10,
                },
            )

            parents.append(user)

        # Специалисты
        specialists = []
        for i in range(1, 6):
            email = f'specialist{i}@example.com'
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'is_active': True,
                },
            )
            if not user.password:
                user.set_password('password123')
                user.save(update_fields=['password'])

            specialist, _ = Specialist.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': f'Специалист {i}',
                    'approach_description': 'Работаю с детьми с РАС, использую разные методики.',
                },
            )

            # Аватар необязательный, но для демонстрации лучше заполнить.
            if not specialist.avatar:
                specialist.avatar = specialist_avatar_path
                specialist.save(update_fields=['avatar'])

            SpecialistDescription.objects.get_or_create(
                specialist=specialist,
                defaults={
                    'specializations': [Specialization.ABA, Specialization.SPEECH_THERAPIST],
                    'years_experience': 3 + i,
                    'methods': [Method.ABA, Method.DIR_FLOORTIME],
                    'age_range': '3-10',
                    'development_types': [DevelopmentType.AUTISM, DevelopmentType.ZPR],
                    'work_format': WorkFormat.ONLINE,
                    'languages': [Language.RU, Language.KZ],
                    'time_zone': 'Asia/Almaty',
                    'city': 'Алматы',
                    'provide_individual_consultations': True,
                    'work_with_child_through_parent': True,
                    'provide_recommendations_and_plans': True,
                    'track_progress_and_analytics': True,
                },
            )

            specialists.append(specialist)

        # Курсы
        courses = []
        for i, specialist in enumerate(specialists, start=1):
            course, _ = Course.objects.get_or_create(
                specialist=specialist,
                title=f'Полный курс моторики {i}',
                defaults={
                    'description': 'Базовый курс для развития моторики у детей с РАС.',
                    'learning_outcomes': 'Базовые навыки координации и простые упражнения для дома.',
                    'tags': [CourseTag.FOR_CHILDREN.value, CourseTag.EASY_START.value],
                    'category': Category.AUTISM,
                    'level': Level.BEGINNER,
                    'price': 12000,
                    'duration': 10 + i,
                    'preview_image': course_preview_path,
                },
            )

            if not course.preview_image:
                course.preview_image = course_preview_path
                course.save(update_fields=['preview_image'])

            # Модули курса
            for m in range(1, 4):
                CourseModule.objects.get_or_create(
                    course=course,
                    title=f'Модуль {m}',
                    defaults={
                        'description': f'Описание модуля {m}',
                        'material_type': MaterialType.ARTICLE,
                        'file': 'courses/materials/sample.pdf',
                    },
                )

            courses.append(course)

        # Если в базе уже есть "битые" имена файлов (например, '.png'),
        # создаём заглушки под каждое существующее `preview_image.name`,
        # чтобы фронт всегда мог отрисовать картинку по URL.
        for course in Course.objects.all():
            if course.preview_image:
                ensure_sample_png(course.preview_image.name)

        # Отзывы и покупки от первых трёх родителей
        for parent in parents[:3]:
            for course in courses[:3]:
                purchase, _ = CoursePurchase.objects.get_or_create(user=parent, course=course)
                CourseReview.objects.get_or_create(
                    user=parent,
                    course=course,
                    defaults={
                        'rating': 4,
                        'comment': 'Полезный курс, понятные материалы.',
                    },
                )

        # То же самое для аватаров специалистов.
        for specialist in Specialist.objects.all():
            if specialist.avatar:
                ensure_sample_png(specialist.avatar.name)

        self.stdout.write(self.style.SUCCESS('Демо-данные успешно созданы.'))

