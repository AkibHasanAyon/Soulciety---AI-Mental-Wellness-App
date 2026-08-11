from django.db import transaction
from django.db.models import Q, Count, F
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from accounts.models import CustomUser
from user_profiles.models import UserProfile
from user_profiles.serializers import UserPublicSerializer
from notifications.helpers import create_notification

from .models import CommunityPost, Like, Comment, Follow, PostReport, DailyPrompt
from .serializers import (
    CommunityPostSerializer, PostDetailSerializer,
    CommentSerializer, PostReportCreateSerializer, DailyPromptSerializer
)

class PostListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        GET /api/community/posts/?tab=all|following|my
        """
        tab = request.query_params.get('tab', 'all').lower()

        if tab == 'following':
            following_ids = Follow.objects.filter(follower=request.user).values_list('following', flat=True)
            posts = CommunityPost.objects.filter(user__id__in=following_ids, is_active=True)
        elif tab == 'my':
            posts = CommunityPost.objects.filter(user=request.user, is_active=True)
        else:
            posts = CommunityPost.objects.filter(is_active=True)

        # Optimize with select_related for the user profile (used in UserPublicSerializer)
        posts = posts.select_related('user__profile').annotate(
            computed_comments_count=Count('comments')
        ).order_by('-created_at')

        serializer = CommunityPostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CommunityPostSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            post = serializer.save(user=request.user)
            return Response(
                CommunityPostSerializer(post, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class PostDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user=None):
        try:
            if user:
                return CommunityPost.objects.get(id=pk, user=user, is_active=True)
            return CommunityPost.objects.get(id=pk, is_active=True)
        except CommunityPost.DoesNotExist:
            return None

    def get(self, request, pk):
        post = self.get_object(pk)
        if not post:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = PostDetailSerializer(post, context={'request': request})
        return Response(serializer.data)

    # --- ADDED PUT METHOD ---
    def put(self, request, pk):
        post = self.get_object(pk, user=request.user)
        if not post:
            return Response({"error": "Post not found or permission denied"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CommunityPostSerializer(post, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # --- ADDED PATCH METHOD ---
    def patch(self, request, pk):
        post = self.get_object(pk, user=request.user)
        if not post:
            return Response({"error": "Post not found or permission denied"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CommunityPostSerializer(post, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        post = self.get_object(pk, user=request.user)
        if not post:
            return Response({"error": "Post not found or permission denied"}, status=status.HTTP_404_NOT_FOUND)
        
        # This triggers your model's delete() which cleans up Cloudinary
        post.delete()
        return Response({"message": "Post deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
    

class LikeToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        post = CommunityPost.objects.filter(id=post_id, is_active=True).first()
        if not post:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        like, created = Like.objects.get_or_create(user=request.user, post=post)
        
        if created:
            # Atomic increment
            CommunityPost.objects.filter(id=post_id).update(likes_count=F('likes_count') + 1)
            
            # Notification Logic
            if post.user != request.user:
                sender_name = getattr(request.user, 'profile', None).full_name or "A user"
                transaction.on_commit(lambda: create_notification(
                    user=post.user,
                    title="New Like",
                    message=f"✨ {sender_name} liked your post.",
                    notif_type='post_like',
                    data={"type": "community", "post_id": str(post.id)}
                ))
            return Response({"liked": True, "message": "Post liked"})
        else:
            like.delete()
            # Atomic decrement
            CommunityPost.objects.filter(id=post_id).update(likes_count=F('likes_count') - 1)
            return Response({"liked": False, "message": "Post unliked"})

class CommentListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        comments = Comment.objects.filter(post_id=post_id).select_related('user__profile').order_by('created_at')
        serializer = CommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, post_id):
        post = CommunityPost.objects.filter(id=post_id, is_active=True).first()
        if not post:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = CommentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            comment = serializer.save(user=request.user, post=post)
            
            # Atomic increment
            CommunityPost.objects.filter(id=post_id).update(comments_count=F('comments_count') + 1)

            # Notification
            if post.user != request.user:
                sender_name = getattr(request.user, 'profile', None).full_name or "A user"
                transaction.on_commit(lambda: create_notification(
                    user=post.user,
                    title="New Comment",
                    message=f"💬 {sender_name} commented on your post.",
                    notif_type='post_comment',
                    data={"type": "community", "post_id": str(post.id)}
                ))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, comment_id):
        comment = Comment.objects.filter(id=comment_id).first()
        if not comment:
            return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if comment.user != request.user and comment.post.user != request.user:
            return Response({"error": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        post_id = comment.post.id
        comment.delete()
        
        # Atomic decrement
        CommunityPost.objects.filter(id=post_id).update(comments_count=F('comments_count') - 1)
        return Response(status=status.HTTP_204_NO_CONTENT)



class FollowingUsersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        following_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        following_profiles = UserProfile.objects.filter(user_id__in=following_ids).select_related('user')
        serializer = UserPublicSerializer(following_profiles, many=True, context={'request': request})
        return Response(serializer.data)



class UserPostListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        posts = CommunityPost.objects.filter(user_id=user_id, is_active=True).annotate(
            computed_comments_count=Count('comments')
        ).order_by('-created_at')
        
        serializer = CommunityPostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)

class FollowToggleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        if request.user.id == user_id:
            return Response({"error": "Cannot follow yourself"}, status=status.HTTP_400_BAD_REQUEST)

        target = CustomUser.objects.filter(id=user_id).first()
        if not target:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        follow, created = Follow.objects.get_or_create(follower=request.user, following=target)

        if created:
            sender_name = getattr(request.user, 'profile', None).full_name or "A user"
            transaction.on_commit(lambda: create_notification(
                user=target,
                title="New Follower",
                message=f"👤 {sender_name} started following you.",
                notif_type='user_follow',
                data={"type": "profile", "user_id": str(request.user.id)}
            ))
            return Response({"following": True, "message": "Followed"})
        else:
            follow.delete()
            return Response({"following": False, "message": "Unfollowed"})


class PostReportCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PostReportCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        post_id = serializer.validated_data['post_id']
        reason = serializer.validated_data['reason']

        post = CommunityPost.objects.filter(id=post_id, is_active=True).first()
        if not post:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)

        PostReport.objects.create(
            reporter=request.user,
            post=post,
            reported_post_id=post.id,
            reason=reason
        )

        return Response(
            {"message": "Post reported successfully"},
            status=status.HTTP_201_CREATED
        )


class TodayPromptView(APIView):
    """Returns the most recent daily AI prompt post."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Find the latest post from the system user
        post = (
            CommunityPost.objects
            .filter(
                user__email='soulciety-ai@system.local',
                is_active=True
            )
            .select_related('user__profile')
            .order_by('-created_at')
            .first()
        )

        if not post:
            return Response(
                {"message": "No daily prompt available yet."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CommunityPostSerializer(post, context={'request': request})
        return Response(serializer.data)