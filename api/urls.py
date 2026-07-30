from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (UserViewSet, IntersectionViewSet, CameraViewSet, 
                    VehicleViewSet, SignalViewSet, EmissionViewSet)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'intersections', IntersectionViewSet)
router.register(r'cameras', CameraViewSet)
router.register(r'vehicles', VehicleViewSet)
router.register(r'signals', SignalViewSet)
router.register(r'emissions', EmissionViewSet)

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('', include(router.urls)),
]
