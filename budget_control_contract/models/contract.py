# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class ContractContract(models.Model):
    _inherit = "contract.contract"

    budget_move_ids = fields.One2many(
        comodel_name="contract.budget.move",
        inverse_name="contract_id",
        string="Contract Budget Moves",
        ondelete="cascade",
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

    # Allow trigger, because contract line is always editable.
    @api.constrains("contract_line_ids")
    def recompute_budget_move(self):
        self.mapped("contract_line_ids").recompute_budget_move()
        # As there is no state changes, check_budget after done the budget moves
        BudgetPeriod = self.env["budget.period"]
        for doc in self:
            currency = doc.journal_id.currency_id or self.env.company.currency_id
            BudgetPeriod.with_context(doc_currency=currency).check_budget(
                doc.contract_line_ids, doc_type="contract"
            )

    def close_budget_move(self):
        self.mapped("contract_line_ids").close_budget_move()

    def write(self, vals):
        """
        - Commit budget when check commit budget
        - Archived ot not check commit budget, document should delete all budget commitment
        """
        res = super().write(vals)
        contract_not_active = self.filtered(lambda x: not x.active)
        if contract_not_active:
            self.mapped("budget_move_ids").unlink()
            return res
        self = self.filtered("active")
        self.recompute_budget_move()
        # Special for contract, as line can always change
        # make sure budget is checked when line changes
        if "contract_line_ids" in vals:
            BudgetPeriod = self.env["budget.period"]
            for doc in self:
                BudgetPeriod.check_budget(doc.contract_line_ids, doc_type="contract")
        return res


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
    invoice_lines = fields.One2many(
        comodel_name="account.move.line",
        inverse_name="contract_line_id",
        copy=False,
    )
    qty_invoiced = fields.Float(
        compute="_compute_qty_invoiced",
        string="Billed Qty",
        digits="Product Unit of Measure",
        store=True,
    )

    @api.depends("invoice_lines.move_id.state", "invoice_lines.quantity", "quantity")
    def _compute_qty_invoiced(self):
        for line in self:
            # compute qty_invoiced
            qty = 0.0
            for inv_line in line.invoice_lines:
                if inv_line.move_id.state not in ["cancel"]:
                    if inv_line.move_id.move_type in [
                        "in_invoice",
                        "out_invoice",
                    ]:
                        qty += inv_line.product_uom_id._compute_quantity(
                            inv_line.quantity, line.uom_id
                        )
                    elif inv_line.move_id.move_type in [
                        "in_refund",
                        "out_refund",
                    ]:
                        qty -= inv_line.product_uom_id._compute_quantity(
                            inv_line.quantity, line.uom_id
                        )
            line.qty_invoiced = qty

    def _compute_account_id(self):
        for rec in self:
            rec.account_id = rec._get_contract_line_account()

    def recompute_budget_move(self):
        for contract_line in self:
            contract_line.budget_move_ids.unlink()
            # skip commit budget, if not check commit budget field
            if not contract_line.contract_id.commit_budget:
                continue
            contract_line.commit_budget()
            contract_line.forward_commit()
            contract_line.invoice_lines.uncommit_contract_budget()

    def _get_contract_line_account(self):
        fpos = self.contract_id.fiscal_position_id
        account = self.product_id.product_tmpl_id.get_product_accounts(fpos)["expense"]
        return account

    def _init_docline_budget_vals(self, budget_vals):
        self.ensure_one()
        quantity = self.quantity
        if "quantity" in budget_vals and budget_vals.get("quantity"):
            quantity = budget_vals.pop("quantity")
        budget_vals["amount_currency"] = self.price_unit * quantity
        # Document specific vals
        budget_vals.update(
            {
                "contract_line_id": self.id,
                "analytic_tag_ids": [(6, 0, self.analytic_tag_ids.ids)],
            }
        )
        return super()._init_docline_budget_vals(budget_vals)

    def _valid_commit_state(self):
        # Contract has no state, watch commit_budget
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
