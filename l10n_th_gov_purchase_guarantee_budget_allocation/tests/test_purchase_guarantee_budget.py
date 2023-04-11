# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo.addons.l10n_th_gov_purchase_guarantee.tests.test_purchase_guarantee import (
    TestPurchaseGuarantee,
)


class TestPurchaseGuaranteeBudget(TestPurchaseGuarantee):
    def setUp(self):
        super().setUp()
