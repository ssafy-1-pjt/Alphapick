from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Prefetch
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Comment, CommunityNotification, Post, PostLike, UserFollow
from .serializers import (
    CommentCreateSerializer,
    CommentSerializer,
    CommunityNotificationSerializer,
    CommunityUserSerializer,
    PostSerializer,
)


User = get_user_model()


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author_id == request.user.id


class CommunityUserListView(generics.ListAPIView):
    serializer_class = CommunityUserSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = User.objects.annotate(
            followers_total=Count("follower_relations", distinct=True),
            following_total=Count("following_relations", distinct=True),
        ).order_by("username")
        query = self.request.query_params.get("q")
        if query:
            queryset = queryset.filter(username__icontains=query)
        return queryset


class FollowingUserListView(generics.ListAPIView):
    serializer_class = CommunityUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            User.objects.filter(follower_relations__follower=self.request.user)
            .annotate(
                followers_total=Count("follower_relations", distinct=True),
                following_total=Count("following_relations", distinct=True),
            )
            .order_by("username")
        )


class UserActivityView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, user_id):
        user = generics.get_object_or_404(User, pk=user_id)
        posts = (
            Post.objects.filter(author=user)
            .select_related("author", "stock")
            .prefetch_related(
                "likes",
                Prefetch(
                    "comments",
                    queryset=Comment.objects.select_related("author").prefetch_related(
                        Prefetch("replies", queryset=Comment.objects.select_related("author").order_by("created_at"))
                    ).order_by("created_at"),
                ),
            )
            .order_by("-created_at")
        )
        comments = Comment.objects.filter(author=user).select_related("author", "post", "post__stock").order_by("-created_at")
        context = {"request": request}
        return Response(
            {
                "user": CommunityUserSerializer(user, context=context).data,
                "posts": PostSerializer(posts, many=True, context=context).data,
                "comments": CommentSerializer(comments, many=True, context=context).data,
            }
        )


class UserFollowToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        target = generics.get_object_or_404(User, pk=user_id)
        if target.pk == request.user.pk:
            return Response({"detail": "자기 자신은 팔로우할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        follow, created = UserFollow.objects.get_or_create(follower=request.user, following=target)
        following = created
        if created:
            CommunityNotification.objects.create(
                recipient=target,
                actor=request.user,
                kind=CommunityNotification.Kind.FOLLOW,
            )
        if not created:
            follow.delete()
            following = False

        serializer = CommunityUserSerializer(target, context={"request": request})
        return Response(
            {
                "following": following,
                "user": serializer.data,
            }
        )


class NotificationListView(generics.ListAPIView):
    serializer_class = CommunityNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return CommunityNotification.objects.filter(recipient=self.request.user).select_related(
            "actor", "post", "post__stock", "comment"
        )


class NotificationUnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"unread_count": CommunityNotification.objects.filter(recipient=request.user, is_read=False).count()})


class NotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, notification_id):
        notification = generics.get_object_or_404(CommunityNotification, pk=notification_id, recipient=request.user)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response({"id": notification.pk, "is_read": True})


class NotificationReadAllView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated = CommunityNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"updated": updated})


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    permission_classes = [IsAuthorOrReadOnly]

    def get_queryset(self):
        queryset = (
            Post.objects.select_related("author")
            .select_related("stock")
            .prefetch_related(
                "likes",
                Prefetch("comments", queryset=Comment.objects.select_related("author").order_by("created_at")),
            )
            .order_by("-created_at")
        )
        ticker = self.request.query_params.get("ticker")
        if ticker:
            queryset = queryset.filter(stock_id=ticker)
        return queryset

    def get_permissions(self):
        if self.action in {"update", "partial_update", "destroy"}:
            return [permissions.IsAuthenticated(), IsAuthorOrReadOnly()]
        if self.action in {"create", "like", "comments"}:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=["post"], url_path="like")
    def like(self, request, pk=None):
        post = self.get_object()
        with transaction.atomic():
            like = PostLike.objects.filter(user=request.user, post=post).first()
            if like:
                like.delete()
                liked = False
            else:
                PostLike.objects.create(user=request.user, post=post)
                liked = True
                if post.author_id != request.user.id:
                    CommunityNotification.objects.create(
                        recipient=post.author,
                        actor=request.user,
                        post=post,
                        kind=CommunityNotification.Kind.LIKE,
                    )
            likes_count = PostLike.objects.filter(post=post).count()
        return Response({"post": post.pk, "liked": liked, "likes_count": likes_count})

    @action(detail=True, methods=["post"], url_path="comments")
    def comments(self, request, pk=None):
        post = self.get_object()
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent_id = serializer.validated_data.get("parent_id")
        parent = None
        if parent_id:
            parent = generics.get_object_or_404(Comment, pk=parent_id)
            if parent.post_id != post.pk:
                return Response({"parent_id": ["같은 게시글의 댓글에만 답글을 작성할 수 있습니다."]}, status=status.HTTP_400_BAD_REQUEST)
        comment = Comment.objects.create(post=post, parent=parent, author=request.user, content=serializer.validated_data["content"])
        recipient_ids = {post.author_id}
        if parent:
            recipient_ids.add(parent.author_id)
        recipient_ids.discard(request.user.id)
        CommunityNotification.objects.bulk_create(
            [
                CommunityNotification(
                    recipient_id=recipient_id,
                    actor=request.user,
                    post=post,
                    comment=comment,
                    kind=CommunityNotification.Kind.REPLY if parent else CommunityNotification.Kind.COMMENT,
                )
                for recipient_id in recipient_ids
            ]
        )
        return Response(
            {
                "comment": CommentSerializer(comment, context={"request": request}).data,
                "comments_count": post.comments.count(),
            },
            status=status.HTTP_201_CREATED,
        )


class CommentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, comment_id):
        comment = generics.get_object_or_404(Comment, pk=comment_id)
        if comment.author_id != request.user.pk:
            return Response({"detail": "댓글 작성자만 삭제할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)
        if comment.replies.exists():
            return Response({"detail": "답글이 달린 댓글은 답글을 모두 삭제한 뒤 삭제할 수 있습니다."}, status=status.HTTP_400_BAD_REQUEST)
        post_id = comment.post_id
        comment.delete()
        return Response({"deleted": comment_id, "post": post_id})
