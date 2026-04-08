from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .enums import Language, Method, ParentRelationship, Specialization, SpecialistDevelopmentType, WorkFormat
from .models import Child, ParentAddress, Specialist, SpecialistDescription, UserProfile

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'password_confirm')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Пароли не совпадают.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        email = validated_data['email']
        password = validated_data['password']
        user = User.objects.create_user(username=email, email=email, password=password)
        return user


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = ('id', 'email', 'full_name', 'relationship', 'relationship_other')

    def validate(self, attrs):
        if attrs.get('relationship') == ParentRelationship.OTHER and not attrs.get('relationship_other', '').strip():
            raise serializers.ValidationError({
                'relationship_other': 'Укажите, кем вы приходитесь ребёнку (при выборе «Другое»).',
            })
        return attrs

    def create(self, validated_data):
        return UserProfile.objects.create(user=self.context['request'].user, **validated_data)


class SpecialistSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Specialist
        fields = ('id', 'email', 'full_name', 'approach_description')

    def create(self, validated_data):
        return Specialist.objects.create(user=self.context['request'].user, **validated_data)


class SpecialistDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialistDescription
        fields = (
            'id',
            'specializations',
            'years_experience',
            'methods',
            'age_range',
            'development_types',
            'work_format',
            'languages',
            'time_zone',
            'city',
            'provide_individual_consultations',
            'work_with_child_through_parent',
            'provide_recommendations_and_plans',
            'track_progress_and_analytics',
        )

    def create(self, validated_data):
        specialist = self.context['request'].user.specialist
        return SpecialistDescription.objects.create(specialist=specialist, **validated_data)


class ChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = Child
        fields = (
            'id',
            'name',
            'age',
            'development_type',
            'communication_style',
            'understands_instructions',
            'sensory_sensitivities',
            'motor_difficulties',
            'behavior_notices',
            'motivators',
            'interests',
            'comfortable_duration',
        )

    def create(self, validated_data):
        parent = self.context['request'].user.profile
        return Child.objects.create(parent=parent, **validated_data)


class ParentAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParentAddress
        fields = ('id', 'address')

    def create(self, validated_data):
        profile = self.context['request'].user.profile
        return ParentAddress.objects.create(profile=profile, **validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Старый пароль неверный.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Пароли не совпадают.'})
        return attrs


class SpecialistSettingsSerializer(serializers.Serializer):
    """Объединённый сериализатор: Specialist + SpecialistDescription для настроек."""
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(max_length=255)
    approach_description = serializers.CharField(required=False, allow_blank=True)
    specializations = serializers.JSONField(required=False, default=list)
    years_experience = serializers.IntegerField(required=False, allow_null=True)
    methods = serializers.JSONField(required=False, default=list)
    age_range = serializers.CharField(required=False, allow_blank=True)
    work_format = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    time_zone = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)

    def _validate_codes_list(self, value, enum_cls, field_name):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError(
                {field_name: 'Ожидается массив кодов (например ["speech_therapist", "aba"]).'}
            )
        allowed = {choice.value for choice in enum_cls}
        invalid = [item for item in value if item not in allowed]
        if invalid:
            raise serializers.ValidationError(
                {field_name: f'Недопустимые значения: {invalid}. Используйте value из choices.'}
            )
        return value

    def validate_specializations(self, value):
        return self._validate_codes_list(value, Specialization, 'specializations')

    def validate_methods(self, value):
        return self._validate_codes_list(value, Method, 'methods')

    def validate_work_format(self, value):
        if value in (None, ''):
            return value
        allowed = {choice.value for choice in WorkFormat}
        if value not in allowed:
            raise serializers.ValidationError(
                f'Недопустимый work_format: "{value}". Допустимо: {sorted(allowed)}.'
            )
        return value

    def to_representation(self, specialist):
        desc = getattr(specialist, 'description', None)
        return {
            'email': specialist.user.email,
            'full_name': specialist.full_name,
            'approach_description': specialist.approach_description,
            'specializations': desc.specializations if desc else [],
            'years_experience': desc.years_experience if desc else None,
            'methods': desc.methods if desc else [],
            'age_range': desc.age_range if desc else '',
            'work_format': desc.work_format if desc else None,
            'time_zone': desc.time_zone if desc else '',
            'city': desc.city if desc else '',
        }

    def update(self, specialist, validated_data):
        specialist_fields = {'full_name', 'approach_description'}
        desc_fields = {
            'specializations', 'years_experience', 'methods',
            'age_range', 'work_format', 'time_zone', 'city',
        }

        for field in specialist_fields:
            if field in validated_data:
                setattr(specialist, field, validated_data[field])
        specialist.save()

        desc_data = {k: v for k, v in validated_data.items() if k in desc_fields}
        if desc_data:
            desc, _ = SpecialistDescription.objects.get_or_create(specialist=specialist)
            for field, value in desc_data.items():
                setattr(desc, field, value)
            desc.save()

        return specialist


