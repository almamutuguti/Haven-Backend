from django.urls import path
from . import views

urlpatterns = [
    path('api/programs/', views.TrainingProgramListCreateAPIView.as_view(), name='training-program-list-create'),
    path('api/programs/<int:pk>/', views.TrainingProgramDetailAPIView.as_view(), name='training-program-detail'),
    path('api/programs/<int:training_id>/participants/', views.TrainingProgramParticipantsAPIView.as_view(), name='training-program-participants'),
    path('api/programs/<int:training_id>/join/', views.JoinTrainingProgramAPIView.as_view(), name='join-training-program'),
    path('api/statistics/', views.TrainingStatisticsAPIView.as_view(), name='training-statistics'),
]