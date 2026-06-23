from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase


User = get_user_model()


class RegisterApiTests(APITestCase):
    def payload(self, **overrides):
        data = {
            "username": "new_user",
            "nickname": "새 사용자",
            "email": "new.user@gmail.com",
            "password": "SecurePass!123",
            "risk_type": "neutral",
        }
        data.update(overrides)
        return data

    def test_register_accepts_supported_email_domain(self):
        response = self.client.post("/api/auth/register/", self.payload(), format="json")

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email="new.user@gmail.com").exists())

    def test_register_rejects_unsupported_email_domain(self):
        response = self.client.post("/api/auth/register/", self.payload(email="new@invalid.example"), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user(username="existing", email="same@naver.com", password="SecurePass!123")

        response = self.client.post("/api/auth/register/", self.payload(email="same@naver.com"), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_register_rejects_duplicate_nickname(self):
        User.objects.create_user(username="nickname_owner", nickname="중복닉네임", email="owner@naver.com", password="SecurePass!123")

        response = self.client.post("/api/auth/register/", self.payload(nickname="중복닉네임"), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("nickname", response.data)

    def test_register_returns_field_errors_for_short_username_and_password(self):
        response = self.client.post(
            "/api/auth/register/",
            self.payload(username="a", nickname="a", password="short"),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)
        self.assertIn("nickname", response.data)
        self.assertIn("password", response.data)

    def test_authenticated_user_can_update_nickname(self):
        user = User.objects.create_user(username="profile_user", nickname="기존닉네임", password="SecurePass!123")
        self.client.force_authenticate(user=user)

        response = self.client.patch("/api/users/me/", {"nickname": "새닉네임"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["nickname"], "새닉네임")
