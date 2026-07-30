from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import PasswordResetToken

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'department', 'role', 'password', 'password_confirm',
        ]
        extra_kwargs = {
            # Only admins should be able to hand out elevated roles; enforced
            # again in the view, this is just a sane serializer-level default.
            'role': {'default': User.Role.VIEWER},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        # Self-service signups are never admins, regardless of what was posted.
        validated_data['role'] = User.Role.VIEWER
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone_number', 'department', 'role', 'is_verified', 'created_at',
        ]
        read_only_fields = ['id', 'role', 'is_verified', 'created_at']


class AdminUserSerializer(UserSerializer):
    """Used by admin-only endpoints where role changes are permitted."""
    class Meta(UserSerializer.Meta):
        read_only_fields = ['id', 'created_at']


class FlowAITokenObtainPairSerializer(TokenObtainPairSerializer):
    """Adds user profile fields to the JWT payload and login response."""
    username_field = User.USERNAME_FIELD  # 'email'

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['name'] = user.get_full_name() or user.username
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_token(self, value):
        try:
            reset_token = PasswordResetToken.objects.select_related('user').get(token=value, used=False)
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError('Invalid or already-used reset token.')
        if reset_token.expires_at < timezone.now():
            raise serializers.ValidationError('This reset token has expired.')
        self.context['reset_token'] = reset_token
        return value
