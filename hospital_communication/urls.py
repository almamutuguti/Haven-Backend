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
    r'patient-assessments', 
    views.PatientAssessmentViewSet,
    basename='patient-assessment'
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

router.register(
    r'reports',
    views.HospitalReportViewSet,
    basename='hospital-report'
)


urlpatterns = [
    path('api/', include(router.urls)),
]

# Additional custom endpoints using class-based views
urlpatterns += [
    path(
        'api/communications/hospital-pending/',
        views.HospitalPendingCommunicationsAPIView.as_view(),
        name='hospital-pending'
    ),
    path(
        'api/communications/first-aider-active/',
        views.FirstAiderActiveCommunicationsAPIView.as_view(),
        name='first-aider-active'
    ),
    path(
        'api/communications/<uuid:pk>/acknowledge/',
        views.AcknowledgeCommunicationAPIView.as_view(),
        name='acknowledge-communication'
    ),
    path(
        'api/communications/<uuid:pk>/update-preparation/',
        views.UpdatePreparationAPIView.as_view(),
        name='update-preparation'
    ),
    path(
        'api/communications/<uuid:pk>/add-assessment/',
        views.AddAssessmentAPIView.as_view(),
        name='add-assessment'
    ),
    path(
        'api/communications/<uuid:pk>/update-status/',
        views.UpdateStatusAPIView.as_view(),
        name='update-status'
    ),
    path(
        'api/communications/<uuid:pk>/logs/',
        views.CommunicationLogsAPIView.as_view(),
        name='communication-logs'
    ),

    path(
        'api/communications/<uuid:pk>/add-patient-assessment/',
        views.EmergencyHospitalCommunicationViewSet.as_view({'post': 'add_patient_assessment', 'put': 'add_patient_assessment'}),
        name='add-patient-assessment'
    ),
    path(
        'api/communications/<uuid:pk>/patient-assessment/',
        views.EmergencyHospitalCommunicationViewSet.as_view({'get': 'patient_assessment'}),
        name='get-patient-assessment'
    ),
    path(
        'api/communications/<uuid:pk>/delete-patient-assessment/',
        views.EmergencyHospitalCommunicationViewSet.as_view({'delete': 'delete_patient_assessment'}),
        name='delete-patient-assessment'
    ),
        path(
        'api/communications/create-with-assessment/',
        views.EmergencyHospitalCommunicationViewSet.as_view({'post': 'create_with_assessment'}),
        name='create-with-assessment'
    ),
        path(
        'api/communications/<uuid:pk>/get-or-create-assessment/',
        views.EmergencyHospitalCommunicationViewSet.as_view({'get': 'get_or_create_assessment'}),
        name='get-or-create-assessment'
    ),

     path(
        'api/reports/statistics/',
        views.HospitalStatisticsReportAPIView.as_view(),
        name='hospital-statistics-report'
    ),
    path(
        'api/reports/export-data/',
        views.ExportCommunicationsDataAPIView.as_view(),
        name='export-communications-data'
    ),
    path(
        'api/reports/generate/',
        views.HospitalReportViewSet.as_view({'post': 'generate'}),
        name='generate-report'
    ),
]