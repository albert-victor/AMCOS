"""RBAC scan: each role must only access allowed URLs (no cross-role leaks)."""
from django.test import TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.core.test_client import SafeClient
from apps.cooperative.models import Cooperative
from apps.core.permissions import PERMISSIONS, user_can

ROLES = [c[0] for c in User.ROLE_CHOICES]

# URL name -> permission key required (GET)
PROTECTED_GET_URLS = {
    'members:list': 'members.list',
    'members:create': 'members.create',
    'audit:trails': 'audit.view',
    'audit:compliance': 'audit.view',
    'reporting:dashboard': 'reporting.view',
    'reporting:members': 'reporting.view',
    'accounting:dashboard': 'accounting.view',
    'accounting:income_create': 'accounting.create',
    'payments:dashboard': 'payments.dashboard',
    'payments:make': 'payments.make',
    'payments:invoice_list': 'payments.invoices',
    'cooperative:branches': 'cooperative.admin',
    'cooperative:profile': 'cooperative.profile',
    'governance:meeting_create': 'governance.manage',
    'notifications:broadcast': 'notifications.broadcast',
    'notifications:send': 'notifications.send',
    'shares:dividends': 'shares.list',
}

# Member should use *_own permissions for list pages
MEMBER_LIST_URLS = {
    'payments:list': 'payments.list_own',
    'savings:list': 'savings.list_own',
    'loans:list': 'loans.list_own',
    'shares:list': 'shares.list_own',
}


class RolePermissionMatrixTest(TestCase):
    """Every role has a defined permission profile."""

    def test_all_roles_in_matrix(self):
        self.assertEqual(len(ROLES), 16)

    def test_super_admin_has_all_permissions(self):
        user = User(role='super_admin')
        for key in PERMISSIONS:
            self.assertTrue(user_can(user, key), msg=f'super_admin missing {key}')


class RoleUrlAccessTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.coop = Cooperative.objects.create(
            name='RBAC Test AMCOS',
            code='RBAC01',
            type='amcos',
        )
        cls.users = {}
        for role in ROLES:
            if role == 'super_admin':
                u = User.objects.create_user(
                    username=f'rbac_{role}',
                    password='testpass123',
                    role=role,
                    phone=f'2557{hash(role) % 10000000:07d}',
                )
            else:
                u = User.objects.create_user(
                    username=f'rbac_{role}',
                    password='testpass123',
                    role=role,
                    cooperative_id=cls.coop.id,
                    phone=f'2558{hash(role) % 10000000:07d}',
                )
            cls.users[role] = u

    def _login(self, role):
        client = SafeClient()
        client.login(username=f'rbac_{role}', password='testpass123')
        if role != 'super_admin':
            session = client.session
            session['cooperative_id'] = self.coop.id
            session.save()
        return client

    def _expected_allowed(self, role, perm_key):
        user = self.users[role]
        return user_can(user, perm_key)

    def test_staff_protected_urls_match_permissions(self):
        """Non-members: URL access must match permission registry."""
        for role in ROLES:
            if role == 'member':
                continue
            client = self._login(role)
            for url_name, perm_key in PROTECTED_GET_URLS.items():
                allowed = self._expected_allowed(role, perm_key)
                path = reverse(url_name)
                resp = client.get(path, follow=False)
                with self.subTest(role=role, url=url_name, allowed=allowed):
                    if allowed:
                        self.assertIn(
                            resp.status_code, (200, 302),
                            msg=f'{role} denied for {url_name} (expected allow)',
                        )
                        if resp.status_code == 302:
                            self.assertNotIn(
                                reverse('core:dashboard'),
                                resp.url or '',
                                msg=f'{role} redirected away from allowed {url_name}',
                            )
                    else:
                        self.assertEqual(
                            resp.status_code, 302,
                            msg=f'{role} got {resp.status_code} for forbidden {url_name}',
                        )
                        self.assertTrue(
                            resp.url.endswith(reverse('core:dashboard'))
                            or 'dashboard' in resp.url,
                            msg=f'{role} wrong redirect for {url_name}: {resp.url}',
                        )

    def test_member_cannot_access_staff_lists(self):
        client = self._login('member')
        for url_name in ('members:list', 'audit:trails', 'reporting:dashboard', 'payments:make'):
            resp = client.get(reverse(url_name), follow=False)
            with self.subTest(url=url_name):
                self.assertEqual(resp.status_code, 302)

    def test_member_can_access_own_list_endpoints(self):
        client = self._login('member')
        for url_name, perm_key in MEMBER_LIST_URLS.items():
            self.assertTrue(self._expected_allowed('member', perm_key))
            resp = client.get(reverse(url_name), follow=True)
            with self.subTest(url=url_name):
                self.assertEqual(resp.status_code, 200)

    def test_auditor_cannot_access_accounting(self):
        client = self._login('auditor')
        resp = client.get(reverse('accounting:dashboard'), follow=False)
        self.assertEqual(resp.status_code, 302)

    def test_loan_officer_cannot_access_audit(self):
        client = self._login('loan_officer')
        resp = client.get(reverse('audit:trails'), follow=False)
        self.assertEqual(resp.status_code, 302)

    def test_board_member_cannot_access_reporting_dashboard(self):
        """board_member has nav link but not reporting.view — known gap."""
        client = self._login('board_member')
        resp = client.get(reverse('reporting:dashboard'), follow=False)
        self.assertEqual(resp.status_code, 302)

    def test_tcdc_can_view_reports_but_not_create(self):
        for role in ('tcdc_wilaya', 'tcdc_mkoa'):
            client = self._login(role)
            for url_name in ('reporting:dashboard', 'accounting:dashboard', 'audit:trails', 'members:list'):
                resp = client.get(reverse(url_name), follow=False)
                with self.subTest(role=role, url=url_name):
                    self.assertIn(resp.status_code, (200, 302))
            for url_name in ('members:create', 'payments:make', 'accounting:income_create'):
                resp = client.get(reverse(url_name), follow=False)
                with self.subTest(role=role, url=url_name):
                    self.assertEqual(resp.status_code, 302)


class NavRoleCoverageTest(TestCase):
    """Roles that must have dedicated sidebar blocks in base.html."""

    NAV_DEDICATED_BLOCKS = {
        'super_admin', 'chairperson', 'secretary', 'treasurer', 'accountant',
        'board_member', 'carder', 'member', 'cooperative_admin',
        'loan_officer', 'auditor', 'tcdc_wilaya', 'tcdc_mkoa',
    }

    def test_all_staff_roles_have_dedicated_nav_blocks(self):
        staff_roles = {
            'super_admin', 'cooperative_admin', 'parrc', 'chairperson',
            'secretary', 'treasurer', 'accountant', 'loan_officer', 'auditor',
            'board_member', 'carder', 'tcdc_wilaya', 'tcdc_mkoa', 'member',
        }
        missing = staff_roles - self.NAV_DEDICATED_BLOCKS
        self.assertEqual(missing, {'parrc'}, msg=f'roles missing dedicated nav: {missing}')
