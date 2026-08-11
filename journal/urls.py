from django.urls import path
from .views import JournalEntryListCreateView, JournalEntryDetailView, JournalArchiveToggleView, JournalArchivedListView

urlpatterns = [
    # List all entries & create new one
    path('entries/', JournalEntryListCreateView.as_view(), name='journal-entries'),

    # Get, update, or delete a specific entry
    path('entries/<int:pk>/', JournalEntryDetailView.as_view(), name='journal-entry-detail'),
    
        # New Archive route
      # Archive Logic
    path('entries/<int:pk>/archive/', JournalArchiveToggleView.as_view(), name='journal-archive-toggle'),
    path('archived/', JournalArchivedListView.as_view(), name='journal-archived-list'),
]