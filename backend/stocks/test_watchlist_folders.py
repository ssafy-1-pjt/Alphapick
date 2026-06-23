from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Stock


User = get_user_model()


class WatchlistFolderApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="watcher", password="password123")
        self.stock = Stock.objects.create(ticker="005930.KS", name="삼성전자", market="KOSPI", sector="반도체")
        self.client.force_authenticate(self.user)

    def test_user_can_group_and_ungroup_watchlist_stock(self):
        folder_response = self.client.post("/api/watchlist/folders/", {"name": "반도체"}, format="json")
        folder_id = folder_response.data["id"]
        save_response = self.client.post(f"/api/watchlist/{self.stock.ticker}/", {"folder_id": folder_id}, format="json")
        list_response = self.client.get("/api/watchlist/")
        delete_folder_response = self.client.delete(f"/api/watchlist/folders/{folder_id}/")
        after_delete_response = self.client.get("/api/watchlist/")

        self.assertEqual(folder_response.status_code, 201)
        self.assertEqual(save_response.status_code, 201)
        self.assertEqual(list_response.data["results"][0]["folder"]["name"], "반도체")
        self.assertEqual(delete_folder_response.status_code, 204)
        self.assertIsNone(after_delete_response.data["results"][0]["folder"])
