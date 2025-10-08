# apps/accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    """Form for creating new users with easy data input"""
    
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
        }),
        help_text="Enter a strong password"
    )
    
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Confirm password',
        }),
        help_text="Enter the same password as above"
    )
    
    class Meta:
        model = CustomUser
        fields = (
            'badge_number', 'username', 'email', 'phone_number', 
            'user_type', 'first_name', 'last_name', 'certification_level',
            'emergency_contact_name', 'emergency_contact_phone'
        )
        widgets = {
            'badge_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., FA001, HS002, SA001',
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., john_doe, mary_smith',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., john@haven.com',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+254712345678',
            }),
            'user_type': forms.Select(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., John',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Doe',
            }),
            'certification_level': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Basic First Aid, EMT, Paramedic',
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Jane Doe',
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+254798765432',
            }),
        }
        help_texts = {
            'badge_number': 'Unique identifier for the user (e.g., FA001 for First Aider 001)',
            'user_type': 'Select the role of this user in the system',
            'phone_number': 'Kenyan format: +254712345678',
        }

    def clean_badge_number(self):
        badge_number = self.cleaned_data.get('badge_number')
        if CustomUser.objects.filter(badge_number=badge_number).exists():
            raise ValidationError("A user with this badge number already exists.")
        return badge_number

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and CustomUser.objects.filter(phone_number=phone_number).exists():
            raise ValidationError("A user with this phone number already exists.")
        return phone_number

class CustomUserChangeForm(UserChangeForm):
    """Form for updating existing users"""
    
    class Meta:
        model = CustomUser
        fields = (
            'badge_number', 'username', 'email', 'phone_number', 
            'user_type', 'first_name', 'last_name', 'certification_level',
            'emergency_contact_name', 'emergency_contact_phone',
            'is_active', 'is_staff', 'is_superuser'
        )
        widgets = {
            'badge_number': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'user_type': forms.Select(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'certification_level': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

class QuickUserCreateForm(forms.ModelForm):
    """Simplified form for quick user creation during testing"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Set password',
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ('badge_number', 'username', 'user_type', 'password')
        widgets = {
            'badge_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., FA001',
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., test_user',
            }),
            'user_type': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class BulkUserCreateForm(forms.Form):
    """Form for creating multiple test users at once"""
    
    user_type = forms.ChoiceField(
        choices=CustomUser.USER_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    count = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=3,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Number of test users to create (1-10)"
    )
    
    base_badge = forms.CharField(
        initial='TEST',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., TEST, DEMO, DEV',
        }),
        help_text="Base for badge numbers (e.g., TEST001, TEST002)"
    )