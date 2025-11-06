from rest_framework import serializers
from .models import CustomUser, Organization

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
    hospital_id = serializers.UUIDField(required=False, allow_null=True)
    organization_id = serializers.UUIDField(required=False, allow_null=True)
    
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
    hospital_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    organization_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
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
    hospital_id = serializers.UUIDField(required=False, allow_null=True)
    organization_id = serializers.UUIDField(required=False, allow_null=True)
    
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