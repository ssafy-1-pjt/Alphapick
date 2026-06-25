from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Comment, CommunityNotification, Post, PostLike, UserFollow
from .moderation import validate_clean_text
from stocks.models import Stock


User = get_user_model()


class CommunityUserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    profile_image_url = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    is_me = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "nickname",
            "display_name",
            "profile_image_url",
            "risk_type",
            "followers_count",
            "following_count",
            "is_following",
            "is_me",
        )

    def get_display_name(self, obj):
        return obj.display_name()

    def get_profile_image_url(self, obj):
        if not obj.profile_image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.profile_image.url) if request else obj.profile_image.url

    def get_followers_count(self, obj):
        return obj.follower_relations.count()

    def get_following_count(self, obj):
        return obj.following_relations.count()

    def get_is_following(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        if request.user.pk == obj.pk:
            return False
        return UserFollow.objects.filter(follower=request.user, following=obj).exists()

    def get_is_me(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and request.user.pk == obj.pk)


class CommentSerializer(serializers.ModelSerializer):
    author = CommunityUserSerializer(read_only=True)
    can_delete = serializers.SerializerMethodField()
    post_stock = serializers.CharField(source="post.stock_id", read_only=True, allow_null=True)
    post_title = serializers.CharField(source="post.title", read_only=True)
    parent_id = serializers.IntegerField(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ("id", "post", "post_stock", "post_title", "parent_id", "author", "content", "created_at", "can_delete", "replies")
        read_only_fields = ("id", "post", "author", "created_at", "can_delete")

    def get_can_delete(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and request.user.pk == obj.author_id)

    def get_replies(self, obj):
        return CommentSerializer(obj.replies.all(), many=True, context=self.context).data


class CommentCreateSerializer(serializers.ModelSerializer):
    parent_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = Comment
        fields = ("content", "parent_id")

    def validate_content(self, value):
        try:
            cleaned = validate_clean_text(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        if not cleaned:
            raise serializers.ValidationError("댓글 내용을 입력해주세요.")
        return cleaned


class CommunityNotificationSerializer(serializers.ModelSerializer):
    actor = CommunityUserSerializer(read_only=True)
    post_title = serializers.CharField(source="post.title", read_only=True, default="")
    post_stock = serializers.CharField(source="post.stock_id", read_only=True, allow_null=True)
    comment_id = serializers.IntegerField(source="comment.id", read_only=True, allow_null=True)

    class Meta:
        model = CommunityNotification
        fields = (
            "id",
            "kind",
            "actor",
            "post",
            "post_title",
            "post_stock",
            "comment_id",
            "is_read",
            "created_at",
        )


class PostSerializer(serializers.ModelSerializer):
    stock = serializers.PrimaryKeyRelatedField(
        queryset=Stock.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    stock_name = serializers.CharField(source="stock.name", read_only=True)
    stock_sector = serializers.CharField(source="stock.sector", read_only=True)
    author = CommunityUserSerializer(read_only=True)
    comments = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    liked_by_me = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "stock",
            "stock_name",
            "stock_sector",
            "author",
            "title",
            "content",
            "created_at",
            "updated_at",
            "likes_count",
            "comments_count",
            "liked_by_me",
            "can_edit",
            "comments",
        )
        read_only_fields = ("id", "author", "created_at", "updated_at")

    def validate(self, attrs):
        if self.instance is None and not attrs.get("stock"):
            raise serializers.ValidationError({"stock": "종목 토론방 게시글에는 종목이 필요합니다."})
        return attrs

    def validate_title(self, value):
        try:
            cleaned = validate_clean_text(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        if not cleaned:
            raise serializers.ValidationError("제목을 입력해주세요.")
        return cleaned

    def validate_content(self, value):
        try:
            cleaned = validate_clean_text(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        if not cleaned:
            raise serializers.ValidationError("내용을 입력해주세요.")
        return cleaned

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_liked_by_me(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return PostLike.objects.filter(user=request.user, post=obj).exists()

    def get_can_edit(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and request.user.pk == obj.author_id)

    def get_comments(self, obj):
        return CommentSerializer(
            [comment for comment in obj.comments.all() if comment.parent_id is None],
            many=True,
            context=self.context,
        ).data
