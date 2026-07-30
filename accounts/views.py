import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model, login as django_login, logout as django_logout
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import redirect, render
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .forms import LoginForm, SignUpForm
from .models import PasswordResetToken
from .permissions import IsAdminRole
from .serializers import (
    AdminUserSerializer,
    ChangePasswordSerializer,
    FlowAITokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()

# ---------------------------------------------------------------------------
# JSON / JWT API (used by the SPA dashboard, mobile clients, external tools)
# ---------------------------------------------------------------------------

class RegisterAPIView(generics.CreateAPIView):
    """POST /api/accounts/register/ — public self-service signup (Viewer role)."""
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class FlowAILoginView(TokenObtainPairView):
    """POST /api/accounts/login/ — returns access + refresh JWT plus user profile."""
    serializer_class = FlowAITokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class LogoutAPIView(APIView):
    """POST /api/accounts/logout/ — blacklists the supplied refresh token."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response({'detail': 'Invalid or already-blacklisted token.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class ProfileAPIView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/accounts/profile/ — the logged-in user's own profile."""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'old_password': 'Incorrect password.'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'detail': 'Password updated successfully.'})


class PasswordResetRequestAPIView(APIView):
    """POST /api/accounts/password-reset/ — issues a short-lived reset token.

    Always returns 200 whether or not the email exists, to avoid leaking
    which addresses are registered.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.filter(email__iexact=email).first()
        if user:
            PasswordResetToken.objects.filter(user=user, used=False).update(used=True)
            reset_token = PasswordResetToken.objects.create(
                id=uuid.uuid4(),
                user=user,
                token=uuid.uuid4().hex,
                expires_at=timezone.now() + timedelta(hours=1),
            )
            # In production this dispatches an email via Celery/SES/etc.
            # Left as a hook — wired up in the notifications module phase.
            print(f'[DEV] Password reset token for {email}: {reset_token.token}')
        return Response({'detail': 'If that email exists, a reset link has been sent.'})


class PasswordResetConfirmAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_token = serializer.context['reset_token']
        reset_token.user.set_password(serializer.validated_data['new_password'])
        reset_token.user.save()
        reset_token.used = True
        reset_token.save(update_fields=['used'])
        return Response({'detail': 'Password has been reset successfully.'})


class AdminUserListView(generics.ListAPIView):
    """GET /api/accounts/users/ — admin-only directory, used by the admin panel."""
    queryset = User.objects.all().order_by('-created_at')
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]


# ---------------------------------------------------------------------------
# Session-based views for the server-rendered dashboard (glassmorphism UI)
# ---------------------------------------------------------------------------

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    form = SignUpForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.role = User.Role.VIEWER
        user.set_password(form.cleaned_data['password'])
        user.save()
        django_login(request, user)
        return redirect('dashboard:home')
    return render(request, 'registration/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    form = LoginForm(request.POST or None)
    error = None
    if request.method == 'POST' and form.is_valid():
        from django.contrib.auth import authenticate
        user = authenticate(
            request,
            username=form.cleaned_data['email'],
            password=form.cleaned_data['password'],
        )
        if user is not None:
            django_login(request, user)
            return redirect('dashboard:home')
        error = 'Invalid email or password.'
    return render(request, 'registration/login.html', {'form': form, 'error': error})


def logout_view(request):
    django_logout(request)
    return redirect('home')
