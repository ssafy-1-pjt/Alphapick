from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CommentDetailView, CommunityUserListView, PostViewSet, UserFollowToggleView


router = DefaultRouter()
router.register("posts", PostViewSet, basename="community-post")

urlpatterns = [
    path("", include(router.urls)),
    path("users/", CommunityUserListView.as_view(), name="community-users"),
    path("users/<int:user_id>/follow/", UserFollowToggleView.as_view(), name="community-user-follow"),
    path("comments/<int:comment_id>/", CommentDetailView.as_view(), name="community-comment-detail"),
]
