"""Tests for Mgowelo member registration and board approval workflow."""
from decimal import Decimal

from django.contrib.auth import authenticate
from django.test import TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.core.test_client import SafeClient
from apps.cooperative.models import Cooperative
from apps.members.models import Member, MemberBoardApproval
from apps.members.member_access import (
    BOARD_APPROVALS_REQUIRED,
    get_member_lifecycle_stage,
    parse_hectares_from_post,
    activate_full_member_if_shares_paid,
)
from apps.members.cooperative_defaults import get_mgowelo_cooperative
from apps.members.services import record_board_approval
from apps.shares.models import Share


class HectaresValidationTest(TestCase):
    def test_minimum_hectares(self):
        class FakePost:
            def get(self, k, d=''):
                return {'hectares': '5'}.get(k, d)
        val, other, err_sw, _ = parse_hectares_from_post(FakePost())
        self.assertIsNone(val)
        self.assertIsNotNone(err_sw)

    def test_hectares_10_ok(self):
        class FakePost:
            def get(self, k, d=''):
                return {'hectares': '10'}.get(k, d)
        val, other, err_sw, err_en = parse_hectares_from_post(FakePost())
        self.assertEqual(val, Decimal('10'))
        self.assertIsNone(err_sw)


class BoardApprovalWorkflowTest(TestCase):
    def setUp(self):
        self.coop = get_mgowelo_cooperative()
        self.member_user = User.objects.create_user(
            username='255799900001',
            phone='255799900001',
            password='test123',
            first_name='Test',
            last_name='Farmer',
            role='member',
            cooperative_id=self.coop.id,
        )
        self.member = Member.objects.create(
            cooperative_id=self.coop.id,
            user_id=self.member_user.id,
            member_number='MGW-2026-9999',
            first_name='Test',
            last_name='Farmer',
            phone='255799900001',
            gender='male',
            status='payment_confirmed',
            registration_fee_paid=True,
            hectares=Decimal('12'),
        )
        self.member_user.member_id = self.member.id
        self.member_user.save()

        self.board_users = []
        for i in range(BOARD_APPROVALS_REQUIRED):
            u = User.objects.create_user(
                username=f'board_test_{i}',
                phone=f'25578880000{i}',
                password='board123',
                role='board_member',
                cooperative_id=self.coop.id,
            )
            self.board_users.append(u)

    def test_lifecycle_pending_board_then_approved(self):
        self.assertEqual(get_member_lifecycle_stage(self.member), 'pending_board')
        for u in self.board_users:
            record_board_approval(self.member, u.id)
            self.member.refresh_from_db()
        self.assertEqual(self.member.status, 'approved')
        self.assertEqual(get_member_lifecycle_stage(self.member), 'pending_shares')

    def test_full_member_after_shares(self):
        for u in self.board_users:
            record_board_approval(self.member, u.id)
        Share.objects.create(
            cooperative_id=self.coop.id,
            member_id=self.member.id,
            certificate_number='SHTEST001',
            total_shares=2,
            total_value=Decimal('200000'),
        )
        activate_full_member_if_shares_paid(self.member)
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, 'active')
        self.assertEqual(get_member_lifecycle_stage(self.member), 'full')


class RegisterMemberViewTest(TestCase):
    def setUp(self):
        self.coop = get_mgowelo_cooperative()
        self.client = SafeClient()

    def test_register_success_redirects_and_pending_board(self):
        url = reverse('auth:register_member')
        phone = '255799900088'
        data = {
            'first_name': 'Juma',
            'last_name': 'Mkulima',
            'hectares': '10',
            'phone': phone,
            'email': 'juma.mkulima@example.test',
            'national_id': '19980101-22222-00001-00',
            'password': 'pass1234',
            'confirm_password': 'pass1234',
            'payment_method': 'mpesa',
            'payment_phone': phone,
            'accept_terms': '1',
        }
        resp = self.client.post(url, data, follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('registered=1', resp.url)
        member = Member.objects.filter(phone=phone).first()
        self.assertIsNotNone(member)
        self.assertTrue(member.registration_fee_paid)
        self.assertEqual(member.status, 'payment_confirmed')
        self.assertEqual(get_member_lifecycle_stage(member), 'pending_board')
