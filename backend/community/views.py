from django.contrib.auth import get_user_model
from django.db.models import Count, Prefetch
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Comment, Post, PostLike, UserFollow
from .serializers import CommentCreateSerializer, CommentSerializer, CommunityUserSerializer, PostSerializer


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


class UserFollowToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        target = generics.get_object_or_404(User, pk=user_id)
        if target.pk == request.user.pk:
            return Response({"detail": "자기 자신은 팔로우할 수 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        follow, created = UserFollow.objects.get_or_create(follower=request.user, following=target)
        following = created
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
        like, created = PostLike.objects.get_or_create(user=request.user, post=post)
        liked = created
        if not created:
            like.delete()
            liked = False
        return Response({"post": post.pk, "liked": liked, "likes_count": post.likes.count()})

    @action(detail=True, methods=["post"], url_path="comments")
    def comments(self, request, pk=None):
        post = self.get_object()
        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = Comment.objects.create(post=post, author=request.user, content=serializer.validated_data["content"])
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
        post_id = comment.post_id
        comment.delete()
        return Response({"deleted": comment_id, "post": post_id})
