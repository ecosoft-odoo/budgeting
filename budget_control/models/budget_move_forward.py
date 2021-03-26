# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class BudgetMoveForward(models.Model):
    _name = "budget.move.forward"
    _description = "Budget Move Forward"
    _inherit = ["mail.thread"]

    name = fields.Char(
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    assignee_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned To",
        domain=lambda self: [
            (
                "groups_id",
                "in",
                [self.env.ref("budget_control.group_budget_control_user").id],
            )
        ],
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
        copy=False,
    )
    to_budget_id = fields.Many2one(
        comodel_name="mis.budget",
        string="To Budget Period",
        required=True,
        ondelete="restrict",
        readonly=True,
        states={"draft": [("readonly", False)]},
        # TODO: add domain, and default
    )
    date_budget_move = fields.Date(
        related="to_budget_id.date_from",
        string="Move to date",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
        ],
        string="Status",
        readonly=True,
        copy=False,
        index=True,
        default="draft",
        tracking=True,
    )
    forward_line_ids = fields.One2many(
        comodel_name="budget.move.forward.line",
        inverse_name="forward_id",
        string="Forward Lines",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)", "Name must be unique!"),
    ]

    def _get_domain_search(self, model):
        self.ensure_one()
        domain_search = [("amount_commit", ">", 0.0)]
        return domain_search

    def _get_domain_unlink(self, model):
        self.ensure_one()
        domain_search = [
            ("forward_id", "=", self.id),
            ("res_model", "=", model),
        ]
        return domain_search

    def _get_document_number(self, doc):
        return False

    def _prepare_vals_forward(self, docs, model):
        self.ensure_one()
        value_dict = []
        for doc in docs:
            # Filter out budget move that have been carry forward.
            analytic = doc[doc._budget_analytic_field]
            current_move = doc._filter_current_move(analytic)
            current_commit_move = sum(current_move.mapped("debit")) - sum(
                current_move.mapped("credit")
            )
            if not current_commit_move:
                continue
            value_dict.append(
                {
                    "forward_id": self.id,
                    "res_model": model,
                    "res_id": doc.id,
                    "document_id": "{},{}".format(model, doc.id),
                    "document_number": self._get_document_number(doc),
                    "amount_commit": doc.amount_commit,
                    "date_commit": doc.date_commit,
                }
            )
        return value_dict

    def get_budget_move_forward(self):
        """Get budget move forward for each new commit document type."""
        Line = self.env["budget.move.forward.line"]
        specific_model = self._context.get("res_model", False)
        for rec in self:
            models = Line._fields["res_model"].selection
            for model in list(dict(models).keys()):
                if specific_model and specific_model != model:
                    continue
                domain_unlink = rec._get_domain_unlink(model)
                Line.search(domain_unlink).unlink()
                domain_search = rec._get_domain_search(model)
                docs = self.env[model].search(domain_search)
                vals = rec._prepare_vals_forward(docs, model)
                Line.create(vals)

    def action_budget_carry_forward(self):
        """
        Concept carry forward
            1. Reversed budget move each document line
            2. Commit new budget move for carry forward and Update it to next analytic
            3. Updated new budget move to next analytic
        Example
            Analytic A - Budget Period 2020 - From 01/01/2020 To 31/12/2020
            Analytic A - Budget Period 2021 - From 01/01/2021 To 31/12/2021
        Table of Purchase Budget Move
        =====================================================
        Date       | Analytic Account    | Debit | Credit
        =====================================================
        01/03/2020 | [2020] Analytic A   | 100.0 |
        --------------------Carry Forward--------------------
        01/03/2020 | [2020] Analytic A   |       | 100.0
        01/01/2021 | [2021] Analytic A   | 100.0 |
        """
        Line = self.env["budget.move.forward.line"]
        for rec in self:
            models = Line._fields["res_model"].selection
            for model in list(dict(models).keys()):
                doclines = Line.search(
                    [("forward_id", "=", rec.id), ("res_model", "=", model)]
                ).mapped("document_id")
                if not doclines:
                    continue
                for docline in doclines:
                    analytic = docline[docline._budget_analytic_field]
                    next_analytic = analytic.next_year_analytic()
                    docline.commit_budget(reverse=True)
                    budget_move = docline.commit_budget()
                    budget_move.write(
                        {
                            "analytic_account_id": next_analytic.id,
                            "date": rec.date_budget_move,
                        }
                    )
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "draft"})


class BudgetMoveForwardLine(models.Model):
    _name = "budget.move.forward.line"
    _description = "Budget Move Forward Line"

    forward_id = fields.Many2one(
        comodel_name="budget.move.forward",
        index=True,
        readonly=True,
        required=True,
    )
    res_model = fields.Selection(
        selection=[],
        string="Res Model",
        required=True,
    )
    res_id = fields.Integer(
        string="Res ID",
        required=True,
    )
    document_id = fields.Reference(
        selection=[],
        string="Document",
        required=True,
    )
    document_number = fields.Char(string="Document Number")
    date_commit = fields.Date(
        string="Date",
        required=True,
    )
    amount_commit = fields.Float(
        string="Commitment",
        required=True,
    )
