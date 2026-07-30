from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = 'accounts'

urlpatterns = [
    # --- JSON / JWT API ---
    path('api/register/', views.RegisterAPIView.as_view(), name='api_register'),
    path('api/login/', views.FlowAILoginView.as_view(), name='api_login'),
    path('api/login/refresh/', TokenRefreshView.as_view(), name='api_login_refresh'),
    path('api/logout/', views.LogoutAPIView.as_view(), name='api_logout'),
    path('api/profile/', views.ProfileAPIView.as_view(), name='api_profile'),
    path('api/change-password/', views.ChangePasswordAPIView.as_view(), name='api_change_password'),
    path('api/password-reset/', views.PasswordResetRequestAPIView.as_view(), name='api_password_reset'),
    path('api/password-reset/confirm/', views.PasswordResetConfirmAPIView.as_view(), name='api_password_reset_confirm'),
    path('api/users/', views.AdminUserListView.as_view(), name='api_user_list'),

    # --- Session-based pages (glassmorphism dashboard UI) ---
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
