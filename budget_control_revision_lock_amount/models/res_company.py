# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    budget_control_revision_lock_amount = fields.Selection(
        selection=[
            ("none", "No Lock"),
            ("current", "Lock until current month"),
            ("last", "Lock until last month"),
        ],
        string="Budget Control Revision - Lock Amount",
        default="none",
        help="Determines the lock amount period for budget control revisions. \
            Options are: No Lock, Lock until current month, Lock until last month",
    )