class PublicSpecialistSerializer(serializers.ModelSerializer):
    average_rating = serializers.FloatField(read_only=True)
    total_courses = serializers.IntegerField(read_only=True)
    city = serializers.CharField(source='description.city', read_only=True)
    specializations = serializers.JSONField(source='description.specializations', read_only=True)
    work_format = serializers.CharField(source='description.work_format', read_only=True)
    avatar = serializers.ImageField(read_only=True)

    class Meta:
        model = Specialist
        fields = (
            'id',
            'full_name',
            'approach_description',
            'average_rating',
            'total_courses',
            'city',
            'specializations',
            'work_format',
            'avatar',
        )
        read_only_fields = fields


class PublicSpecialistAvatarSerializer(serializers.ModelSerializer):

    class Meta:
        model = Specialist
        fields = ('id', 'avatar')
        read_only_fields = fields


class PublicSpecialistCardSerializer(serializers.ModelSerializer):
    """
    Поля карточки специалиста для списков (как компактные карточки курсов).
    """

    specialization = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    reviews_count = serializers.IntegerField(read_only=True)
    price_from = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    years_experience = serializers.SerializerMethodField()
    currency = serializers.SerializerMethodField()
    short_description = serializers.CharField(source='approach_description', read_only=True)

    class Meta:
        model = Specialist
        fields = (
            'id',
            'full_name',
            'specialization',
            'avatar',
            'average_rating',
            'reviews_count',
            'years_experience',
            'price_from',
            'currency',
            'short_description',
        )
        read_only_fields = fields

    def get_currency(self, obj):
        return 'KZT'

    def get_specialization(self, obj):
        try:
            codes = obj.description.specializations
        except SpecialistDescription.DoesNotExist:
            return None
        if not codes or not isinstance(codes, list):
            return None
        code = codes[0]
        try:
            return Specialization(code).label
        except ValueError:
            return str(code)

    def get_years_experience(self, obj):
        try:
            return obj.description.years_experience
        except SpecialistDescription.DoesNotExist:
            return None

    def get_avatar(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get('request')
        url = obj.avatar.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def to_representation(self, instance):
        data = super().to_representation(instance)
        ar = data.get('average_rating')
        if ar is not None:
            data['average_rating'] = round(float(ar), 1)
        return data


class PublicSpecialistDetailSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    average_rating = serializers.FloatField(read_only=True, allow_null=True)
    reviews_count = serializers.IntegerField(read_only=True)
    price_from = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    currency = serializers.SerializerMethodField()
    specializations = serializers.SerializerMethodField()
    methods = serializers.SerializerMethodField()
    languages = serializers.SerializerMethodField()
    development_types = serializers.SerializerMethodField()
    work_format = serializers.SerializerMethodField()
    years_experience = serializers.IntegerField(source='description.years_experience', read_only=True, allow_null=True)
    age_range = serializers.CharField(source='description.age_range', read_only=True)
    city = serializers.CharField(source='description.city', read_only=True)
    time_zone = serializers.CharField(source='description.time_zone', read_only=True)
    provide_individual_consultations = serializers.BooleanField(
        source='description.provide_individual_consultations', read_only=True
    )
    work_with_child_through_parent = serializers.BooleanField(
        source='description.work_with_child_through_parent', read_only=True
    )
    provide_recommendations_and_plans = serializers.BooleanField(
        source='description.provide_recommendations_and_plans', read_only=True
    )
    track_progress_and_analytics = serializers.BooleanField(
        source='description.track_progress_and_analytics', read_only=True
    )

    class Meta:
        model = Specialist
        fields = (
            'id',
            'full_name',
            'avatar',
            'average_rating',
            'reviews_count',
            'price_from',
            'currency',
            'approach_description',
            'specializations',
            'methods',
            'languages',
            'development_types',
            'work_format',
            'years_experience',
            'age_range',
            'city',
            'time_zone',
            'provide_individual_consultations',
            'work_with_child_through_parent',
            'provide_recommendations_and_plans',
            'track_progress_and_analytics',
        )
        read_only_fields = fields

    def _enum_list(self, enum_cls, values):
        if not values or not isinstance(values, list):
            return []
        labels = {choice.value: choice.label for choice in enum_cls}
        return [{'value': v, 'label': labels.get(v, str(v))} for v in values if isinstance(v, str) and v in labels]

    def get_currency(self, obj):
        return 'KZT'

    def get_avatar(self, obj):
        if not obj.avatar:
            return None
        request = self.context.get('request')
        url = obj.avatar.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_specializations(self, obj):
        values = getattr(getattr(obj, 'description', None), 'specializations', [])
        return self._enum_list(Specialization, values)

    def get_methods(self, obj):
        values = getattr(getattr(obj, 'description', None), 'methods', [])
        return self._enum_list(Method, values)

    def get_languages(self, obj):
        values = getattr(getattr(obj, 'description', None), 'languages', [])
        return self._enum_list(Language, values)

    def get_development_types(self, obj):
        values = getattr(getattr(obj, 'description', None), 'development_types', [])
        return self._enum_list(SpecialistDevelopmentType, values)

    def get_work_format(self, obj):
        value = getattr(getattr(obj, 'description', None), 'work_format', None)
        if not value:
            return None
        try:
            label = WorkFormat(value).label
        except ValueError:
            label = str(value)
        return {'value': value, 'label': label}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        ar = data.get('average_rating')
        if ar is not None:
            data['average_rating'] = round(float(ar), 1)
        return data