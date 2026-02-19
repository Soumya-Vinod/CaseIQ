from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)

from apps.accounts.views import UserViewSet, RegisterView
from apps.laws.views import ActViewSet, LawSectionViewSet, LawPDFViewSet
from apps.queries.views import QueryViewSet
from apps.complaints.views import ComplaintViewSet
from apps.ai_engine.views import AnalyzeScenarioView

# Router for ViewSets
router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")
router.register(r"acts", ActViewSet, basename="acts")
router.register(r"laws", LawSectionViewSet, basename="laws")
router.register(r"law-pdfs", LawPDFViewSet, basename="law-pdfs")
router.register(r"queries", QueryViewSet, basename="queries")
router.register(r"complaints", ComplaintViewSet, basename="complaints")

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    
    # Authentication
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/logout/", TokenBlacklistView.as_view(), name="token_blacklist"),
    
    # AI Analysis
    path("api/analyze/", AnalyzeScenarioView.as_view(), name="analyze"),
    
    # All other endpoints via router
    path("api/", include(router.urls)),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Debug toolbar
    try:
        import debug_toolbar
        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass