from django.urls import path
from .views import (
    CategoryListView, VideoListView, FeaturedVideosView,
    SuggestedVideosView, VideoDetailView, PopularVideosView,    VideoBookmarkToggleView, # New
    BookmarkedVideoListView  # New
)

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='categories'),
    path('videos/', VideoListView.as_view(), name='videos-list'),
    path('videos/popular/', PopularVideosView.as_view(), name='popular-videos'),
    # Bookmark routes
    path('videos/<int:pk>/bookmark/', VideoBookmarkToggleView.as_view(), name='video-bookmark-toggle'),
    path('videos/bookmarks/', BookmarkedVideoListView.as_view(), name='bookmarked-videos'),
    
    
    path('videos/featured/', FeaturedVideosView.as_view(), name='featured-videos'),
    path('videos/suggested/', SuggestedVideosView.as_view(), name='suggested-videos'),
    path('videos/<int:pk>/', VideoDetailView.as_view(), name='video-detail'),
    
]