from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q

from .permissions import IsSystemAdmin
from .models import CustomUser, Organization

# Import Hospital model with error handling
try:
    from hospitals.models import Hospital
    HAS_HOSPITALS = True
except ImportError:
    HAS_HOSPITALS = False
    Hospital = None

from .serializers import (
    AdminUserUpdateSerializer,
    ChangePasswordSerializer,
    UserRegistrationSerializer, 
    LoginSerializer,
    UserProfileSerializer,
    HospitalSerializer,
    OrganizationSerializer
)


class RegisterAPIView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        # Check for existing users
        existing_users = CustomUser.objects.filter(
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
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        serializer = UserProfileSerializer(
            request.user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
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
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def get_queryset(self):
        return CustomUser.objects.all().order_by('-date_joined')


class ActiveUsersCountAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def get(self, request):
        active_users = CustomUser.objects.filter(is_active=True)
        return Response({
            'active_users_count': active_users.count()
        })


class UsersByTypeAPIView(generics.ListAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        role = self.request.query_params.get('role')
        queryset = self.get_queryset()
        
        # Add message to response data if no users found for specific role
        if role and len(response.data) == 0:
            response.data = {
                "message": f"No active users found with role '{role}'",
                "role": role,
                "users": []
            }
        
        return response
    
    def get_queryset(self):
        role = self.request.query_params.get('role')
        
        queryset = CustomUser.objects.filter(is_active=True)
        
        if role:
            queryset = queryset.filter(role=role)
            
        return queryset


class UserUpdateAPIView(generics.UpdateAPIView):
    serializer_class = AdminUserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    queryset = CustomUser.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'user_id'
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'message': 'User updated successfully',
            'user': UserProfileSerializer(instance).data
        })


class AdminUserDeleteAPIView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    queryset = CustomUser.objects.all()
    lookup_field = 'id'
    lookup_url_kwarg = 'user_id'
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Prevent admin from deleting themselves
        if instance == request.user:
            return Response({
                'error': 'You cannot delete your own account'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_destroy(instance)
        return Response({
            'message': 'User deleted successfully'
        }, status=status.HTTP_200_OK)


class HospitalListAPIView(generics.ListAPIView):
    serializer_class = HospitalSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        if HAS_HOSPITALS:
            return Hospital.objects.all().order_by('name')
        return Hospital.objects.none()


class OrganizationListAPIView(generics.ListAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return Organization.objects.all().order_by('name')
    

class ChangePasswordAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Create new tokens since password changed
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Password changed successfully',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)