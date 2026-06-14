from django.test import TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.cooperative.models import Cooperative, Branch
from apps.core.test_client import SafeClient
from apps.members.cooperative_defaults import get_mgowelo_cooperative
from apps.members.models import Member
from apps.payments.models import Payment


class WorkflowGuardrailsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.coop = Cooperative.objects.create(
            name="Workflow AMCOS",
            code="WFAMCOS1",
            type="amcos",
            status="active",
            registration_fee=100000,
        )
        cls.super_admin = User.objects.create_user(
            username="wf_admin",
            password="testpass123",
            phone="255700000001",
            role="super_admin",
            is_staff=True,
            cooperative_id=cls.coop.id,
            is_verified=True,
        )
        cls.coop_admin = User.objects.create_user(
            username="wf_coop_admin",
            password="testpass123",
            phone="255700000002",
            role="cooperative_admin",
            cooperative_id=cls.coop.id,
            is_verified=True,
        )
        cls.member_user = User.objects.create_user(
            username="wf_member",
            password="testpass123",
            phone="255700000003",
            role="member",
            cooperative_id=cls.coop.id,
            is_verified=True,
        )
        cls.member = Member.objects.create(
            cooperative_id=cls.coop.id,
            user_id=cls.member_user.id,
            member_number="MGW-2026-9999",
            first_name="Flow",
            last_name="Member",
            phone="255700000003",
            gender="other",
            status="pending",
        )
        cls.member_user.member_id = cls.member.id
        cls.member_user.save(update_fields=["member_id"])

    def login_with_coop(self, user):
        client = SafeClient()
        client.force_login(user)
        session = client.session
        session["cooperative_id"] = user.cooperative_id
        session.save()
        return client

    def test_key_pages_load_for_admin(self):
        client = self.login_with_coop(self.super_admin)
        paths = [
            reverse("core:dashboard"),
            reverse("members:list"),
            reverse("payments:list"),
            reverse("savings:list"),
            reverse("loans:list"),
            reverse("accounting:dashboard"),
            reverse("governance:meetings"),
            reverse("reporting:dashboard"),
            reverse("notifications:inbox"),
        ]
        for path in paths:
            with self.subTest(path=path):
                response = client.get(path, follow=True)
                self.assertEqual(response.status_code, 200)

    def test_member_cannot_approve_member(self):
        client = self.login_with_coop(self.member_user)
        response = client.get(reverse("members:approve", args=[self.member.id]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.member.refresh_from_db()
        self.assertNotEqual(self.member.status, "active")

    def test_submit_transaction_can_auto_verify(self):
        client = self.login_with_coop(self.member_user)
        response = client.post(
            reverse("payments:submit_transaction"),
            {
                "payment_type": "contribution",
                "payment_method": "mpesa",
                "amount": "15000",
                "phone": "255700000003",
                "transaction_id": "MPESA-WF-123456",
                "description": "workflow test payment",
                "pay_simulation": "1",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        payment = Payment.objects.filter(transaction_id="MPESA-WF-123456").latest("id")
        self.assertEqual(payment.status, "completed")
        self.assertEqual(payment.verification_method, "auto")

    def test_member_cannot_edit_cooperative_profile(self):
        client = self.login_with_coop(self.member_user)
        original_name = self.coop.name
        response = client.post(
            reverse('cooperative:profile'),
            {'name': 'Hacked Cooperative Name'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.coop.refresh_from_db()
        self.assertEqual(self.coop.name, original_name)

    def test_register_member_creates_member_record(self):
        client = SafeClient()
        response = client.post(
            reverse("auth:register_member"),
            {
                "payment_method": "mpesa",
                "payment_phone": "255712345678",
                "first_name": "New",
                "last_name": "Applicant",
                "phone": "255700000111",
                "email": "new@app.test",
                "national_id": "19990101-11111-00001-00",
                "password": "testpass123",
                "confirm_password": "testpass123",
                "hectares": "10",
                "accept_terms": "1",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        mgowelo = get_mgowelo_cooperative()
        user = User.objects.get(phone="255700000111")
        member = Member.objects.get(user_id=user.id)
        self.assertEqual(member.cooperative_id, mgowelo.id)
        payment = Payment.objects.filter(member_id=member.id, payment_type="registration_fee").latest("id")
        self.assertEqual(payment.status, "completed")

    def test_branch_create_uses_foreign_key(self):
        client = self.login_with_coop(self.coop_admin)
        response = client.post(
            reverse("cooperative:branch_create"),
            {
                "name": "HQ Branch",
                "code": "WF-HQ",
                "address": "HQ Street",
                "city": "Dar",
                "region": "Dar",
                "phone": "255700000222",
                "email": "hq@wf.test",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        branch = Branch.objects.get(code="WF-HQ")
        self.assertEqual(branch.cooperative_id, self.coop.id)
