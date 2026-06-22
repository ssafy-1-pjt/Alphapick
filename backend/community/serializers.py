from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Comment, Post, PostLike, UserFollow
from stocks.models import Stock


User = get_user_model()


class CommunityUserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
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
            "risk_type",
            "followers_count",
            "following_count",
            "is_following",
            "is_me",
        )

    def get_display_name(self, obj):
        return obj.display_name()

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

    class Meta:
        model = Comment
        fields = ("id", "post", "author", "content", "created_at", "can_delete")
        read_only_fields = ("id", "post", "author", "created_at", "can_delete")

    def get_can_delete(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and request.user.pk == obj.author_id)


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("content",)

    def validate_content(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("댓글 내용을 입력해주세요.")
        return cleaned


class PostSerializer(serializers.ModelSerializer):
    stock = serializers.PrimaryKeyRelatedField(
        queryset=Stock.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    stock_name = serializers.CharField(source="stock.name", read_only=True)
    stock_sector = serializers.CharField(source="stock.sector", read_only=True)
    author = CommunityUserSerializer(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
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
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("제목을 입력해주세요.")
        return cleaned

    def validate_content(self, value):
        cleaned = value.strip()
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
