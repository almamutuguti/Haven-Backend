"""
URL configuration for HavenBackend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Schema view for Swagger/OpenAPI
schema_view = get_schema_view(
    openapi.Info(
        title="Haven Emergency Response Platform API",
        default_version='v1',
        description="""
        # Haven Emergency Response Platform - API Documentation
        
        ## Overview
        A scalable, mission-critical backend architecture for the Haven emergency response platform, 
        designed to be the most reliable and efficient emergency hospital integration system in Kenya.
        """,
        terms_of_service=" ",
        contact=openapi.Contact(email="mutugutialma@gmail.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('geolocation/', include('geolocation.urls')),
    path('emergencies/', include('emergencies.urls')),
    path('hospitals/', include('hospitals.urls')),
    path('hospital-comms/', include('hospital_communication.urls')),  # For hospital communication endpoints
    path('notifications/', include('notifications.urls')),  # For notification endpoints

    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    
]

urlpatterns += staticfiles_urlpatterns()

