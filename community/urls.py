from django.urls import path
from .views import (
    PostListCreateView, PostDetailView,
    LikeToggleView, CommentListCreateView, CommentDetailView, UserPostListView,
    FollowToggleView, FollowingUsersView, PostReportCreateView, TodayPromptView
)

urlpatterns = [
    # Main feed (All / Following / My posts)
    path('posts/<int:pk>/', PostListCreateView.as_view(), name='community-posts'),
    
    path('posts/', PostListCreateView.as_view(), name='community-posts-list'),

    # For GET (one), PUT (update), PATCH (partial update), and DELETE
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),

    # Single post
    path('posts/details/<int:pk>/', PostDetailView.as_view(), name='community-post-detail'),

    # Like toggle
    path('posts/<int:post_id>/like/', LikeToggleView.as_view(), name='post-like'),

    # Comments
    path('posts/<int:post_id>/comments/', CommentListCreateView.as_view(), name='post-comments'),
    
    path('posts/<int:comment_id>/comments/', CommentDetailView.as_view(), name='comment-delete'),
    
    # NEW: Route for getting posts of a specific user
    path('user/<int:user_id>/posts/', UserPostListView.as_view(), name='user-posts-list'),

    # Follow toggle
    path('users/<int:user_id>/follow/', FollowToggleView.as_view(), name='user-follow'),
    
    # New route for the top "Following" chat heads row
    path('following-users/', FollowingUsersView.as_view(), name='following-users'),

    # Report a post
    path('posts/report/', PostReportCreateView.as_view(), name='post-report-create'),

    # Daily AI prompt
    path('prompts/today/', TodayPromptView.as_view(), name='today-prompt'),
]