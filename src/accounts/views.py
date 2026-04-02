from django.contrib.auth import get_user_model, authenticate
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers import (
    UserSerializer,
    LoginResponseSerializer,
    LoginRequestSerializer,
    LogoutRequestSerializer,
    LogoutResponseSerializer,
    ChangeEmailRequestSerializer,
    ChangeEmailResponseSerializer,
    ChangePasswordRequestSerializer,
    ChangePasswordResponseSerializer,
)

UserModel = get_user_model()


class RegisterView(CreateAPIView):
    queryset = UserModel.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]


@extend_schema(
    tags=['auth'],
    summary='Login endpoint',
    description='Authenticate user and get access and refresh tokens.',
    request=LoginRequestSerializer,
    responses={
        200: LoginResponseSerializer,
        401: 'Invalid email or password',
    }
)
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(email=email, password=password)

        if user is None:
            return Response(
                {
                    'error': 'Invalid message or password',
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'message': 'Login successful'
            },
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=['auth'],
    summary='Logout endpoint',
    description='Blacklist the refresh token',
    request=LogoutRequestSerializer,
    responses={
        200: LogoutResponseSerializer,
        400: 'Invalid or expired token',
    }
)
class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {
                    'message': 'Logout successful',
                },
                status=status.HTTP_200_OK
            )
        except TokenError:
            return Response(
                {
                    'message': 'Invalid or expired token'
                },
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(
    tags=['auth'],
    summary='Change email',
    description='Authenticated user changes their email by confirming their current password.',
    request=ChangeEmailRequestSerializer,
    responses={
        200: ChangeEmailResponseSerializer,
        400: 'Validation error',
        401: 'Unauthorized',
    }
)
class ChangeEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        serializer = ChangeEmailRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                'message': 'Email changed successfully.',
                'email': user.email,
            },
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=['auth'],
    summary='Change password',
    description='Authenticated user changes their password by confirming their current password.',
    request=ChangePasswordRequestSerializer,
    responses={
        200: ChangePasswordResponseSerializer,
        400: 'Validation error',
        401: 'Unauthorized',
    }
)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordRequestSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                'message': 'Password changed successfully.'
            },
            status=status.HTTP_200_OK
        )
