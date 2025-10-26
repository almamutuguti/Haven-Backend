from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = (
            'badge_number', 'username', 'email', 'phone', 'password', 'password_confirm',
            'role', 'first_name', 'last_name', 'registration_number', 
            'emergency_contact_name', 'emergency_contact_phone'
        )
        extra_kwargs = {
            'badge_number': {'required': True},
            'username': {'required': True}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords don't match."})
        
        # Validate at least one contact method exists
        if not attrs.get('email') and not attrs.get('phone'):
            raise serializers.ValidationError(
                "Either email or phone number must be provided."
            )
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        badge_number = validated_data.pop('badge_number')
        
        user = CustomUser.objects.create_user(
            badge_number=badge_number,
            password=password,
            **validated_data
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            # Multi-field authentication
            if '@' in email:
                try:
                    user = CustomUser.objects.get(email=email)
                except CustomUser.DoesNotExist:
                    raise serializers.ValidationError("Invalid credentials.")
            else:
                # Handle other login methods if needed
                raise serializers.ValidationError("Please use email to login.")
            
            # Check if user is active
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            
            # Verify password
            if not user.check_password(password):
                raise serializers.ValidationError("Invalid credentials.")
            
            # Add user to validated data
            data['user'] = user
            return data
            
        raise serializers.ValidationError("Must include 'email' and 'password'.")



class UserProfileSerializer(serializers.ModelSerializer):

    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    phone = serializers.CharField(read_only=True)
    role = serializers.CharField(read_only=True)
    badge_number = serializers.CharField(read_only=True)
    registration_number = serializers.CharField(read_only=True)
    class Meta:
        model = CustomUser
        fields = (
            'id', 'username', 'email', 'phone', 'role', 'first_name', 
            'last_name', 'badge_number', 'registration_number',
            'emergency_contact_name', 'emergency_contact_phone',
            'date_joined', 'is_active', 'is_staff'
        )


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            'first_name', 'last_name', 'email', 'phone',
            'emergency_contact_name', 'emergency_contact_phone'
        )

class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            'first_name', 'last_name', 'email', 'phone', 'role',
            'emergency_contact_name', 'emergency_contact_phone',
            'is_active', 'badge_number', 'registration_number'
        )
    
    def validate_role(self, value):
        # Ensure the role is valid
        valid_roles = ['system_admin', 'hospital_staff', 'first_aider', 'superuser']
        if value not in valid_roles:
            raise serializers.ValidationError(f"Invalid role: {value}. Must be one of {valid_roles}.")
        return value