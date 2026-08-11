"""
URL configuration for tlecap_backend project.

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

# tlecap_backend/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('app_home.urls')),  # ← add this
    path('api/', include('chat.urls')),
     path('api/spiritual/', include('spiritual.urls')),  # ← add this
     path('api/journal/', include('journal.urls')),  # ← add this
     path('api/community/', include('community.urls')),
     path('api/profile/', include('user_profiles.urls')),
     path('api/', include('notifications.urls')),
     path('api/healing/', include('healing_journey.urls')),
]
