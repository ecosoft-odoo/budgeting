# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetCommitForward(models.Model):
    _inherit = "budget.commit.forward"

    forward_contract_ids = fields.One2many(
        comodel_name="budget.commit.forward.line",
        inverse_name="forward_id",
        string="Contracts",
        domain=[("res_model", "=", "contract.line")],
    )

    def _get_document_number(self, doc):
        if doc._name == "contract.line":
            return doc.contract_id.name
        return super()._get_document_number(doc)

    def _get_domain_search(self, model):
        """ Filter Contract used analytic account"""
        domain_search = super()._get_domain_search(model)
        if model == "contract.line":
            domain_search.extend(
                [
                    ("analytic_account_id", "!=", False),
                ]
            )
        return domain_search


class BudgetCommitForwardLine(models.Model):
    _inherit = "budget.commit.forward.line"

    res_model = fields.Selection(
        selection_add=[("contract.line", "Contract")],
        ondelete={"contract.line": "cascade"},
    )
    document_id = fields.Reference(
        selection_add=[("contract.line", "Contract")],
        ondelete={"contract.line": "cascade"},
    )
