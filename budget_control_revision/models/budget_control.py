# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models


class BudgetControl(models.Model):
    _name = "budget.control"
    _inherit = ["budget.control", "base.revision"]
    _order = "revision_number desc, budget_id desc, analytic_account_id"

    current_revision_id = fields.Many2one(
        comodel_name="budget.control",
    )
    old_revision_ids = fields.One2many(
        comodel_name="budget.control",
    )
    init_revision = fields.Boolean(
        string="Initial Version", default=True, readonly=True
    )
    revision_number = fields.Integer(readonly=True)
    enable_revision_number = fields.Boolean(
        compute="_compute_group_revision_number"
    )

    def _get_permission_edit_revision(self):
        # Default by Budget Manager
        return self.env.user.has_group(
            "budget_control.group_budget_control_manager"
        )

    @api.depends("revision_number")
    def _compute_group_revision_number(self):
        editable = False
        group_enable_revision = self.env.user.has_group(
            "budget_control_revision.group_enable_revision"
        )
        permission_editable = self._get_permission_edit_revision()
        if group_enable_revision and permission_editable:
            editable = True
        self.update({"enable_revision_number": editable})
        return True

    def _filter_by_budget_control(self, val):
        res = super()._filter_by_budget_control(val)
        if val["amount_type"] != "1_budget":
            return res
        revision_number = (
            0 if not val["revision_number"] else int(val["revision_number"])
        )
        return res and revision_number == self.revision_number
