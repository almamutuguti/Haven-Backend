from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta

from accounts.utils import send_otp_email, send_verification_email

from .permissions import (
    IsSystemAdmin, IsHospitalAdmin, IsOrganizationAdmin,
    CanAccessHospitalDashboard, CanAccessOrganizationDashboard
)
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
    PasswordResetRequestSerializer,
    PasswordResetSerializer,
    RequestOTPSerializer,
    UserRegistrationSerializer, 
    LoginSerializer,
    UserProfileSerializer,
    HospitalSerializer,
    OrganizationSerializer,
    VerifyEmailSerializer,
    VerifyOTPSerializer
)


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================

# views.py - Update RegisterAPIView

class RegisterAPIView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        print(f"\n{'='*80}")
        print("REGISTER API CALLED")
        print(f"Request data: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        print(f"User created: {user.email} (ID: {user.id})")
        print(f"Is email verified: {user.is_email_verified}")
        print(f"Email verification token before sending: {user.email_verification_token}")
        
        # CRITICAL: Pass EMAIL to send_verification_email, not user object
        result = send_verification_email(user.email)
        
        # Refresh user to see if token was saved
        user.refresh_from_db()
        print(f"After email sent - Token in DB: '{user.email_verification_token}'")
        print(f"Expected token: '{result.get('token')}'")
        print(f"Tokens match: {user.email_verification_token == result.get('token')}")
        print(f"{'='*80}\n")
        
        return Response({
            'message': 'User registered successfully. Please check your email to verify your account.',
            'user': UserProfileSerializer(user).data,
            'requires_verification': True,
            'debug': {
                'token_saved': user.email_verification_token is not None,
                'token_match': user.email_verification_token == result.get('token')
            }
        }, status=status.HTTP_201_CREATED)
    

# In views.py, update LoginAPIView
class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Check if email is verified
            if not user.is_email_verified:
                return Response({
                    'message': 'Please verify your email first.',
                    'requires_verification': True,
                    'user': UserProfileSerializer(user).data
                }, status=status.HTTP_200_OK)
            
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


# ============================================================================
# USER MANAGEMENT VIEWS (SYSTEM ADMIN ONLY)
# ============================================================================

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


# ============================================================================
# HOSPITAL & ORGANIZATION VIEWS
# ============================================================================

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


# ============================================================================
# SYSTEM ADMIN DASHBOARD VIEWS
# ============================================================================

class SystemAdminOverviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def get(self, request):
        """Get system-wide overview statistics"""
        # User statistics
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()
        users_by_role = CustomUser.objects.values('role').annotate(count=Count('id'))
        
        # Organization statistics
        total_organizations = Organization.objects.count()
        verified_organizations = Organization.objects.filter(is_verified=True).count()
        active_organizations = Organization.objects.filter(is_active=True).count()
        
        # Hospital statistics (if hospitals app is available)
        hospital_stats = {}
        if HAS_HOSPITALS:
            total_hospitals = Hospital.objects.count()
            operational_hospitals = Hospital.objects.filter(is_operational=True).count()
            hospital_stats = {
                'total_hospitals': total_hospitals,
                'operational_hospitals': operational_hospitals
            }
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_users = CustomUser.objects.filter(date_joined__gte=week_ago).count()
        
        return Response({
            'system_overview': {
                'total_users': total_users,
                'active_users': active_users,
                'recent_users': recent_users,
                'users_by_role': list(users_by_role),
                'total_organizations': total_organizations,
                'verified_organizations': verified_organizations,
                'active_organizations': active_organizations,
                **hospital_stats
            }
        })


class SystemAdminUsersAPIView(generics.ListAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def get_queryset(self):
        queryset = CustomUser.objects.all().order_by('-date_joined')
        
        # Filter by role if provided
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
            
        # Filter by active status if provided
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        # Add summary statistics
        total_count = self.get_queryset().count()
        active_count = self.get_queryset().filter(is_active=True).count()
        
        response.data = {
            'summary': {
                'total_users': total_count,
                'active_users': active_count
            },
            'users': response.data
        }
        
        return response


# ============================================================================
# HOSPITAL ADMIN DASHBOARD VIEWS
# ============================================================================

class HospitalAdminOverviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHospitalAdmin]
    
    def get(self, request):
        """Get hospital-specific overview statistics"""
        user = request.user
        
        if not user.hospital:
            return Response({
                'error': 'User is not associated with any hospital'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        hospital = user.hospital
        
        # Staff statistics
        total_staff = CustomUser.objects.filter(
            hospital=hospital, 
            role__in=['hospital_staff', 'hospital_admin']
        ).count()
        
        active_staff = CustomUser.objects.filter(
            hospital=hospital,
            role__in=['hospital_staff', 'hospital_admin'],
            is_active=True
        ).count()
        
        # Associated first aiders (from organizations that work with this hospital)
        associated_first_aiders = CustomUser.objects.filter(
            role='first_aider',
            organization__isnull=False,
            is_active=True
        ).count()
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_staff = CustomUser.objects.filter(
            hospital=hospital,
            date_joined__gte=week_ago
        ).count()
        
        return Response({
            'hospital_overview': {
                'hospital_name': hospital.name,
                'hospital_type': hospital.hospital_type,
                'hospital_level': hospital.level,
                'total_staff': total_staff,
                'active_staff': active_staff,
                'associated_first_aiders': associated_first_aiders,
                'recent_staff_additions': recent_staff,
                'is_operational': hospital.is_operational
            }
        })


class HospitalStaffManagementAPIView(generics.ListAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsHospitalAdmin]
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.hospital:
            return CustomUser.objects.none()
        
        # Return only staff from this hospital
        return CustomUser.objects.filter(
            hospital=user.hospital,
            role__in=['hospital_staff', 'hospital_admin']
        ).order_by('-date_joined')


class HospitalAssociatedFirstAidersAPIView(generics.ListAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsHospitalAdmin]
    
    def get_queryset(self):
        # Return first aiders who might be associated with this hospital
        # This would typically be based on geographical proximity or partnerships
        return CustomUser.objects.filter(
            role='first_aider',
            is_active=True
        ).select_related('organization').order_by('first_name')


# ============================================================================
# ORGANIZATION ADMIN DASHBOARD VIEWS
# ============================================================================

class OrganizationAdminOverviewAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]
    
    def get(self, request):
        """Get organization-specific overview statistics"""
        user = request.user
        
        if not user.organization:
            return Response({
                'error': 'User is not associated with any organization'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        organization = user.organization
        
        # First aider statistics
        total_first_aiders = CustomUser.objects.filter(
            organization=organization, 
            role__in=['first_aider', 'organization_admin']
        ).count()
        
        active_first_aiders = CustomUser.objects.filter(
            organization=organization,
            role__in=['first_aider', 'organization_admin'],
            is_active=True
        ).count()
        
        # Certification statistics (you would need a Certification model for this)
        certified_first_aiders = CustomUser.objects.filter(
            organization=organization,
            role='first_aider',
            is_active=True
        ).count()  # This would be more sophisticated with actual certification data
        
        # Recent activity (last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        recent_first_aiders = CustomUser.objects.filter(
            organization=organization,
            date_joined__gte=week_ago
        ).count()
        
        return Response({
            'organization_overview': {
                'organization_name': organization.name,
                'organization_type': organization.organization_type,
                'total_first_aiders': total_first_aiders,
                'active_first_aiders': active_first_aiders,
                'certified_first_aiders': certified_first_aiders,
                'recent_first_aider_additions': recent_first_aiders,
                'is_verified': organization.is_verified,
                'is_active': organization.is_active
            }
        })


class OrganizationFirstAidersManagementAPIView(generics.ListAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]
    
    def get_queryset(self):
        user = self.request.user
        
        if not user.organization:
            return CustomUser.objects.none()
        
        # Return only first aiders from this organization
        return CustomUser.objects.filter(
            organization=user.organization,
            role__in=['first_aider', 'organization_admin']
        ).order_by('-date_joined')


class OrganizationCertificationsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOrganizationAdmin]
    
    def get(self, request):
        """Get certification data for organization's first aiders"""
        user = request.user
        
        if not user.organization:
            return Response({
                'error': 'User is not associated with any organization'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # This would typically query a Certification model
        # For now, return basic first aider data
        first_aiders = CustomUser.objects.filter(
            organization=user.organization,
            role='first_aider',
            is_active=True
        ).values('id', 'first_name', 'last_name', 'badge_number', 'registration_number')
        
        return Response({
            'first_aiders': list(first_aiders),
            'certification_summary': {
                'total_certified': len(first_aiders),  # Placeholder
                'pending_renewals': 0,  # Placeholder
                'expired_certifications': 0  # Placeholder
            }
        })


# ============================================================================
# DASHBOARD REDIRECTION AND ACCESS CONTROL
# ============================================================================

class DashboardAccessAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Determine which dashboard the user should access based on their role"""
        user = request.user
        
        role_dashboard_map = {
            'system_admin': '/dashboard/admin',
            'hospital_admin': '/dashboard/hospital-admin',
            'organization_admin': '/dashboard/organization-admin',
            'hospital_staff': '/dashboard/hospital-staff',
            'first_aider': '/dashboard/first-aider'
        }
        
        dashboard_path = role_dashboard_map.get(user.role, '/dashboard')
        
        return Response({
            'dashboard_path': dashboard_path,
            'user_role': user.role,
            'user_data': UserProfileSerializer(user).data
        })


class UserRoleCheckAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Check if user has access to specific dashboard"""
        dashboard_type = request.query_params.get('dashboard')
        user = request.user
        
        dashboard_access = {
            'system_admin': user.role == 'system_admin',
            'hospital_admin': user.role in ['hospital_admin', 'hospital_staff'],
            'organization_admin': user.role in ['organization_admin', 'first_aider'],
            'hospital_staff': user.role == 'hospital_staff',
            'first_aider': user.role == 'first_aider'
        }
        
        has_access = dashboard_access.get(dashboard_type, False)
        
        return Response({
            'has_access': has_access,
            'user_role': user.role,
            'requested_dashboard': dashboard_type
        })
    

class VerifyEmailAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Print detailed request information
        print(f"\n{'='*80}")
        print("VERIFY EMAIL API - REQUEST DETAILS")
        print(f"Method: {request.method}")
        print(f"Content-Type: {request.content_type}")
        print(f"Headers: {dict(request.headers)}")
        print(f"Request data (raw): {request.body}")
        print(f"Request data (parsed): {request.data}")
        
        # Get token from request
        token = request.data.get('token')
        print(f"Token from request.data.get('token'): {token}")
        print(f"Token type: {type(token)}")
        print(f"Token length: {len(token) if token else 0}")
        print(f"{'='*80}\n")
        
        # Check if token is None or empty
        if not token:
            print("ERROR: Token is None or empty in request")
            return Response({
                "detail": "Token is required.",
                "received_data": str(request.data)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Trim whitespace just in case
        token = token.strip()
        
        serializer = VerifyEmailSerializer(data={'token': token})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            user.is_email_verified = True
            user.email_verification_token = None
            user.email_verification_sent_at = None
            user.save()
            
            print(f"Email verified successfully for user: {user.email}")
            
            return Response({
                'message': 'Email verified successfully!',
                'user': {
                    'email': user.email,
                    'is_email_verified': user.is_email_verified
                }
            }, status=status.HTTP_200_OK)
        
        print(f"Serializer errors: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ResendVerificationEmailAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'error': 'No account found with this email.'}, status=status.HTTP_404_NOT_FOUND)
        
        if user.is_email_verified:
            return Response({'message': 'Email is already verified.'}, status=status.HTTP_200_OK)
        
        # Pass EMAIL, not user object
        result = send_verification_email(email)
        
        return Response({
            'message': 'Verification email sent successfully.',
            'email': user.email,
            'debug': {
                'token_generated': result.get('token') is not None,
                'user_id': user.id
            }
        }, status=status.HTTP_200_OK)
    
    
class RequestOTPAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Check if email is verified (optional, depending on your requirements)
            require_email_verification = request.data.get('require_email_verification', True)
            
            if require_email_verification and not user.is_email_verified:
                return Response({
                    'error': 'Please verify your email first.',
                    'requires_verification': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
            send_otp_email(user, is_password_reset=False)
            
            return Response({
                'message': 'OTP sent successfully.',
                'email': user.email,
                'otp_expires_in': '10 minutes'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            user.otp_verified = True
            user.otp = None
            user.otp_created_at = None
            user.save()
            
            # Generate JWT tokens for the user
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'OTP verified successfully.',
                'user': {
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'is_email_verified': user.is_email_verified
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            send_otp_email(user, is_password_reset=True)
            
            return Response({
                'message': 'Password reset OTP sent successfully.',
                'email': user.email,
                'otp_expires_in': '10 minutes'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            new_password = serializer.validated_data['new_password']
            
            # Update password
            user.set_password(new_password)
            user.otp = None
            user.otp_created_at = None
            user.otp_verified = False
            user.otp_for_password_reset = False
            user.save()
            
            return Response({
                'message': 'Password reset successful. You can now login with your new password.',
                'email': user.email
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OTPLoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Combined endpoint for OTP-based login
        email = request.data.get('email')
        otp = request.data.get('otp')
        
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # If OTP is provided, verify it
        if otp:
            serializer = VerifyOTPSerializer(data={'email': email, 'otp': otp})
            
            if serializer.is_valid():
                user = serializer.validated_data['user']
                user.otp_verified = True
                user.otp = None
                user.otp_created_at = None
                user.save()
                
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'message': 'Login successful.',
                    'user': {
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'role': user.role,
                        'is_email_verified': user.is_email_verified
                    },
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    }
                }, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # If no OTP provided, send OTP
        serializer = RequestOTPSerializer(data={'email': email})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Check email verification
            if not user.is_email_verified:
                return Response({
                    'error': 'Please verify your email first.',
                    'requires_verification': True
                }, status=status.HTTP_400_BAD_REQUEST)
            
            send_otp_email(user, is_password_reset=False)
            
            return Response({
                'message': 'OTP sent successfully.',
                'email': user.email,
                'otp_expires_in': '10 minutes',
                'next_step': 'verify_otp'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# In your accounts/views.py, add:

class SystemAdminRecentActivityAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def get(self, request):
        """Get recent system activity"""
        from django.db.models import Q
        from datetime import datetime, timedelta
        
        # Get activities from last 24 hours
        day_ago = timezone.now() - timedelta(days=1)
        
        # Recent user registrations
        recent_users = CustomUser.objects.filter(
            date_joined__gte=day_ago
        ).values('id', 'username', 'email', 'role', 'date_joined')
        
        # Recent organization verifications
        recent_org_verifications = Organization.objects.filter(
            updated_at__gte=day_ago,
            is_verified=True
        ).values('id', 'name', 'updated_at')
        
        # Compile activities
        activities = []
        
        for user in recent_users:
            activities.append({
                'type': 'user_registration',
                'title': 'New User Registration',
                'description': f'{user["username"]} joined as {user["role"]}',
                'timestamp': user['date_joined'],
                'user': {
                    'username': user['username'],
                    'role': user['role']
                }
            })
        
        for org in recent_org_verifications:
            activities.append({
                'type': 'organization_verified',
                'title': 'Organization Verified',
                'description': f'{org["name"]} verification completed',
                'timestamp': org['updated_at'],
                'organization': {
                    'name': org['name']
                }
            })
        
        # Sort by timestamp (newest first)
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return Response({
            'recent_activities': activities[:10]  # Limit to 10 most recent
        })

class SystemHealthAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSystemAdmin]
    
    def get(self, request):
        """Get system health metrics"""
        # This would be more sophisticated in production
        # Could connect to monitoring systems
        
        from django.db import connection
        import psutil
        import time
        
        # Measure API response time
        start_time = time.time()
        # Simple database query to measure performance
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            db_performance = "Optimal"
        except Exception:
            db_performance = "Degraded"
        
        api_response_time = round((time.time() - start_time) * 1000, 2)
        
        # Get server metrics (simplified)
        server_load = psutil.cpu_percent(interval=1)
        
        # Get database connection count (PostgreSQL example)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                active_connections = cursor.fetchone()[0]
        except:
            active_connections = "Unknown"
        
        return Response({
            'system_health': {
                'api_response_time': f"{api_response_time}ms",
                'database_performance': db_performance,
                'server_load': f"{server_load}%",
                'active_connections': active_connections,
                'uptime': "99.9%",  # Would get from system monitoring
                'timestamp': timezone.now().isoformat()
            }
        })