from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Comment, CommunityNotification, Post, PostLike, UserFollow
from stocks.models import Stock


User = get_user_model()


class CommunityApiTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="password123", nickname="Alice")
        self.bob = User.objects.create_user(username="bob", password="password123", nickname="Bob")
        self.stock = Stock.objects.create(
            ticker="005930.KS",
            name="삼성전자",
            market="KOSPI",
            sector="반도체",
        )
        self.other_stock = Stock.objects.create(
            ticker="000660.KS",
            name="SK하이닉스",
            market="KOSPI",
            sector="반도체",
        )
        self.post = Post.objects.create(
            stock=self.stock,
            author=self.alice,
            title="첫 의견",
            content="오늘 포트폴리오 괜찮네요.",
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_user_cannot_follow_self(self):
        self.authenticate(self.alice)
        response = self.client.post(f"/api/community/users/{self.alice.pk}/follow/")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(UserFollow.objects.exists())

    def test_user_can_toggle_follow(self):
        self.authenticate(self.alice)

        first = self.client.post(f"/api/community/users/{self.bob.pk}/follow/")
        second = self.client.post(f"/api/community/users/{self.bob.pk}/follow/")

        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.data["following"])
        self.assertEqual(CommunityNotification.objects.filter(recipient=self.bob, actor=self.alice, kind="follow").count(), 1)
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.data["following"])
        self.assertFalse(UserFollow.objects.exists())

    def test_user_can_view_following_users_and_their_activity(self):
        Comment.objects.create(post=self.post, author=self.bob, content="작성 댓글")
        UserFollow.objects.create(follower=self.alice, following=self.bob)
        self.authenticate(self.alice)

        following = self.client.get("/api/community/users/following/")
        activity = self.client.get(f"/api/community/users/{self.bob.pk}/activity/")

        self.assertEqual(following.status_code, 200)
        self.assertEqual(following.data["results"][0]["id"], self.bob.pk)
        self.assertEqual(activity.status_code, 200)
        self.assertEqual(activity.data["user"]["id"], self.bob.pk)
        self.assertEqual(len(activity.data["comments"]), 1)

    def test_user_can_toggle_like(self):
        self.authenticate(self.bob)
        url = reverse("community-post-like", kwargs={"pk": self.post.pk})

        liked = self.client.post(url)
        unliked = self.client.post(url)

        self.assertEqual(liked.status_code, 200)
        self.assertTrue(liked.data["liked"])
        self.assertEqual(liked.data["likes_count"], 1)
        self.assertEqual(CommunityNotification.objects.filter(recipient=self.alice, actor=self.bob, kind="like").count(), 1)
        self.assertEqual(unliked.status_code, 200)
        self.assertFalse(unliked.data["liked"])
        self.assertEqual(unliked.data["likes_count"], 0)
        self.assertFalse(PostLike.objects.exists())

    def test_post_author_can_delete_post(self):
        self.authenticate(self.alice)

        response = self.client.delete(reverse("community-post-detail", kwargs={"pk": self.post.pk}))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Post.objects.filter(pk=self.post.pk).exists())

    def test_other_user_cannot_delete_post(self):
        self.authenticate(self.bob)

        response = self.client.delete(reverse("community-post-detail", kwargs={"pk": self.post.pk}))

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

    def test_posts_can_be_filtered_by_stock_ticker(self):
        Post.objects.create(
            stock=self.other_stock,
            author=self.bob,
            title="다른 종목 의견",
            content="하이닉스 토론입니다.",
        )

        response = self.client.get("/api/community/posts/?ticker=005930.KS")

        self.assertEqual(response.status_code, 200)
        posts = response.data["results"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["stock"], self.stock.ticker)

    def test_authenticated_user_creates_stock_discussion_post(self):
        self.authenticate(self.bob)

        response = self.client.post(
            "/api/community/posts/",
            {
                "stock": self.stock.ticker,
                "title": "삼성전자 전망",
                "content": "실적 흐름을 지켜보고 있습니다.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["stock"], self.stock.ticker)
        self.assertEqual(response.data["stock_name"], self.stock.name)

    def test_comment_author_can_delete_comment(self):
        self.authenticate(self.bob)
        create_response = self.client.post(
            reverse("community-post-comments", kwargs={"pk": self.post.pk}),
            {"content": "동의합니다."},
            format="json",
        )
        comment_id = create_response.data["comment"]["id"]

        delete_response = self.client.delete(f"/api/community/comments/{comment_id}/")

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(Comment.objects.filter(pk=comment_id).exists())

    def test_other_user_cannot_delete_comment(self):
        comment = Comment.objects.create(post=self.post, author=self.bob, content="제 댓글입니다.")
        self.authenticate(self.alice)

        response = self.client.delete(f"/api/community/comments/{comment.pk}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Comment.objects.filter(pk=comment.pk).exists())

    def test_post_and_comment_reject_profanity(self):
        self.authenticate(self.bob)
        post_response = self.client.post(
            "/api/community/posts/",
            {"stock": self.stock.ticker, "title": "시발 제목", "content": "정상 내용"},
            format="json",
        )
        comment_response = self.client.post(
            reverse("community-post-comments", kwargs={"pk": self.post.pk}),
            {"content": "ㅅ ㅂ 댓글"},
            format="json",
        )

        self.assertEqual(post_response.status_code, 400)
        self.assertIn("title", post_response.data)
        self.assertEqual(comment_response.status_code, 400)
        self.assertIn("content", comment_response.data)

    def test_user_can_create_reply_and_parent_with_reply_cannot_be_deleted(self):
        self.authenticate(self.bob)
        parent = Comment.objects.create(post=self.post, author=self.alice, content="원댓글")

        reply_response = self.client.post(
            reverse("community-post-comments", kwargs={"pk": self.post.pk}),
            {"content": "답글", "parent_id": parent.pk},
            format="json",
        )
        self.authenticate(self.alice)
        delete_response = self.client.delete(f"/api/community/comments/{parent.pk}/")
        post_response = self.client.get("/api/community/posts/?ticker=005930.KS")

        self.assertEqual(reply_response.status_code, 201)
        self.assertEqual(reply_response.data["comment"]["parent_id"], parent.pk)
        self.assertEqual(delete_response.status_code, 400)
        self.assertEqual(len(post_response.data["results"][0]["comments"]), 1)
        self.assertEqual(len(post_response.data["results"][0]["comments"][0]["replies"]), 1)

    def test_comment_and_reply_create_notifications_for_related_authors(self):
        charlie = User.objects.create_user(username="charlie", password="password123", nickname="Charlie")
        self.authenticate(self.bob)
        comment_response = self.client.post(
            reverse("community-post-comments", kwargs={"pk": self.post.pk}),
            {"content": "게시글 댓글"},
            format="json",
        )
        parent = Comment.objects.get(pk=comment_response.data["comment"]["id"])

        self.assertEqual(CommunityNotification.objects.filter(recipient=self.alice, kind="comment").count(), 1)
        self.assertFalse(CommunityNotification.objects.filter(recipient=self.bob).exists())

        self.authenticate(charlie)
        reply_response = self.client.post(
            reverse("community-post-comments", kwargs={"pk": self.post.pk}),
            {"content": "대댓글", "parent_id": parent.pk},
            format="json",
        )

        self.assertEqual(reply_response.status_code, 201)
        self.assertEqual(CommunityNotification.objects.filter(recipient=self.alice, kind="reply").count(), 1)
        self.assertEqual(CommunityNotification.objects.filter(recipient=self.bob, kind="reply").count(), 1)
