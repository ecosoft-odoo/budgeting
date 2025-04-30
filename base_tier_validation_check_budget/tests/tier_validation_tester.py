# Copyright 2025 Ecosoft (http://ecosoft.co.th)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models


class TierValidationTester(models.Model):
    _inherit = "tier.validation.tester"
    _docline_rel = "user_id"  # Test only
    _docline_type = "account"
