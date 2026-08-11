from django.urls import path
from .views import (
    ProfileView, ChangePasswordView,
    SavedSpiritualView, JournalArchiveView, HelpCenterView
)

urlpatterns = [
    # Main profile (view + update settings)
    path('users/', ProfileView.as_view(), name='profile'),

    # Change password
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),

    # Saved Spiritual content
    path('saved-spiritual/', SavedSpiritualView.as_view(), name='saved-spiritual'),

    # Journal Archive
    path('journal-archive/', JournalArchiveView.as_view(), name='journal-archive'),

    # Help Center
    path('help-center/', HelpCenterView.as_view(), name='help-center'),
]