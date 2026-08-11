# healing_journey/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ── Phase 2: Assessment endpoints ──
    path('assessment/questions/', views.AssessmentQuestionsView.as_view(), name='healing-assessment-questions'),
    path('assessment/', views.AssessmentSubmitView.as_view(), name='healing-assessment-submit'),
    path('assessment/status/', views.AssessmentStatusView.as_view(), name='healing-assessment-status'),
    path('assessment/profile/', views.AssessmentProfileView.as_view(), name='healing-assessment-profile'),

    # Phase 4: Day endpoints
    path('days/<int:day_number>/', views.DayDetailView.as_view(), name='healing-day-detail'),

    # Phase 5: Plan & Today endpoints
    path('plan/', views.PlanOverviewView.as_view(), name='healing-plan'),
    path('today/', views.TodayView.as_view(), name='healing-today'),

    # Phase 6: Completion & Progress endpoints
    path('days/<int:day_number>/complete/', views.DayCompleteView.as_view(), name='healing-day-complete'),
    path('days/<int:day_number>/reflection/', views.HealingReflectionView.as_view(), name='healing-day-reflection'),
    path('progress/', views.ProgressView.as_view(), name='healing-progress'),

    # Phase 7: Settings endpoint
    path('settings/', views.SettingsView.as_view(), name='healing-settings'),

    # Phase 8: Reset endpoint
    path('reset/', views.ResetJourneyView.as_view(), name='healing-reset'),

    # Phase 9: Saved Affirmations & Community Sharing
    path('affirmations/', views.SavedAffirmationListView.as_view(), name='healing-affirmations-list'),
    path('affirmations/<int:pk>/', views.DeleteSavedAffirmationView.as_view(), name='healing-affirmations-delete'),
    path('days/<int:day_number>/save-affirmation/', views.SaveDayAffirmationView.as_view(), name='healing-save-affirmation'),
    path('days/<int:day_number>/share/', views.ShareToCommunityView.as_view(), name='healing-share-community'),
]
