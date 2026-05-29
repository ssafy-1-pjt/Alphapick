from django.contrib import admin

from .models import Comment, Post, PostLike, UserFollow


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author", "created_at", "updated_at")
    search_fields = ("title", "content", "author__username", "author__nickname")
    list_filter = ("created_at",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "author", "created_at")
    search_fields = ("content", "author__username", "post__title")


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "user", "created_at")


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ("id", "follower", "following", "created_at")
