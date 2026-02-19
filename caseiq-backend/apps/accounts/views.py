from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    ChangePasswordSerializer,
)

User = get_user_model()


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing user profiles.
    Only admins can list all users.
    """
    queryset = User.objects.all().order_by("-created_at")
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Get current user's profile.
        GET /api/users/me/
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=["patch"], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        """
        Update current user's profile.
        PATCH /api/users/update_profile/
        """
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """
        Change password for authenticated user.
        POST /api/users/change_password/
        """
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"detail": "Old password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        
        return Response({"detail": "Password updated successfully."})


class RegisterView(generics.CreateAPIView):
    """
    Register a new user account.
    POST /api/auth/register/
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]