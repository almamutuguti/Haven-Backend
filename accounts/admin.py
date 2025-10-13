from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import CustomUser, EmergencyAccessLog
from .forms import CustomUserCreationForm, CustomUserChangeForm, QuickUserCreateForm, BulkUserCreateForm

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = ('badge_number', 'username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('badge_number', 'username', 'email', 'phone_number', 'first_name', 'last_name')
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
                'role', 'phone_number', 'registration_number',
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
                'role', 'email', 'phone_number', 'first_name', 'last_name',
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
            form = QuickUserCreateForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'User created successfully!')
                return redirect('..')
        else:
            form = QuickUserCreateForm()
        
        context = {
            **self.admin_site.each_context(request),
            'title': 'Quick User Creation',
            'form': form,
        }
        return render(request, 'admin/accounts/quick_create.html', context)
    
    def bulk_create_view(self, request):
        """View for bulk user creation"""
        if request.method == 'POST':
            form = BulkUserCreateForm(request.POST)
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
            form = BulkUserCreateForm()
        
        context = {
            **self.admin_site.each_context(request),
            'title': 'Bulk User Creation',
            'form': form,
        }
        return render(request, 'admin/accounts/bulk_create.html', context)

@admin.register(EmergencyAccessLog)
class EmergencyAccessLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'access_token', 'created_at', 'expires_at', 'ip_address')
    list_filter = ('created_at',)
    search_fields = ('user__badge_number', 'user__username', 'access_token', 'reason')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'