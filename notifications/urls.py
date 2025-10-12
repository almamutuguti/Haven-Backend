from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'templates', views.NotificationTemplateViewSet, basename='notification-template')
router.register(r'preferences', views.UserNotificationPreferenceViewSet, basename='notification-preference')
router.register(r'sms-logs', views.SMSLogViewSet, basename='sms-log')
router.register(r'push-logs', views.PushNotificationLogViewSet, basename='push-log')
router.register(r'email-logs', views.EmailLogViewSet, basename='email-log')
router.register(r'admin-notifications', views.AdminNotificationViewSet, basename='admin-notification')

urlpatterns = [
    path('api/notifications/', include(router.urls)),
]

# Additional custom endpoints
urlpatterns += [
    path(
        'api/notifications/notifications/mark-all-read/',
        views.NotificationViewSet.as_view({'post': 'mark_all_as_read'}),
        name='mark-all-notifications-read'
    ),
    path(
        'api/notifications/notifications/unread-count/',
        views.NotificationViewSet.as_view({'get': 'unread_count'}),
        name='unread-notifications-count'
    ),
    path(
        'api/notifications/notifications/send-bulk/',
        views.NotificationViewSet.as_view({'post': 'send_bulk'}),
        name='send-bulk-notifications'
    ),
    path(
        'api/notifications/notifications/stats/',
        views.NotificationViewSet.as_view({'get': 'stats'}),
        name='notification-stats'
    ),
    path(
        'api/notifications/notifications/<uuid:pk>/mark-read/',
        views.NotificationViewSet.as_view({'post': 'mark_as_read'}),
        name='mark-notification-read'
    ),
    path(
        'api/notifications/preferences/quick-toggle/',
        views.UserNotificationPreferenceViewSet.as_view({'post': 'quick_toggle'}),
        name='notification-preference-toggle'
    ),
    path(
        'api/notifications/templates/<uuid:pk>/test/',
        views.NotificationTemplateViewSet.as_view({'post': 'test'}),
        name='test-notification-template'
    ),
    path(
        'api/notifications/admin-notifications/system-stats/',
        views.AdminNotificationViewSet.as_view({'get': 'system_stats'}),
        name='admin-notification-stats'
    ),
]