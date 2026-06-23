from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CommentDetailView,
    CommunityUserListView,
    FollowingUserListView,
    NotificationListView,
    NotificationReadAllView,
    NotificationReadView,
    NotificationUnreadCountView,
    PostViewSet,
    UserActivityView,
    UserFollowToggleView,
)


router = DefaultRouter()
router.register("posts", PostViewSet, basename="community-post")

urlpatterns = [
    path("", include(router.urls)),
    path("users/", CommunityUserListView.as_view(), name="community-users"),
    path("users/following/", FollowingUserListView.as_view(), name="community-following-users"),
    path("users/<int:user_id>/activity/", UserActivityView.as_view(), name="community-user-activity"),
    path("users/<int:user_id>/follow/", UserFollowToggleView.as_view(), name="community-user-follow"),
    path("notifications/", NotificationListView.as_view(), name="community-notifications"),
    path("notifications/unread-count/", NotificationUnreadCountView.as_view(), name="community-notification-unread-count"),
    path("notifications/read-all/", NotificationReadAllView.as_view(), name="community-notification-read-all"),
    path("notifications/<int:notification_id>/read/", NotificationReadView.as_view(), name="community-notification-read"),
    path("comments/<int:comment_id>/", CommentDetailView.as_view(), name="community-comment-detail"),
]
