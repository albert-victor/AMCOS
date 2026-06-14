"""Authenticated page smoke tests — sidebar pages must load after nav UX changes."""
from django.test import TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.core.test_client import SafeClient


class NavPagesSmokeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="navtest_admin",
            password="testpass123",
            role="super_admin",
            is_staff=True,
        )

    def setUp(self):
        self.client = SafeClient()
        self.client.login(username="navtest_admin", password="testpass123")

    def test_key_module_pages_return_200(self):
        paths = [
            reverse("core:dashboard"),
            reverse("members:list"),
            reverse("loans:list"),
            reverse("savings:list"),
            reverse("payments:list"),
            reverse("notifications:inbox"),
            reverse("reporting:dashboard"),
        ]
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path, follow=True)
                self.assertEqual(
                    response.status_code,
                    200,
                    msg=f"Expected 200 for {path}, got {response.status_code}",
                )
                self.assertIn(b"nav-menu", response.content)
                self.assertIn(b"nav-footer", response.content)
                self.assertIn(b"app.js", response.content)
