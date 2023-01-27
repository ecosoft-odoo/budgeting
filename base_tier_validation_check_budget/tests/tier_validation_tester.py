# Copyright 2020 Ecosoft (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class TierValidationTester(models.Model):
    _name = "tier.validation.tester"
    _description = "Tier Validation Tester"
    _inherit = ["tier.validation"]
    _docline_rel = "test_line"
    _docline_type = "test"

    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("cancel", "Cancel"),
        ],
        default="draft",
    )
    test_field = fields.Float()
    user_id = fields.Many2one(string="Assigned to:", comodel_name="res.users")
    test_bool = fields.Boolean()
    test_line = fields.One2many(
        comodel_name="tier.validation.line.tester",
        inverse_name="test_id",
    )


class TierValidationLineTester(models.Model):
    _name = "tier.validation.line.tester"
    _description = "Tier Validation Tester"

    test_id = fields.Many2one(comodel_name="tier.validation.tester")
