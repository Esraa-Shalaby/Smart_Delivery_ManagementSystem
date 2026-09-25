"""
API views for the accounts app.

Views stay thin: validation happens in serializers, business logic
happens in services.py.
"""

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.serializers import UserRegistrationSerializer, UserSerializer
from apps.accounts.services import register_user, update_user


class UserRegistrationView(APIView):
    """
    Registers a new user.

    A MANAGER account can only be created by an already-authenticated
    MANAGER; anyone else requesting the MANAGER role is rejected.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        requested_role = serializer.validated_data.get("role")

        if requested_role == User.Role.MANAGER:
            requester = request.user
            if not (requester.is_authenticated and requester.role == User.Role.MANAGER):
                return Response(
                    {"detail": "Only an existing manager can create a manager account."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        user = register_user(**serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class UserProfileView(APIView):
    """
    Retrieves the authenticated user's profile.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)


class UserProfileUpdateView(APIView):
    """
    Updates the authenticated user's profile information.
    Password and role cannot be changed through this endpoint.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = update_user(user=request.user, data=request.data)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
