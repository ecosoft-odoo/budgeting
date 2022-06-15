# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    def _get_where_commitment(self, docline):
        """Find max revision number from budget_control"""
        where_query = super()._get_where_commitment(docline)
        bc_max_revision = self.env["budget.control"].search(
            [("active", "=", True)], order="revision_number desc", limit=1
        )
        # commitment is not revision
        where_revision = "(revision_number = '{}' or revision_number is null)".format(
            bc_max_revision.revision_number
        )
        return " and ".join([where_query, where_revision])
