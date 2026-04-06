from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .enums import ParentRelationship, Specialization
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
        if not codes:
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