from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
from .models import CustomUser
from .serializers import (
    UserRegistrationSerializer, 
    LoginSerializer,
    EmergencyBypassSerializer,
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
            Q(phone_number=request.data.get('phone_number')) |
            Q(username=request.data.get('username'))
        )
        
        if existing_users.exists():
            return Response({
                'error': 'User with this email, phone or username already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'User registered successfully',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
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


class EmergencyBypassAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = EmergencyBypassSerializer(data=request.data)
        
        if serializer.is_valid():
            badge_number = serializer.validated_data['badge_number']
            reason = serializer.validated_data.get('reason', 'Emergency situation')
            ip_address = request.META.get('REMOTE_ADDR')
            
            eligible_users = CustomUser.objects.all().filter(
                badge_number=badge_number,
                user_type__in=['first_aider', 'hospital_admin', 'system_admin'],
                is_active=True
            )
            
            result = EmergencyAccessService.grant_emergency_access(
                badge_number, reason, ip_address, eligible_users
            )
            
            if result:
                user = eligible_users.get(id=result['user'].id)
                refresh = RefreshToken.for_user(user)
                refresh['emergency_access'] = True
                
                return Response({
                    'message': 'Emergency access granted',
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh),
                    'expires_at': result['expires_at'],
                    'user': UserProfileSerializer(user).data,
                    'scope': 'emergency',
                }, status=status.HTTP_200_OK)
            
            return Response({
                'error': 'Emergency access not available'
            }, status=status.HTTP_403_FORBIDDEN)
        
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
        if self.request.user.user_type not in ['system_admin', 'hospital_admin']:
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
        user_type = self.request.query_params.get('type')
        
        if user_type:
            return CustomUser.objects.all().filter(user_type=user_type, is_active=True)
        else:
            return CustomUser.objects.all().filter(is_active=True)