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
            'style': 'width: 300px;'
        }),
        help_text="Enter a strong password"
    )
    
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Confirm password',
            'style': 'width: 300px;'
        }),
        help_text="Enter the same password as above"
    )
    
    class Meta:
        model = CustomUser
        fields = (
            'badge_number', 'username', 'email', 'phone', 
            'role', 'first_name', 'last_name', 'registration_number',
            'hospital', 'organization',
            'emergency_contact_name', 'emergency_contact_phone'
        )
        widgets = {
            'badge_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., FA001, HS002, SA001',
                'style': 'width: 300px;'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., john_doe, mary_smith',
                'style': 'width: 300px;'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., john@haven.com',
                'style': 'width: 300px;'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+254712345678',
                'style': 'width: 300px;'
            }),
            'role': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 300px;',
                'onchange': 'toggleHospitalOrganization()'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., John',
                'style': 'width: 300px;'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Doe',
                'style': 'width: 300px;'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., KRCFA12345, MOH7890',
                'style': 'width: 300px;'
            }),
            'hospital': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 300px;',
                'id': 'id_hospital'
            }),
            'organization': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 300px;',
                'id': 'id_organization'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Jane Doe',
                'style': 'width: 300px;'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+254798765432',
                'style': 'width: 300px;'
            }),
        }
        help_texts = {
            'badge_number': 'Unique identifier for the user (e.g., FA001 for First Aider 001)',
            'role': 'Select the role of this user in the system',
            'phone': 'Kenyan format: +254712345678',
            'hospital': 'Required for Hospital Staff',
            'organization': 'Required for First Aiders',
        }

    def clean_badge_number(self):
        badge_number = self.cleaned_data.get('badge_number')
        if CustomUser.objects.filter(badge_number=badge_number).exists():
            raise ValidationError("A user with this badge number already exists.")
        return badge_number

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and CustomUser.objects.filter(phone=phone).exists():
            raise ValidationError("A user with this phone number already exists.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        hospital = cleaned_data.get('hospital')
        organization = cleaned_data.get('organization')
        
        if role == 'hospital_staff' and not hospital:
            raise ValidationError({
                'hospital': 'Hospital is required for Hospital Staff.'
            })
        
        if role == 'first_aider' and not organization:
            raise ValidationError({
                'organization': 'Organization is required for First Aiders.'
            })
        
        return cleaned_data

class CustomUserChangeForm(UserChangeForm):
    """Form for updating existing users"""
    
    class Meta:
        model = CustomUser
        fields = (
            'badge_number', 'username', 'email', 'phone', 
            'role', 'first_name', 'last_name', 'registration_number',
            'hospital', 'organization',
            'emergency_contact_name', 'emergency_contact_phone',
            'is_active', 'is_staff', 'is_superuser'
        )
        widgets = {
            'badge_number': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 300px;'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 300px;'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'style': 'width: 300px;'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 300px;'
            }),
            'role': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 300px;',
                'onchange': 'toggleHospitalOrganization()'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 300px;'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 300px;'
            }),
            'registration_number': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 300px;'
            }),
            'hospital': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 300px;',
                'id': 'id_hospital'
            }),
            'organization': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 300px;',
                'id': 'id_organization'
            }),
            'emergency_contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 300px;'
            }),
            'emergency_contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'style': 'width: 300px;'
            }),
        }

class QuickUserCreateForm(forms.ModelForm):
    """Simplified form for quick user creation during testing"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Set password',
            'style': 'width: 300px;'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ('badge_number', 'username', 'role', 'hospital', 'organization', 'password')
        widgets = {
            'badge_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., FA001',
                'style': 'width: 300px;'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., test_user',
                'style': 'width: 300px;'
            }),
            'role': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 300px;',
                'onchange': 'toggleHospitalOrganization()'
            }),
            'hospital': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 300px;',
                'id': 'id_hospital'
            }),
            'organization': forms.Select(attrs={
                'class': 'form-control',
                'style': 'width: 300px;',
                'id': 'id_organization'
            }),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class BulkUserCreateForm(forms.Form):
    """Form for creating multiple test users at once"""
    
    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control',
            'style': 'width: 300px;'
        })
    )
    
    count = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=3,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'style': 'width: 300px;'
        }),
        help_text="Number of test users to create (1-10)"
    )
    
    base_badge = forms.CharField(
        initial='TEST',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., TEST, DEMO, DEV',
            'style': 'width: 300px;'
        }),
        help_text="Base for badge numbers (e.g., TEST001, TEST002)"
    )

class TestLoginForm(forms.Form):
    """Simple form to test login credentials"""
    
    login = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Badge number, username, email, or phone',
            'style': 'width: 300px;'
        }),
        help_text="Enter badge number, username, email, or phone number"
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'style': 'width: 300px;'
        })
    )

class EmergencyAccessTestForm(forms.Form):
    """Form to test emergency access functionality"""
    
    badge_number = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter badge number',
            'style': 'width: 300px;'
        }),
        help_text="Badge number of first aider or hospital staff"
    )
    
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Emergency reason (optional)',
            'rows': 3,
            'style': 'width: 300px;'
        })
    )