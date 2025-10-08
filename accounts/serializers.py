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
            'badge_number', 'username', 'email', 'phone_number', 'password', 'password_confirm',
            'user_type', 'first_name', 'last_name', 'certification_level', 
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
        if not attrs.get('email') and not attrs.get('phone_number'):
            raise serializers.ValidationError(
                "Either email or phone number must be provided."
            )
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = CustomUser.objects.create_user(
            badge_number=validated_data['badge_number'],
            password=password,
            **validated_data
        )
        return user

class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()  # badge_number, email, phone, or username
    password = serializers.CharField()
    
    def validate(self, data):
        login = data.get('login')
        password = data.get('password')
        
        if login and password:
            user = None
            
            # Multi-field authentication
            if '@' in login:
                try:
                    user = CustomUser.objects.get(email=login)
                except CustomUser.DoesNotExist:
                    pass
            elif login.startswith('+'):
                try:
                    user = CustomUser.objects.get(phone_number=login)
                except CustomUser.DoesNotExist:
                    pass
            else:
                # Try badge_number first, then username
                try:
                    user = CustomUser.objects.get(badge_number=login)
                except CustomUser.DoesNotExist:
                    try:
                        user = CustomUser.objects.get(username=login)
                    except CustomUser.DoesNotExist:
                        pass
            
            if user:
                user = authenticate(username=user.badge_number, password=password)
            
            if user and user.is_active:
                data['user'] = user
                return data
            
            raise serializers.ValidationError("Invalid credentials.")
        raise serializers.ValidationError("Must include 'login' and 'password'.")

class EmergencyBypassSerializer(serializers.Serializer):
    badge_number = serializers.CharField()
    reason = serializers.CharField(required=False)

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            'id', 'badge_number', 'username', 'email', 'phone_number', 'user_type',
            'first_name', 'last_name', 'certification_level', 
            'emergency_contact_name', 'emergency_contact_phone',
            'date_joined', 'last_login'
        )
        read_only_fields = ('id', 'date_joined', 'last_login')