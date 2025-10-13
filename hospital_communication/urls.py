from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(
    r'communications', 
    views.EmergencyHospitalCommunicationViewSet,
    basename='emergency-communication'
)
router.register(
    r'logs', 
    views.CommunicationLogViewSet,
    basename='communication-log'
)
router.register(
    r'assessments', 
    views.FirstAiderAssessmentViewSet,
    basename='first-aider-assessment'
)

urlpatterns = [
    path('api/hospital-comms/', include(router.urls)),
]

# Additional custom endpoints using class-based views
urlpatterns += [
    path(
        'api/hospital-comms/communications/hospital-pending/',
        views.HospitalPendingCommunicationsAPIView.as_view(),
        name='hospital-pending'
    ),
    path(
        'api/hospital-comms/communications/first-aider-active/',
        views.FirstAiderActiveCommunicationsAPIView.as_view(),
        name='first-aider-active'
    ),
    path(
        'api/hospital-comms/communications/<uuid:pk>/acknowledge/',
        views.AcknowledgeCommunicationAPIView.as_view(),
        name='acknowledge-communication'
    ),
    path(
        'api/hospital-comms/communications/<uuid:pk>/update-preparation/',
        views.UpdatePreparationAPIView.as_view(),
        name='update-preparation'
    ),
    path(
        'api/hospital-comms/communications/<uuid:pk>/add-assessment/',
        views.AddAssessmentAPIView.as_view(),
        name='add-assessment'
    ),
    path(
        'api/hospital-comms/communications/<uuid:pk>/update-status/',
        views.UpdateStatusAPIView.as_view(),
        name='update-status'
    ),
    path(
        'api/hospital-comms/communications/<uuid:pk>/logs/',
        views.CommunicationLogsAPIView.as_view(),
        name='communication-logs'
    ),
]