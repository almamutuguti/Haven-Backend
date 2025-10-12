from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import HttpResponseRedirect
from django.utils import timezone
from .models import (
    Notification,
    NotificationTemplate,
    SMSLog,
    PushNotificationLog,
    EmailLog,
    UserNotificationPreference
)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'notification_type', 'channel', 'status', 
        'priority', 'created_at', 'notification_actions'
    ]
    list_filter = ['status', 'notification_type', 'channel', 'priority', 'created_at']
    search_fields = ['user__email', 'user__phone_number', 'title', 'message']
    readonly_fields = ['created_at', 'sent_at', 'delivered_at', 'read_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Recipient Information', {
            'fields': ('user',)
        }),
        ('Notification Content', {
            'fields': ('title', 'message', 'notification_type', 'priority')
        }),
        ('Delivery Information', {
            'fields': ('channel', 'status', 'retry_count')
        }),
        ('Related Objects', {
            'fields': ('emergency_alert', 'hospital_communication')
        }),
        ('Metadata', {
            'fields': ('metadata', 'scheduled_for')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'sent_at', 'delivered_at', 'read_at')
        }),
    )
    
    def notification_actions(self, obj):
        actions = []
        if obj.status in ['pending', 'failed'] and obj.retry_count < 3:
            actions.append(
                f'<a class="button" href="{obj.id}/retry/">Retry</a>'
            )
        if obj.status == 'sent' and not obj.read_at:
            actions.append(
                f'<a class="button" href="{obj.id}/mark-read/">Mark Read</a>'
            )
        return format_html('&nbsp;'.join(actions)) if actions else '-'
    notification_actions.short_description = 'Actions'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
    
    def retry_notification(self, request, notification_id, *args, **kwargs):
        """Retry sending a failed notification"""
        from .services import NotificationOrchestrator
        
        notification = Notification.objects.get(id=notification_id)
        orchestrator = NotificationOrchestrator()
        success = orchestrator.send_notification(notification)
        
        if success:
            self.message_user(request, "Notification retried successfully")
        else:
            self.message_user(request, "Failed to retry notification", level='error')
        
        return HttpResponseRedirect('../../')
    
    def mark_as_read(self, request, notification_id, *args, **kwargs):
        """Mark notification as read"""
        notification = Notification.objects.get(id=notification_id)
        notification.mark_as_read()
        
        self.message_user(request, "Notification marked as read")
        return HttpResponseRedirect('../../')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<uuid:notification_id>/retry/',
                self.admin_site.admin_view(self.retry_notification),
                name='retry-notification',
            ),
            path(
                '<uuid:notification_id>/mark-read/',
                self.admin_site.admin_view(self.mark_as_read),
                name='mark-notification-read',
            ),
        ]
        return custom_urls + urls

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'notification_type', 'channel', 'priority', 'is_active', 'updated_at']
    list_filter = ['notification_type', 'channel', 'is_active', 'updated_at']
    search_fields = ['name', 'title_template', 'message_template']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'notification_type', 'channel', 'priority', 'is_active')
        }),
        ('Template Content', {
            'fields': ('title_template', 'message_template')
        }),
        ('Help Text', {
            'fields': ('variables_help',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ['phone_number', 'status', 'cost', 'sent_at', 'delivered_at']
    list_filter = ['status', 'provider', 'sent_at']
    search_fields = ['phone_number', 'message', 'message_id']
    readonly_fields = ['sent_at', 'delivered_at']
    date_hierarchy = 'sent_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('notification')

@admin.register(PushNotificationLog)
class PushNotificationLogAdmin(admin.ModelAdmin):
    list_display = ['device_token', 'platform', 'status', 'sent_at']
    list_filter = ['platform', 'status', 'sent_at']
    search_fields = ['device_token', 'notification__title']
    readonly_fields = ['sent_at', 'delivered_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('notification')

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'subject', 'status', 'sent_at']
    list_filter = ['status', 'sent_at']
    search_fields = ['recipient', 'subject']
    readonly_fields = ['sent_at', 'delivered_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('notification')

@admin.register(UserNotificationPreference)
class UserNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'push_enabled', 'sms_enabled', 'email_enabled', 'updated_at']
    list_filter = ['push_enabled', 'sms_enabled', 'email_enabled', 'voice_enabled', 'updated_at']
    search_fields = ['user__email', 'user__phone_number']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Channel Preferences', {
            'fields': ('push_enabled', 'sms_enabled', 'email_enabled', 'voice_enabled')
        }),
        ('Emergency Notifications', {
            'fields': ('emergency_push', 'emergency_sms', 'emergency_voice')
        }),
        ('Update Preferences', {
            'fields': ('eta_updates', 'hospital_updates', 'system_alerts')
        }),
        ('Quiet Hours', {
            'fields': ('quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end')
        }),
        ('Rate Limiting', {
            'fields': ('max_notifications_per_hour',)
        }),
        ('Last Updated', {
            'fields': ('updated_at',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

# Custom Admin Actions
def retry_failed_notifications(modeladmin, request, queryset):
    """Retry multiple failed notifications"""
    from .services import NotificationOrchestrator
    
    orchestrator = NotificationOrchestrator()
    success_count = 0
    fail_count = 0
    
    for notification in queryset.filter(status__in=['failed', 'pending']):
        if orchestrator.send_notification(notification):
            success_count += 1
        else:
            fail_count += 1
    
    modeladmin.message_user(
        request, 
        f"Retried {success_count} notifications successfully. Failed: {fail_count}"
    )

retry_failed_notifications.short_description = "Retry selected failed notifications"

def mark_as_delivered(modeladmin, request, queryset):
    """Mark notifications as delivered (for testing)"""
    updated = queryset.update(
        status='delivered',
        delivered_at=timezone.now()
    )
    modeladmin.message_user(request, f"Marked {updated} notifications as delivered")

mark_as_delivered.short_description = "Mark selected as delivered"

# Add actions to Notification admin
NotificationAdmin.actions = [retry_failed_notifications, mark_as_delivered]