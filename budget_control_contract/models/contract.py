# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ContractContract(models.Model):
    _inherit = "contract.contract"

    budget_move_ids = fields.One2many(
        comodel_name="contract.budget.move",
        inverse_name="contract_id",
        string="Contract Budget Moves",
    )
    commit_budget = fields.Boolean(
        string="Commit Budget",
        help="If checked, this contract can commit budget.\n"
        "To commit budget, open tab Budgeting and click Recompute.\n"
        "If related invoice is posted, commit amount is returned.\n"
        "Note:\n"
        "- Budget will commit only once, regardless of number of recurring invoices.\n"
        "- Enable commit budget only when dealing with non-recurring invoices.",
    )

    def recompute_budget_move(self):
        self.mapped("contract_line_ids").recompute_budget_move()
        # Do check after done the budget moves
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            currency = (
                doc.journal_id.currency_id or self.env.company.currency_id
            )
            BudgetPeriod.with_context(doc_currency=currency).check_budget(
                doc.contract_line_ids, doc_type="contract"
            )

    def close_budget_move(self):
        self.mapped("contract_line_ids").close_budget_move()


class ContractLine(models.Model):
    _name = "contract.line"
    _inherit = ["contract.line", "budget.docline.mixin"]
    _budget_analytic_field = "analytic_account_id"
    _budget_date_commit_fields = ["contract_id.write_date"]
    _budget_move_model = "contract.budget.move"
    _doc_rel = "contract_id"

    budget_move_ids = fields.One2many(
        comodel_name="contract.budget.move",
        inverse_name="contract_line_id",
        string="Contract Budget Moves",
    )
    account_id = fields.Many2one(
        comodel_name="account.account",
        compute="_compute_account_id",
    )

    def _compute_account_id(self):
        for rec in self:
            rec.account_id = rec._get_contract_line_account()

    def recompute_budget_move(self):
        MoveLine = self.env["account.move.line"]
        for contract_line in self:
            contract_line.budget_move_ids.unlink()
            # Commit on contract
            contract_line.commit_budget()
            # Uncommitted on invoice confirm
            move_lines = MoveLine.search(
                [("contract_line_id", "=", contract_line.id)]
            )
            move_lines.uncommit_contract_budget()

    def _get_contract_line_account(self):
        fpos = self.contract_id.fiscal_position_id
        account = self.product_id.product_tmpl_id.get_product_accounts(fpos)[
            "expense"
        ]
        return account

    def _init_docline_budget_vals(self, budget_vals):
        self.ensure_one()
        budget_vals["amount_currency"] = self.price_unit * self.quantity
        # Document specific vals
        budget_vals.update(
            {
                "contract_line_id": self.id,
                "analytic_tag_ids": [(6, 0, self.analytic_tag_ids.ids)],
            }
        )
        return super()._init_docline_budget_vals(budget_vals)

    def _valid_commit_state(self):
        if (
            not self.contract_id.commit_budget
            or self.contract_id.journal_id.type != "purchase"
        ):
            return False
        return True

    def prepare_commit(self):
        self.ensure_one()
        if self._name == "contract.line":
            return
        return super().prepare_commit()
