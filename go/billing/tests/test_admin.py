""" Test for billing admin. """

from django.contrib.admin.sites import AdminSite
from django.core.urlresolvers import reverse

from go.base.utils import vumi_api_for_user
from go.base.tests.helpers import GoDjangoTestCase, DjangoVumiApiHelper
from go.billing.models import Account, Transaction
from go.billing.admin import AccountAdmin

from .helpers import mk_statement, mk_transaction


class MockRequest(object):
    pass


class TestStatementAdmin(GoDjangoTestCase):
    def setUp(self):
        self.vumi_helper = self.add_helper(DjangoVumiApiHelper())
        self.user_helper = self.vumi_helper.make_django_user(superuser=True)
        self.user_helper2 = self.vumi_helper.make_django_user('user2')
        self.user_helper3 = self.vumi_helper.make_django_user('user3')

        self.vumi_helper.setup_tagpool(u'pool1', ['tag1'])
        self.user_helper.add_tagpool_permission(u'pool1')

        self.account = Account.objects.get(
            user=self.user_helper.get_django_user())

        self.request = MockRequest()

    def test_admin_accessible(self):
        client = self.vumi_helper.get_client()
        client.login()
        response = client.get(
            reverse('admin:app_list', kwargs={'app_label': 'billing'}))
        self.assertContains(response, "Billing administration")
        self.assertContains(response, "Accounts")
        self.assertContains(response, "Message costs")
        self.assertContains(response, "Statements")
        self.assertContains(response, "Tag pools")
        self.assertContains(response, "Transactions")
        self.assertContains(response, "Low credit notifications")
        self.assertContains(response, "Transaction archives")

    def test_link_to_html_view(self):
        statement = mk_statement(self.account)
        client = self.vumi_helper.get_client()
        client.login()
        response = client.get(reverse('admin:billing_statement_changelist'))
        self.assertContains(response, "1 total")
        self.assertContains(
            response,
            '<a href="/billing/statement/%s">' % (statement.id,))

    def test_statement_admin_view(self):
        mk_transaction(self.account)
        statement = mk_statement(self.account)
        client = self.vumi_helper.get_client()
        client.login()
        response = client.get(
            reverse('admin:billing_statement_change', args=[statement.id]))
        self.assertContains(response, "Monthly Statement for")
        self.assertContains(response, "Account")
        # check that line items have been inlined
        self.assertContains(response, "Channel")
        self.assertContains(response, "Channel type")
        self.assertContains(response, "Description")
        self.assertContains(response, "Units")
        self.assertContains(response, "Credits")
        self.assertContains(response, "Unit cost")
        self.assertContains(response, "Cost")

    def test_account_admin_view(self):
        client = self.vumi_helper.get_client()
        client.login()
        response = client.get(
            reverse('admin:billing_account_changelist'))
        self.assertContains(response, 'Select account to change')
        self.assertContains(response, 'Account number')
        self.assertContains(response, 'User')
        self.assertContains(response, 'Description')
        self.assertContains(response, 'Credit balance')
        self.assertContains(response, 'Last topup balance')
        self.assertContains(response, 'Is developer')

    def test_getting_developer_flag(self):
        admin = AccountAdmin(Account, AdminSite())
        self.assertFalse(admin.is_developer(self.account))
        vumi_api = vumi_api_for_user(self.account.user)
        account = vumi_api.get_user_account()
        account.is_developer = True
        account.save()
        self.assertTrue(admin.is_developer(self.account))

    def test_setting_developer_flag(self):
        admin = AccountAdmin(Account, AdminSite())
        admin._set_developer_flag(self.account.user, True)
        self.assertTrue(admin.is_developer(self.account))
        admin._set_developer_flag(self.account.user, False)
        self.assertFalse(admin.is_developer(self.account))

    def test_setting_developer_flag_on_accounts(self):
        admin = AccountAdmin(Account, AdminSite())
        self.assertTrue(Account.objects.count() >= 3)
        queryset = Account.objects.order_by('account_number')[:2]
        admin.set_developer_flag(self.request, queryset)
        developers = Account.objects.order_by('account_number')[:2]
        non_developers = Account.objects.order_by('account_number')[2:]
        for account in developers:
            self.assertTrue(admin.is_developer(account))
        for account in non_developers:
            self.assertFalse(admin.is_developer(account))

    def test_unsetting_developer_flag_on_account(self):
        admin = AccountAdmin(Account, AdminSite())
        self.assertTrue(Account.objects.count() >= 3)
        for account in Account.objects.all():
            admin._set_developer_flag(account.user, True)
        queryset = Account.objects.order_by('account_number')[:2]
        admin.unset_developer_flag(self.request, queryset)
        non_developers = Account.objects.order_by('account_number')[:2]
        developers = Account.objects.order_by('account_number')[2:]
        for account in non_developers:
            self.assertFalse(admin.is_developer(account))
        for account in developers:
            self.assertTrue(admin.is_developer(account))

    def test_transaction_search(self):
        trans1 = mk_transaction(
            self.account,
            transaction_type=Transaction.TRANSACTION_TYPE_MESSAGE)
        trans2 = mk_transaction(
            self.account,
            transaction_type=Transaction.TRANSACTION_TYPE_TOPUP)
        client = self.vumi_helper.get_client()
        client.login()
        response = client.get(
            reverse('admin:billing_transaction_changelist'),
            {'q': 'Top Up'})
        self.assertContains(response, "1 result")
        self.assertContains(
            response, '<a href="/admin/billing/transaction/%d/">' % trans2.pk)
        self.assertNotContains(
            response, '<a href="/admin/billing/transaction/%d/">' % trans1.pk)
