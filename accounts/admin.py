from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser, EmergencyAccessLog, Organization

# Define forms inline to avoid circular imports
class InlineCustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('badge_number', 'username', 'email', 'role', 'phone', 'hospital', 'organization')

class InlineCustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('badge_number', 'username', 'email', 'role', 'phone', 'hospital', 'organization', 'is_active', 'is_staff')

class InlineQuickUserCreateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('badge_number', 'username', 'role', 'hospital', 'organization')

class InlineBulkUserCreateForm(forms.Form):
    base_badge = forms.CharField(max_length=10, initial='TEST')
    count = forms.IntegerField(min_value=1, max_value=100, initial=10)
    role = forms.ChoiceField(choices=CustomUser.ROLE_CHOICES)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization_type', 'contact_person', 'phone', 'email', 'is_active', 'is_verified')
    list_filter = ('organization_type', 'is_active', 'is_verified', 'created_at')
    search_fields = ('name', 'contact_person', 'email', 'phone')
    ordering = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'organization_type', 'description')
        }),
        (_('Contact Information'), {
            'fields': ('contact_person', 'phone', 'email', 'website', 'address')
        }),
        (_('Status'), {
            'fields': ('is_active', 'is_verified')
        }),
        (_('Important Dates'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = InlineCustomUserChangeForm
    add_form = InlineCustomUserCreationForm
    
    list_display = ('badge_number', 'username', 'email', 'role', 'hospital', 'organization', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'hospital', 'organization')
    search_fields = ('badge_number', 'username', 'email', 'phone', 'first_name', 'last_name')
    ordering = ('badge_number',)
    
    fieldsets = (
        (None, {'fields': ('badge_number', 'password')}),
        (_('Personal info'), {'fields': ('username', 'first_name', 'last_name', 'email')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Haven Specific'), {
            'fields': (
                'role', 'phone', 'registration_number',
                'hospital', 'organization',
                'emergency_contact_name', 'emergency_contact_phone'
            )
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('badge_number', 'password1', 'password2', 'username'),
        }),
        (_('Haven Specific'), {
            'fields': (
                'role', 'email', 'phone', 'first_name', 'last_name',
                'hospital', 'organization',
                'registration_number', 'emergency_contact_name', 'emergency_contact_phone'
            )
        }),
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('quick-create/', self.admin_site.admin_view(self.quick_create_view), name='accounts_customuser_quick_create'),
            path('bulk-create/', self.admin_site.admin_view(self.bulk_create_view), name='accounts_customuser_bulk_create'),
        ]
        return custom_urls + urls
    
    def quick_create_view(self, request):
        """View for quick user creation"""
        if request.method == 'POST':
            form = InlineQuickUserCreateForm(request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                user.set_password('temp123')  # Set a default password
                user.save()
                messages.success(request, 'User created successfully!')
                return redirect('..')
        else:
            form = InlineQuickUserCreateForm()
        
        context = {
            **self.admin_site.each_context(request),
            'title': 'Quick User Creation',
            'form': form,
        }
        return render(request, 'admin/accounts/quick_create.html', context)
    
    def bulk_create_view(self, request):
        """View for bulk user creation"""
        if request.method == 'POST':
            form = InlineBulkUserCreateForm(request.POST)
            if form.is_valid():
                # Create multiple test users
                base_badge = form.cleaned_data['base_badge']
                count = form.cleaned_data['count']
                role = form.cleaned_data['role']
                
                for i in range(1, count + 1):
                    badge_number = f"{base_badge}{i:03d}"
                    username = f"test_{role}_{i:03d}"
                    
                    if not CustomUser.objects.filter(badge_number=badge_number).exists():
                        CustomUser.objects.create_user(
                            badge_number=badge_number,
                            username=username,
                            role=role,
                            password='testpass123'
                        )
                
                messages.success(request, f'Created {count} test users!')
                return redirect('..')
        else:
            form = InlineBulkUserCreateForm()
        
        context = {
            **self.admin_site.each_context(request),
            'title': 'Bulk User Creation',
            'form': form,
        }
        return render(request, 'admin/accounts/bulk_create.html', context)


@admin.register(EmergencyAccessLog)
class EmergencyAccessLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'access_token', 'created_at', 'expires_at', 'ip_address', 'is_valid')
    list_filter = ('created_at',)
    search_fields = ('user__badge_number', 'user__username', 'access_token', 'reason')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'access_token', 'reason')
        }),
        (_('Access Details'), {
            'fields': ('created_at', 'expires_at', 'ip_address')
        }),
    )
    
    def is_valid(self, obj):
        return obj.is_valid()
    is_valid.boolean = True
    is_valid.short_description = 'Is Valid'