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

# Additional custom endpoints
urlpatterns += [
    path(
        'api/hospital-comms/communications/<uuid:pk>/acknowledge/',
        views.EmergencyHospitalCommunicationViewSet.as_view({'post': 'acknowledge'}),
        name='acknowledge-communication'
    ),
    path(
        'api/hospital-comms/communications/<uuid:pk>/update-preparation/',
        views.EmergencyHospitalCommunicationViewSet.as_view({'post': 'update_preparation'}),
        name='update-preparation'
    ),
    path(
        'api/hospital-comms/communications/<uuid:pk>/add-assessment/',
        views.EmergencyHospitalCommunicationViewSet.as_view({'post': 'add_assessment'}),
        name='add-assessment'
    ),
    path(
        'api/hospital-comms/communications/<uuid:pk>/update-status/',
        views.EmergencyHospitalCommunicationViewSet.as_view({'post': 'update_status'}),
        name='update-status'
    ),
    path(
        'api/hospital-comms/communications/<uuid:pk>/logs/',
        views.EmergencyHospitalCommunicationViewSet.as_view({'get': 'logs'}),
        name='communication-logs'
    ),
    path(
        'api/hospital-comms/communications/hospital-pending/',
        views.EmergencyHospitalCommunicationViewSet.as_view({'get': 'hospital_pending'}),
        name='hospital-pending'
    ),
    path(
        'api/hospital-comms/communications/first-aider-active/',
        views.EmergencyHospitalCommunicationViewSet.as_view({'get': 'first_aider_active'}),
        name='first-aider-active'
    ),
]