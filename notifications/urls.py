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
    path('api/', include(router.urls)),
]

# Additional custom endpoints using class-based views
urlpatterns += [
    path(
        'api/mark-all-read/',
        views.MarkAllNotificationsReadAPIView.as_view(),
        name='mark-all-notifications-read'
    ),
    path(
        'api/unread-count/',
        views.UnreadNotificationsCountAPIView.as_view(),
        name='unread-notifications-count'
    ),
    path(
        'api/send-bulk/',
        views.SendBulkNotificationsAPIView.as_view(),
        name='send-bulk-notifications'
    ),
    path(
        'api/stats/',
        views.NotificationStatsAPIView.as_view(),
        name='notification-stats'
    ),
    path(
        'api/<uuid:pk>/mark-read/',
        views.MarkNotificationReadAPIView.as_view(),
        name='mark-notification-read'
    ),
    path(
        'api/quick-toggle/',
        views.NotificationPreferenceToggleAPIView.as_view(),
        name='preference-toggle'
    ),
    path(
        'api/templates/<uuid:pk>/test/',
        views.TestNotificationTemplateAPIView.as_view(),
        name='test-notification-template'
    ),
    path(
        'api/system-stats/',
        views.AdminNotificationStatsAPIView.as_view(),
        name='system-stats'
    ),
]