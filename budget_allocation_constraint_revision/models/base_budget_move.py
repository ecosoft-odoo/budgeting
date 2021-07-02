# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class BaseBudgetMove(models.AbstractModel):
    _inherit = "base.budget.move"

    def _where_query_source_fund(self, docline):
        """ Find max revision number from budget_control """
        where_query = super()._where_query_source_fund(docline)
        bc_max_revision = self.env["budget.control"].search(
            [], order="revision_number", limit=1
        )
        # commitment is not revision
        where_revision = (
            "(revision_number = '{}' or revision_number is null)".format(
                bc_max_revision.revision_number
            )
        )
        return " and ".join([where_query, where_revision])
