from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .enums import ParentRelationship
from .models import Child, Specialist, SpecialistDescription, UserProfile

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