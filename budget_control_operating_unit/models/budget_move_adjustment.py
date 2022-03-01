# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetMoveAdjustment(models.Model):
    _inherit = "budget.move.adjustment"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        default=lambda self: self._default_operating_unit_id(),
        domain="[('user_ids', '=', uid)]",
        help="This operating unit will be defaulted in the move lines.",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    @api.model
    def _default_operating_unit_id(self):
        return self.env["res.users"].operating_unit_default_get()


class BudgetMoveAdjustmentItem(models.Model):
    _inherit = "budget.move.adjustment.item"

    operating_unit_id = fields.Many2one(
        comodel_name="operating.unit",
        domain="[('user_ids', '=', uid)]",
        index=True,
    )

    @api.constrains(
        "adjust_id.operating_unit_id", "operating_unit_id", "adjust_id"
    )
    def _check_line_operating_unit(self):
        for rec in self:
            if (
                rec.adjust_id
                and rec.adjust_id.operating_unit_id
                and rec.operating_unit_id
                and rec.adjust_id.operating_unit_id != rec.operating_unit_id
            ):
                raise UserError(
                    _(
                        "Configuration error. The Operating Unit in "
                        "the Line and in the Adjustment must be the same."
                    )
                )
