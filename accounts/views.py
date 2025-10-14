from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from django.db.models import Q
from .models import CustomUser
from .serializers import (
    UserRegistrationSerializer, 
    LoginSerializer,
    UserProfileSerializer
)
from .services import EmergencyAccessService


class RegisterAPIView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        # Check for existing users
        existing_users = CustomUser.objects.all().filter(
            Q(email=request.data.get('email')) | 
            Q(phone=request.data.get('phone')) |
            Q(username=request.data.get('username'))
        )
        
        if existing_users.exists():
            return Response({
                'error': 'User with this email, phone or username already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'message': 'User registered successfully',
            'user': UserProfileSerializer(user).data,
            # 'tokens': {
            #     'refresh': str(refresh),
            #     'access': str(refresh.access_token),
            # }
        }, status=status.HTTP_201_CREATED)


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Login successful',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RefreshTokenAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            
            return Response({
                'access': str(token.access_token),
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': 'Invalid refresh token'
            }, status=status.HTTP_400_BAD_REQUEST)

class UserProfileAPIView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserListAPIView(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Only allow system admins and hospital admins to view all users
        if self.request.user.role not in ['system_admin', 'hospital_admin']:
            return CustomUser.objects.none()
        return super().get_queryset()


class ActiveUsersCountAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        active_users = CustomUser.objects.all().filter(is_active=True)
        return Response({
            'active_users_count': active_users.count()
        })


class UsersByTypeAPIView(generics.ListAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        role = self.request.query_params.get('type')
        
        if role:
            return CustomUser.objects.all().filter(role=role, is_active=True)
        else:
            return CustomUser.objects.all().filter(is_active=True)