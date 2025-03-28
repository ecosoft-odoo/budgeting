# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetCommitForward(models.Model):
    _name = "budget.commit.forward"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Budget Commit Forward"

    name = fields.Char(
        required=True,
    )
    to_budget_period_id = fields.Many2one(
        comodel_name="budget.period",
        required=True,
        ondelete="restrict",
    )
    to_date_commit = fields.Date(
        related="to_budget_period_id.bm_date_from",
        string="Move commit to date",
    )
    filter_lines = fields.Many2many(
        comodel_name="budget.commit.forward.line",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("review", "Review"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        readonly=True,
        copy=False,
        index=True,
        default="draft",
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        default=lambda self: self.env.user.company_id.currency_id,
    )
    forward_line_ids = fields.One2many(
        comodel_name="budget.commit.forward.line",
        inverse_name="forward_id",
        string="Forward Lines",
    )
    missing_analytic = fields.Boolean(
        compute="_compute_missing_analytic",
        help="Not all forward lines has been assigned with carry forward analytic",
    )
    _sql_constraints = [
        ("name_uniq", "UNIQUE(name)", "Name must be unique!"),
    ]

    def _compute_missing_analytic(self):
        for rec in self:
            rec.missing_analytic = any(
                rec.forward_line_ids.filtered_domain(
                    [("to_analytic_account_id", "=", False)]
                )
            )

    def _get_base_from_extension(self, res_model):
        """For module extension"""
        return ""

    def _get_base_domain_extension(self, res_model):
        """For module extension"""
        return ""

    def _get_name_model(self, res_model, need_replace=False):
        return res_model.replace(".", "_") if need_replace else res_model

    def _get_commit_docline(self, res_model):
        """Base domain for query"""
        self.ensure_one()
        model_name_db = self._get_name_model(res_model, need_replace=True)
        query = """
            SELECT a.id
            FROM %s a
            %s
            , jsonb_each_text(a.amount_commit) AS kv(key, value)
            WHERE value::numeric != 0 AND a.date_commit < '%s'
                AND (a.fwd_date_commit != '%s' OR a.fwd_date_commit is null) %s;
        """
        query_string = query % (
            model_name_db,
            self._get_base_from_extension(res_model),
            self.to_date_commit,
            self.to_date_commit,
            self._get_base_domain_extension(res_model),
        )
        # pylint: disable=sql-injection
        self.env.cr.execute(query_string)
        # Get all domain ids, remove duplicate from many analytics in 1 line
        domain_ids = list({row["id"] for row in self.env.cr.dictfetchall()})
        model_name = self._get_name_model(res_model)
        obj_ids = self.env[model_name].browse(domain_ids)
        return obj_ids

    def _get_document_number(self, doc):
        """For module extension"""
        return False

    def _get_budget_docline_model(self):
        """_compute_missing_analytic"""
        self.ensure_one()
        return []

    def _prepare_vals_forward(self, docs, res_model):
        self.ensure_one()
        value_dict = []
        AnalyticAccount = self.env["account.analytic.account"]
        for doc in docs:
            analytic_account = (
                doc.fwd_analytic_distribution or doc[doc._budget_analytic_field]
            )
            for analytic_id, aa_percent in analytic_account.items():
                method_type = False
                analytic = AnalyticAccount.browse(int(analytic_id))
                if analytic.bm_date_to and analytic.bm_date_to < self.to_date_commit:
                    method_type = "new"
                value_dict.append(
                    {
                        "forward_id": self.id,
                        "analytic_account_id": analytic_id,
                        "analytic_percent": aa_percent / 100,
                        "method_type": method_type,
                        "res_model": res_model,
                        "res_id": doc.id,
                        "document_id": f"{doc._name},{doc.id}",
                        "document_number": self._get_document_number(doc),
                        "amount_commit": doc.amount_commit[str(analytic_id)],
                        "date_commit": doc.fwd_date_commit or doc.date_commit,
                    }
                )
        return value_dict

    def action_review_budget_commit(self):
        for rec in self:
            for res_model in rec._get_budget_docline_model():
                rec.get_budget_commit_forward(res_model)
        self.write({"state": "review"})

    def action_filter_lines(self):
        for rec in self:
            rec.forward_line_ids = rec.filter_lines

    def action_reset_filter_lines(self):
        """Reset lines and review again"""
        self.forward_line_ids.unlink()
        for rec in self:
            rec.action_review_budget_commit()

    def get_budget_commit_forward(self, res_model):
        """Get budget commitment forward for each new commit document type."""
        self = self.sudo()
        Line = self.env["budget.commit.forward.line"]
        for rec in self:
            docs = rec._get_commit_docline(res_model)
            vals = rec._prepare_vals_forward(docs, res_model)
            Line.create(vals)

    def create_missing_analytic(self):
        forward_lines = self.mapped("forward_line_ids").filtered_domain(
            [("to_analytic_account_id", "=", False)]
        )
        for line in forward_lines:
            line.to_analytic_account_id = line.analytic_account_id.next_year_analytic()

    def preview_budget_commit_forward_info(self):
        self.ensure_one()
        if self.missing_analytic:
            raise UserError(
                self.env._(
                    "Some carry forward analytic accounts are missing.\n"
                    "Click 'Create Missing Analytics' button to create for "
                    "next budget period."
                )
            )
        wizard = self.env.ref("budget_control.view_budget_commit_forward_info_form")
        domain = [
            ("forward_id", "=", self.id),
            ("forward_id.state", "in", ["review", "done"]),
        ]
        forward_vals = self._get_forward_initial_commit(domain)
        return {
            "name": self.env._("Preview Budget Commitment"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "budget.commit.forward.info",
            "views": [(wizard.id, "form")],
            "view_id": wizard.id,
            "target": "new",
            "context": {
                "default_forward_id": self.id,
                "default_forward_info_line_ids": forward_vals,
            },
        }

    def _get_forward_initial_commit(self, domain):
        """Get analytic of all analytic accounts for this budget carry forward
        + all the "done" budget carry forward"""
        self.ensure_one()
        forwards = self.env["budget.commit.forward.line"].read_group(
            domain,
            ["to_analytic_account_id", "amount_commit"],
            ["to_analytic_account_id"],
            orderby="to_analytic_account_id",
        )
        res = [
            {
                "analytic_account_id": f["to_analytic_account_id"][0],
                "initial_commit": f["amount_commit"],
            }
            for f in forwards
        ]
        return res

    def _do_forward_commit(self, reverse=False):
        """Create carry forward budget move to all related documents"""
        self = self.sudo()
        _analytic_field = "analytic_account_id" if reverse else "to_analytic_account_id"
        for rec in self:
            group_document = {}

            # Group by document
            for line in rec.forward_line_ids:
                if line.document_id in group_document:
                    group_document[line.document_id].append(line)
                else:
                    group_document[line.document_id] = [line]
            for doc, fwd_lines in group_document.items():
                # Convert to json
                fwd_analytic_distribution = {
                    str(line[_analytic_field].id): line.analytic_percent * 100
                    for line in fwd_lines
                }
                doc.write(
                    {
                        "fwd_analytic_distribution": fwd_analytic_distribution,
                        "fwd_date_commit": fwd_lines[0].date_commit
                        if reverse
                        else rec.to_date_commit,
                    }
                )

            # For case extend, update end date of analytic account.
            if not reverse:
                max_date_to = rec.to_budget_period_id.bm_date_to
                for line in rec.forward_line_ids:
                    if line.method_type == "extend" and line.to_analytic_account_id:
                        current_date_to = line.to_analytic_account_id.bm_date_to
                        line.to_analytic_account_id.bm_date_to = (
                            max(current_date_to, max_date_to)
                            if current_date_to
                            else max_date_to
                        )

    def _do_update_initial_commit(self, reverse=False):
        """Update all Analytic Account's initial commit value
        related to budget period"""
        self.ensure_one()
        # Reset initial when cancel document only
        AnalyticAccount = self.env["account.analytic.account"]
        domain = [("forward_id", "=", self.id)]

        if reverse:
            forward_vals = self._get_forward_initial_commit(domain)
            analytics = AnalyticAccount.browse(
                val["analytic_account_id"] for val in forward_vals
            )
            for analytic, val in zip(analytics, forward_vals, strict=False):
                analytic.initial_commit -= val["initial_commit"]
            return

        # Check if there are existing "done" forward commits in the same period
        forward_exists = (
            self.env["budget.commit.forward"].search_count(
                [
                    ("to_budget_period_id", "=", self.to_budget_period_id.id),
                    ("state", "=", "done"),
                    ("id", "!=", self.id),
                ]
            )
            > 0
        )

        domain.append(("forward_id.state", "in", ["review", "done"]))
        forward_vals = self._get_forward_initial_commit(domain)
        analytics = AnalyticAccount.browse(
            val["analytic_account_id"] for val in forward_vals
        )

        for analytic, val in zip(analytics, forward_vals, strict=False):
            # Check first forward commit in the year, it should overwrite initial commit
            if not forward_exists:
                analytic.initial_commit = val["initial_commit"]
            else:
                analytic.initial_commit += val["initial_commit"]

    def _recompute_budget_move(self):
        for rec in self:
            # Recompute budget on document number
            for document in list(set(rec.forward_line_ids.mapped("document_number"))):
                document.recompute_budget_move()

    def action_budget_commit_forward(self):
        self._do_forward_commit()
        self.write({"state": "done"})
        self._do_update_initial_commit()
        self._recompute_budget_move()

    def action_cancel(self):
        """Do not allow cancel document is past period."""
        forwards = self.env["budget.commit.forward"].search([("state", "=", "done")])
        if forwards:
            max_date_commit = max(forwards.mapped("to_date_commit"))
            # Not allow cancel document is past period.
            if max_date_commit and any(
                rec.to_date_commit < max_date_commit for rec in self
            ):
                raise UserError(
                    _("Unable to cancel this document as it belongs to a past period.")
                )
        self.filtered(lambda fwd: fwd.state == "done")._do_forward_commit(reverse=True)
        self.write({"state": "cancel"})
        self._do_update_initial_commit(reverse=True)
        self._recompute_budget_move()

    def action_draft(self):
        self.filtered(lambda fwd: fwd.state == "done")._do_forward_commit(reverse=True)
        self.mapped("forward_line_ids").unlink()
        self.write({"state": "draft"})
        self._do_update_initial_commit(reverse=True)
        self._recompute_budget_move()


class BudgetCommitForwardLine(models.Model):
    _name = "budget.commit.forward.line"
    _description = "Budget Commit Forward Line"
    _rec_names_search = ["document_number", "analytic_account_id"]

    forward_id = fields.Many2one(
        comodel_name="budget.commit.forward",
        string="Forward Commit",
        index=True,
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        index=True,
        required=True,
        readonly=True,
    )
    analytic_percent = fields.Float(
        readonly=True,
    )
    method_type = fields.Selection(
        selection=[
            ("new", "New"),
            ("extend", "Extend"),
        ],
        string="Method",
        help="New: if the analytic has ended, 'To Analytic Account' is required\n"
        "Extended: if the analytic has ended, "
        "but want to extend to next period date end",
    )
    to_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Forward to Analytic",
        compute="_compute_to_analytic_account_id",
        store=True,
    )
    bm_date_to = fields.Date(
        compute="_compute_bm_date_to",
    )
    res_model = fields.Selection(
        selection=[],
        required=True,
        readonly=True,
    )
    res_id = fields.Integer(
        string="Res ID",
        required=True,
        readonly=True,
    )
    document_id = fields.Reference(
        selection=[],
        string="Resource",
        required=True,
        readonly=True,
    )
    document_number = fields.Reference(
        selection=[],
        string="Document",
        required=True,
        readonly=True,
    )
    date_commit = fields.Date(
        string="Date",
        required=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="forward_id.currency_id",
        readonly=True,
    )
    amount_commit = fields.Monetary(
        string="Commitment",
        required=True,
        readonly=True,
    )

    @api.depends("analytic_account_id")
    def _compute_bm_date_to(self):
        for rec in self:
            rec.bm_date_to = rec.analytic_account_id.bm_date_to

    @api.depends("method_type")
    def _compute_to_analytic_account_id(self):
        for rec in self:
            # Case analytic has no end date, always use same analytic
            if not rec.analytic_account_id.bm_date_to:
                rec.to_analytic_account_id = rec.analytic_account_id
                rec.method_type = False
                continue
            # Case analytic has extended end date that cover new commit date,
            # use same analytic
            if (
                rec.analytic_account_id.bm_date_to
                and rec.analytic_account_id.bm_date_to >= rec.forward_id.to_date_commit
            ):
                rec.to_analytic_account_id = rec.analytic_account_id
                rec.method_type = "extend"
                continue
            # Case want to extend analytic to end of next budget period
            if rec.method_type == "extend":
                rec.to_analytic_account_id = rec.analytic_account_id
                continue
            # Case want to use next analytic, if exists
            if rec.method_type == "new":
                rec.to_analytic_account_id = rec.analytic_account_id.next_year_analytic(
                    auto_create=False
                )

    @api.depends("document_number", "analytic_account_id")
    def _compute_display_name(self):
        res = super()._compute_display_name()
        for fwd_line in self:
            doc_name = fwd_line.document_number.display_name
            analytic_name = fwd_line.analytic_account_id.name
            fwd_line.display_name = f"{doc_name} - {analytic_name}"
        return res
