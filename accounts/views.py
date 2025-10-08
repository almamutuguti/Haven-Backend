from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser
from .serializers import (
    UserRegistrationSerializer, 
    LoginSerializer,
    EmergencyBypassSerializer,
    UserProfileSerializer
)
from .services import EmergencyAccessService

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_user(request):
    """User registration endpoint"""
    serializer = UserRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
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
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_user(request):
    """Unified login endpoint - accepts badge_number, email, phone, or username"""
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

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def emergency_bypass(request):
    """Emergency access bypass for critical situations"""
    serializer = EmergencyBypassSerializer(data=request.data)
    
    if serializer.is_valid():
        badge_number = serializer.validated_data['badge_number']
        reason = serializer.validated_data.get('reason', 'Emergency situation')
        ip_address = request.META.get('REMOTE_ADDR')
        
        result = EmergencyAccessService.grant_emergency_access(
            badge_number, reason, ip_address
        )
        
        if result:
            refresh = RefreshToken.for_user(result['user'])
            refresh['emergency_access'] = True
            
            return Response({
                'message': 'Emergency access granted',
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'expires_at': result['expires_at'],
                'user': UserProfileSerializer(result['user']).data,
                'scope': 'emergency',
            }, status=status.HTTP_200_OK)
        
        return Response({
            'error': 'Emergency access not available'
        }, status=status.HTTP_403_FORBIDDEN)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def refresh_token(request):
    """Refresh JWT token"""
    from rest_framework_simplejwt.tokens import RefreshToken
    
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

@api_view(['GET', 'PUT'])
@permission_classes([permissions.IsAuthenticated])
def user_profile(request):
    """Get or update user profile"""
    if request.method == 'GET':
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout(request):
    """Logout user by blacklisting token"""
    try:
        refresh_token = request.data.get("refresh")
        if refresh_token:
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)