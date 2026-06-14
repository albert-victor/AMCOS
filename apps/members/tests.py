from django.test import TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.core.test_client import SafeClient
from apps.cooperative.models import Cooperative
from apps.members.models import Member
from apps.payments.models import Payment


class MemberCreatePaymentGuardTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.coop = Cooperative.objects.create(
            name='Create Guard AMCOS',
            code='CGAMCOS1',
            type='amcos',
            status='active',
            registration_fee=100000,
        )
        cls.coop_admin = User.objects.create_user(
            username='cg_coop_admin',
            password='testpass123',
            phone='255700000101',
            role='cooperative_admin',
            cooperative_id=cls.coop.id,
            is_verified=True,
        )

    def login_with_coop(self, user):
        client = SafeClient()
        client.force_login(user)
        session = client.session
        session['cooperative_id'] = user.cooperative_id
        session.save()
        return client

    def test_registration_fee_rejected_without_valid_reference(self):
        from apps.payments.services import ensure_registration_fee_paid
        payment, err = ensure_registration_fee_paid(
            cooperative_id=self.coop.id,
            payment_ref='',
            payment_method='mpesa',
            payment_method_other='',
            payment_phone='255712345678',
            payer_description='test',
        )
        self.assertIsNone(payment)
        self.assertEqual(err, 'invalid_reference')

    def test_member_create_succeeds_with_verified_payment(self):
        client = self.login_with_coop(self.coop_admin)
        response = client.post(
            reverse('members:create'),
            {
                'payment_method': 'mpesa',
                'payment_phone': '255712345678',
                'payment_reference': 'ADMIN-REG-123456',
                'first_name': 'Manual',
                'last_name': 'Paid',
                'phone': '255700000303',
                'gender': 'male',
                'password': 'temp1234',
                'confirm_password': 'temp1234',
            },
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        member = Member.objects.get(phone='255700000303')
        self.assertTrue(member.registration_fee_paid)
        self.assertEqual(member.status, 'payment_confirmed')
        payment = Payment.objects.filter(member_id=member.id, payment_type='registration_fee').latest('id')
        self.assertEqual(payment.status, 'completed')
        self.assertEqual(payment.transaction_id, 'ADMIN-REG-123456')
        user = User.objects.get(id=member.user_id)
        self.assertTrue(user.must_change_password)
        self.assertEqual(user.role, 'member')

    def test_admin_registered_user_must_reset_password_on_login(self):
        client = self.login_with_coop(self.coop_admin)
        create_resp = client.post(
            reverse('members:create'),
            {
                'payment_method': 'mpesa',
                'payment_phone': '255712345678',
                'payment_reference': 'ADMIN-REG-654321',
                'first_name': 'Force',
                'last_name': 'Reset',
                'phone': '255700000404',
                'gender': 'male',
                'password': 'officepass',
                'confirm_password': 'officepass',
            },
            follow=False,
        )
        self.assertEqual(create_resp.status_code, 302)
        member = Member.objects.get(phone='255700000404')
        user = User.objects.get(id=member.user_id)
        self.assertTrue(user.must_change_password)

        login_client = SafeClient()
        self.assertTrue(login_client.login(username=user.username, password='officepass'))
        session = login_client.session
        session['cooperative_id'] = self.coop.id
        session.save()

        dash = login_client.get(reverse('core:dashboard'), follow=False)
        self.assertEqual(dash.status_code, 302)
        self.assertIn('force-password-change', dash.url)

        change = login_client.post(
            reverse('auth:force_password_change'),
            {'new_password': 'mynewpass99', 'confirm_password': 'mynewpass99'},
            follow=False,
        )
        self.assertEqual(change.status_code, 302)
        user.refresh_from_db()
        self.assertFalse(user.must_change_password)
        self.assertTrue(user.check_password('mynewpass99'))
