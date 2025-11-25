from rest_framework import serializers
from .models import CustomUser, Organization
from django.contrib.auth.password_validation import validate_password

# Import Hospital model with error handling
try:
    from hospitals.models import Hospital
    HAS_HOSPITALS = True
except ImportError:
    HAS_HOSPITALS = False
    Hospital = None


class HospitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hospital
        fields = ['id', 'name', 'hospital_type', 'level', 'phone', 'email', 'is_operational'] if HAS_HOSPITALS else []


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'organization_type', 'description', 'phone', 'email']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True)
    hospital_id = serializers.IntegerField(required=False, allow_null=True)
    organization_id = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'password', 'password_confirm', 
            'first_name', 'last_name', 'phone', 'role', 
            'hospital_id', 'organization_id'
        ]
    
    def validate(self, attrs):
        # Check if passwords match
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        # Validate role-specific fields
        role = attrs.get('role')
        hospital_id = attrs.get('hospital_id')
        organization_id = attrs.get('organization_id')
        
        if role == 'hospital_staff' and not hospital_id:
            raise serializers.ValidationError({"hospital_id": "Hospital is required for hospital staff."})
        
        if role == 'first_aider' and not organization_id:
            raise serializers.ValidationError({"organization_id": "Organization is required for first aiders."})
        
        return attrs
    
    def create(self, validated_data):
        # Extract the foreign key IDs and remove from validated_data
        password_confirm = validated_data.pop('password_confirm', None)
        hospital_id = validated_data.pop('hospital_id', None)
        organization_id = validated_data.pop('organization_id', None)
        password = validated_data.pop('password')
        
        # Create the user
        user = CustomUser.objects.create_user(
            **validated_data,
            password=password
        )
        
        # Set the foreign key relationships if provided
        if hospital_id and user.role == 'hospital_staff' and HAS_HOSPITALS:
            try:
                hospital = Hospital.objects.get(id=hospital_id)
                user.hospital = hospital
            except Hospital.DoesNotExist:
                raise serializers.ValidationError({"hospital_id": "Hospital not found."})
        
        if organization_id and user.role == 'first_aider':
            try:
                organization = Organization.objects.get(id=organization_id)
                user.organization = organization
            except Organization.DoesNotExist:
                raise serializers.ValidationError({"organization_id": "Organization not found."})
        
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password.")
        
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")
        
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled.")
        
        attrs['user'] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    hospital = HospitalSerializer(read_only=True)
    organization = OrganizationSerializer(read_only=True)
    hospital_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    organization_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'phone', 'role', 'hospital', 'hospital_id', 
            'organization', 'organization_id', 'date_joined',
            'badge_number', 'registration_number', 'is_active'
        ]
        read_only_fields = ['id', 'date_joined', 'badge_number']


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    hospital_id = serializers.IntegerField(required=False, allow_null=True)
    organization_id = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'phone', 'role', 'hospital_id', 'organization_id',
            'is_active', 'badge_number', 'registration_number'
        ]
    
    def update(self, instance, validated_data):
        hospital_id = validated_data.pop('hospital_id', None)
        organization_id = validated_data.pop('organization_id', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update hospital if provided
        if hospital_id is not None and HAS_HOSPITALS:
            if hospital_id:
                try:
                    hospital = Hospital.objects.get(id=hospital_id)
                    instance.hospital = hospital
                except Hospital.DoesNotExist:
                    raise serializers.ValidationError({"hospital_id": "Hospital not found."})
            else:
                instance.hospital = None
        
        # Update organization if provided
        if organization_id is not None:
            if organization_id:
                try:
                    organization = Organization.objects.get(id=organization_id)
                    instance.organization = organization
                except Organization.DoesNotExist:
                    raise serializers.ValidationError({"organization_id": "Organization not found."})
            else:
                instance.organization = None
        
        instance.save()
        return instance
    

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=6)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        # Check if new passwords match
        if attrs.get('new_password') != attrs.get('confirm_password'):
            raise serializers.ValidationError({"new_password": "New passwords do not match."})
        
        # Validate password strength
        try:
            validate_password(attrs.get('new_password'))
        except Exception as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


# ============================================================================
# DASHBOARD SERIALIZERS
# ============================================================================

class DashboardUserSerializer(serializers.ModelSerializer):
    """Simplified user serializer for dashboard listings"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'role', 'is_active', 'date_joined', 'badge_number'
        ]
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class OrganizationDashboardSerializer(serializers.ModelSerializer):
    """Organization serializer with additional dashboard statistics"""
    first_aider_count = serializers.SerializerMethodField()
    active_first_aider_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'organization_type', 'description',
            'contact_person', 'phone', 'email', 'website', 'address',
            'is_active', 'is_verified', 'created_at', 'updated_at',
            'first_aider_count', 'active_first_aider_count'
        ]
    
    def get_first_aider_count(self, obj):
        return obj.first_aiders.count()
    
    def get_active_first_aider_count(self, obj):
        return obj.first_aiders.filter(is_active=True).count()


class HospitalDashboardSerializer(serializers.ModelSerializer):
    """Hospital serializer with additional dashboard statistics"""
    staff_count = serializers.SerializerMethodField()
    active_staff_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Hospital
        fields = [
            'id', 'name', 'hospital_type', 'level', 'phone', 'email',
            'address', 'is_operational', 'staff_count', 'active_staff_count'
        ]
    
    def get_staff_count(self, obj):
        return obj.staff.count()
    
    def get_active_staff_count(self, obj):
        return obj.staff.filter(is_active=True).count()


class SystemOverviewSerializer(serializers.Serializer):
    """Serializer for system admin overview data"""
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    recent_users = serializers.IntegerField()
    users_by_role = serializers.ListField()
    total_organizations = serializers.IntegerField()
    verified_organizations = serializers.IntegerField()
    active_organizations = serializers.IntegerField()
    total_hospitals = serializers.IntegerField(required=False, allow_null=True)
    operational_hospitals = serializers.IntegerField(required=False, allow_null=True)


class HospitalOverviewSerializer(serializers.Serializer):
    """Serializer for hospital admin overview data"""
    hospital_name = serializers.CharField()
    hospital_type = serializers.CharField()
    hospital_level = serializers.CharField()
    total_staff = serializers.IntegerField()
    active_staff = serializers.IntegerField()
    associated_first_aiders = serializers.IntegerField()
    recent_staff_additions = serializers.IntegerField()
    is_operational = serializers.BooleanField()


class OrganizationOverviewSerializer(serializers.Serializer):
    """Serializer for organization admin overview data"""
    organization_name = serializers.CharField()
    organization_type = serializers.CharField()
    total_first_aiders = serializers.IntegerField()
    active_first_aiders = serializers.IntegerField()
    certified_first_aiders = serializers.IntegerField()
    recent_first_aider_additions = serializers.IntegerField()
    is_verified = serializers.BooleanField()
    is_active = serializers.BooleanField()


class CertificationSummarySerializer(serializers.Serializer):
    """Serializer for certification summary data"""
    total_certified = serializers.IntegerField()
    pending_renewals = serializers.IntegerField()
    expired_certifications = serializers.IntegerField()