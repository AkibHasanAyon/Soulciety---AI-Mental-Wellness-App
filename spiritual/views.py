from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from .models import Category, VideoTrack, SuggestedVideo
from .serializers import CategorySerializer, VideoTrackSerializer, SuggestedVideoSerializer

class CategoryListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        categories = Category.objects.filter(is_active=True)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

class VideoListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        category_slug = request.query_params.get('category')
        search = request.query_params.get('search')
        
        queryset = VideoTrack.objects.filter(is_active=True)
        
        if category_slug:
            queryset = queryset.filter(categories__slug=category_slug)
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        
        serializer = VideoTrackSerializer(queryset, many=True)
        return Response(serializer.data)

class FeaturedVideosView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        videos = VideoTrack.objects.filter(is_active=True, is_featured=True)[:10]
        serializer = VideoTrackSerializer(videos, many=True)
        return Response(serializer.data)

class SuggestedVideosView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        suggested = SuggestedVideo.objects.all()[:8]
        serializer = SuggestedVideoSerializer(suggested, many=True)
        return Response(serializer.data)

# spiritual/views.py
from django.db.models import F

class VideoDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            # 1. Fetch the video
            video = VideoTrack.objects.get(id=pk, is_active=True)
            
            # 2. ATOMIC INCREMENT: Increase views_count safely in the database
            VideoTrack.objects.filter(id=pk).update(views_count=F('views_count') + 1)
            
            # Refresh from DB to get the updated count for the response
            video.refresh_from_db()
            
            serializer = VideoTrackSerializer(video)
            return Response(serializer.data)
        except VideoTrack.DoesNotExist:
            return Response({"error": "Video not found"}, status=status.HTTP_404_NOT_FOUND)
        
        
        
# spiritual/views.py

class PopularVideosView(APIView):
    """
    GET /api/spiritual/popular/?limit=5
    Returns videos sorted by views_count (Highest to Lowest).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        # Get 'limit' from query params, default to 10 if not provided
        limit_param = request.query_params.get('limit', 10)
        
        try:
            limit = int(limit_param)
        except ValueError:
            limit = 10 # Fallback if someone sends "abc" instead of a number

        # Order by views_count descending
        videos = VideoTrack.objects.filter(is_active=True).order_by('-views_count')[:limit]
        
        serializer = VideoTrackSerializer(videos, many=True)
        return Response(serializer.data)
    
    
# spiritual/views.py
from .models import UserFavoriteVideo

class VideoBookmarkToggleView(APIView):
    """
    POST /api/spiritual/videos/<pk>/bookmark/
    Adds or removes a video from the user's favorites.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            video = VideoTrack.objects.get(id=pk, is_active=True)
        except VideoTrack.DoesNotExist:
            return Response({"error": "Video not found"}, status=status.HTTP_404_NOT_FOUND)

        # Logic: If exists -> Delete (Unbookmark), If not exists -> Create (Bookmark)
        favorite, created = UserFavoriteVideo.objects.get_or_create(user=request.user, video=video)

        if not created:
            favorite.delete()
            return Response({"is_bookmarked": False, "message": "Removed from bookmarks"})
        
        return Response({"is_bookmarked": True, "message": "Added to bookmarks"}, status=status.HTTP_201_CREATED)


class BookmarkedVideoListView(APIView):
    """
    GET /api/spiritual/bookmarks/
    Returns a list of videos bookmarked by the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get all favorite objects for this user
        favorites = UserFavoriteVideo.objects.filter(user=request.user).select_related('video')
        
        # Extract the video objects from the favorites
        videos = [f.video for f in favorites if f.video.is_active]
        
        # Serialize the video list
        serializer = VideoTrackSerializer(videos, many=True, context={'request': request})
        return Response(serializer.data)