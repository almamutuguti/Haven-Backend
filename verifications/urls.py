
from django.urls import path
from . import views

urlpatterns = [
    path('api/pending/', views.PendingVerificationsView.as_view(), name='pending-verifications'),
    path('api/history/', views.VerificationHistoryView.as_view(), name='verification-history'),
    path('api/stats/', views.VerificationStatsView.as_view(), name='verification-stats'),
    path('api/<int:verification_id>/approve/', views.ApproveVerificationView.as_view(), name='approve-verification'),
    path('api/<int:verification_id>/reject/', views.RejectVerificationView.as_view(), name='reject-verification'),
    path('api/<int:verification_id>/request-info/', views.RequestInfoVerificationView.as_view(), name='request-info-verification'),
    path('api/send-notification/', views.SendVerificationNotificationView.as_view(), name='send-verification-notification'),
    path('api/manual-email-verify/', views.ManualEmailVerificationView.as_view(), name='manual-email-verification'),
]