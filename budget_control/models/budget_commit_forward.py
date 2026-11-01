# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import SQL, float_round, format_date

from .analytic_plan import BUDGET_COLUMN, budget_row_key


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
        domain=[("budget_scope", "=", "fiscal")],
    )
    to_date_commit = fields.Date(
        related="to_budget_period_id.bm_date_from",
        string="Move commit to date",
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
    forward_line_count = fields.Integer(
        string="Lines", compute="_compute_forward_line_count"
    )
    missing_analytic = fields.Boolean(
        compute="_compute_missing_analytic",
        help="Not all forward lines has been assigned with carry forward analytic",
    )
    company_ids = fields.Many2many(
        comodel_name="res.company",
        relation="budget_commit_forward_company_rel",
        column1="forward_id",
        column2="company_id",
        string="Companies",
        help="Restrict to specific companies. Empty = all companies.",
    )
    _name_uniq = models.Constraint(
        "UNIQUE(name)",
        "Name must be unique!",
    )

    @api.depends("forward_line_ids")
    def _compute_forward_line_count(self):
        counts = dict(
            self.env["budget.commit.forward.line"]._read_group(
                [("forward_id", "in", self.ids)], ["forward_id"], ["__count"]
            )
        )
        for rec in self:
            rec.forward_line_count = counts.get(rec, 0)

    def action_view_forward_lines(self):
        """The lines in a list to search, select and remove in bulk."""
        self.ensure_one()
        if self.state == "review":
            # Lines reviewed before the document name was kept
            for line in self.forward_line_ids.filtered(
                lambda line: not line.document_name
            ):
                line.document_name = line.document_number.display_name
        return {
            "name": self.env._("Lines of %s", self.display_name),
            "type": "ir.actions.act_window",
            "res_model": "budget.commit.forward.line",
            "view_mode": "list,form",
            "domain": [("forward_id", "=", self.id)],
            "context": {"create": False, "edit": self.state == "review"},
        }

    @api.depends("forward_line_ids.to_analytic_account_id")
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
        """Base domain for query.

        The extension hooks return SQL code, so a literal ``%`` must be
        written ``%%`` there.
        """
        self.ensure_one()
        if res_model not in self._get_budget_docline_model():
            raise UserError(
                self.env._("%s does not support commitment forward.", res_model)
            )
        model_name_db = self._get_name_model(res_model, need_replace=True)
        # The query reads the commitments of the document lines from the table
        self.env.flush_all()
        self.env.cr.execute(
            SQL(
                """
                SELECT a.id
                FROM %(table)s a
                %(from_extension)s
                , jsonb_each_text(a.amount_commit) AS kv(key, value)
                WHERE value::numeric != 0 AND a.date_commit < %(date_commit)s
                    AND (a.fwd_date_commit != %(date_commit)s
                        OR a.fwd_date_commit is null)
                    %(domain_extension)s
                """,
                table=SQL.identifier(model_name_db),
                from_extension=SQL(self._get_base_from_extension(res_model)),
                date_commit=self.to_date_commit,
                domain_extension=SQL(self._get_base_domain_extension(res_model)),
            )
        )
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
        """One line for each analytic row of the documents that charges a
        fiscal budget analytic, with the other accounts of the row in plan
        columns."""
        self.ensure_one()
        value_dict = []
        AnalyticAccount = self.env["account.analytic.account"]
        AnalyticPlan = self.env["account.analytic.plan"]
        for doc in docs:
            rows = doc._get_budget_analytic_rows(
                doc.fwd_analytic_distribution or doc[doc._budget_analytic_field]
            )
            row_dates = doc._get_budget_row_dates()
            for analytic_ids, ids, percent in rows:
                if not analytic_ids:
                    continue
                analytic = AnalyticAccount.browse(next(iter(analytic_ids)))
                # Lifetime analytics keep their commitments for their duration
                if analytic.budget_control_scope == "lifetime":
                    continue
                dimensions = AnalyticAccount.browse(ids - analytic_ids)
                value_dict.append(
                    {
                        "forward_id": self.id,
                        "analytic_account_id": analytic.id,
                        "analytic_percent": percent / 100,
                        "res_model": res_model,
                        "res_id": doc.id,
                        "document_id": f"{doc._name},{doc.id}",
                        "document_number": self._get_document_number(doc),
                        "amount_commit": (doc.amount_commit or {}).get(
                            budget_row_key(ids), 0.0
                        ),
                        "date_commit": row_dates.get(
                            budget_row_key(ids), doc.date_commit
                        ),
                        **AnalyticPlan._get_budget_column_vals(
                            AnalyticAccount.browse(ids), "budget.commit.forward.line"
                        ),
                        "to_dimension_ids": [Command.set(dimensions.ids)],
                    }
                )
        return value_dict

    def action_review_budget_commit(self):
        for rec in self:
            for res_model in rec._get_budget_docline_model():
                rec._get_budget_commit_forward(res_model)
        self.write({"state": "review"})
        if len(self) == 1 and not self.forward_line_ids:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "message": self.env._(
                        "No commitment dated before %s to forward.",
                        format_date(self.env, self.to_date_commit),
                    ),
                    "next": {"type": "ir.actions.act_window_close"},
                },
            }
        return True

    def _get_budget_commit_forward(self, res_model):
        """Get budget commitment forward for each new commit document type."""
        self.check_access("write")
        forwards = self.sudo()
        Line = forwards.env["budget.commit.forward.line"]
        for rec in forwards:
            docs = rec._get_commit_docline(res_model)
            vals = rec._prepare_vals_forward(docs, res_model)
            Line.create(vals)

    def action_continue_analytics(self):
        """Continue the analytics of the lines without forward analytic in
        the period of the forward."""
        self.ensure_one()
        lines = self.forward_line_ids.filtered_domain(
            [("to_analytic_account_id", "=", False)]
        )
        return self.env["budget.analytic.continue"]._get_continue_action(
            self.to_budget_period_id, lines.analytic_account_id
        )

    def _check_forward_targets(self):
        """The lines carry their commitments to accounts their documents can
        use from the forward date: checked before the forward changes
        anything."""
        limit = 10
        for forward in self.sudo():
            if forward.missing_analytic:
                raise UserError(
                    self.env._(
                        "Some lines have no forward analytic: click Continue "
                        "Analytics, or choose them."
                    )
                )
            lines = forward.forward_line_ids
            lines._check_to_dimensions()
            messages = [
                message for line in lines if (message := line._get_target_error())
            ]
            if len(messages) > limit:
                messages[limit:] = [
                    self.env._("And %s more lines.", len(messages) - limit)
                ]
            if messages:
                raise UserError("\n".join(messages))

    def preview_budget_commit_forward_info(self):
        self.ensure_one()
        self._check_forward_targets()
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
                "default_forward_info_line_ids": [
                    Command.create(vals) for vals in forward_vals
                ],
            },
        }

    def _get_forward_initial_commit(self, domain):
        """Get analytic of all analytic accounts for this budget carry forward
        + all the "done" budget carry forward"""
        self.ensure_one()
        forwards = self.env["budget.commit.forward.line"]._read_group(
            domain,
            ["to_analytic_account_id"],
            ["amount_commit:sum"],
            order="to_analytic_account_id",
        )
        res = [
            {
                "analytic_account_id": analytic.id,
                "initial_commit": amount_commit,
            }
            for analytic, amount_commit in forwards
        ]
        return res

    def _do_forward_commit(self, reverse=False):
        """Create carry forward budget move to all related documents"""
        forwards = self.sudo()
        for rec in forwards:
            group_document = {}

            # Group by document
            for line in rec.forward_line_ids:
                if line.document_id in group_document:
                    group_document[line.document_id].append(line)
                else:
                    group_document[line.document_id] = [line]
            for doc, fwd_lines in group_document.items():
                # The forward lines move their rows to their target rows, or
                # back when reversing: the other rows of the document stay
                fwd_analytic_distribution = defaultdict(float)
                for key, percent in (
                    doc.fwd_analytic_distribution
                    or doc[doc._budget_analytic_field]
                    or {}
                ).items():
                    row = budget_row_key(int(aid) for aid in str(key).split(","))
                    fwd_analytic_distribution[row] += percent
                for line in fwd_lines:
                    source, target = (
                        line._get_budget_row_key(),
                        line._get_target_row_key(),
                    )
                    if reverse:
                        source, target = target, source
                    percent = line.analytic_percent * 100
                    fwd_analytic_distribution[source] -= percent
                    fwd_analytic_distribution[target] += percent
                precision = self.env["decimal.precision"].precision_get(
                    "Percentage Analytic"
                )
                doc.write(
                    {
                        "fwd_analytic_distribution": {
                            key: percent
                            for key, percent in fwd_analytic_distribution.items()
                            if float_round(percent, precision_digits=precision)
                        },
                        "fwd_date_commit": fwd_lines[0].date_commit
                        if reverse
                        else rec.to_date_commit,
                    }
                )

    def _get_forward_documents(self):
        """Documents of the forward lines, whose commitments the forward
        changes."""
        return list(set(self.forward_line_ids.mapped("document_number")))

    def _recompute_budget_move(self, documents=None):
        """Recompute the commitments of the forward documents, or of
        ``documents`` once the lines are gone."""
        if documents is None:
            documents = self._get_forward_documents()
        for document in documents:
            document.recompute_budget_move()

    def _check_forward_reversible(self):
        """A done forward is reversed only while its documents have nothing
        on the forward date or after it but the carried commitments, e.g. no
        bill and no later forward."""
        ForwardLine = self.env["budget.commit.forward.line"].sudo()
        for forward in self:
            for line in forward.sudo().forward_line_ids:
                docline = line.document_id
                consumed = docline[docline._budget_field()].filtered(
                    lambda move, forward=forward: (
                        move.date >= forward.to_date_commit and not move.fwd_commit
                    )
                )
                forwarded = ForwardLine.search_count(
                    [
                        ("res_model", "=", line.res_model),
                        ("res_id", "=", line.res_id),
                        ("forward_id.state", "=", "done"),
                        ("forward_id.to_date_commit", ">", forward.to_date_commit),
                    ],
                    limit=1,
                )
                if consumed or forwarded:
                    raise UserError(
                        self.env._(
                            "Cannot reverse %(forward)s: %(document)s has commitments "
                            "or actuals from %(date)s, or is forwarded again.",
                            forward=forward.display_name,
                            document=line.document_number.display_name,
                            date=format_date(self.env, forward.to_date_commit),
                        )
                    )

    def _reverse_forward_commit(self):
        """Undo what completing these forwards did, while their lines exist."""
        done = self.filtered(lambda fwd: fwd.state == "done")
        done._check_forward_reversible()
        done._do_forward_commit(reverse=True)
        return done

    def action_budget_commit_forward(self):
        self._check_forward_targets()
        self._do_forward_commit()
        self.write({"state": "done"})
        self._recompute_budget_move()

    def action_cancel(self):
        """Do not allow cancel document is past period."""
        cancel_domain = [("state", "=", "done")]
        company_ids = self.mapped("company_ids").ids
        if company_ids:
            cancel_domain += [("company_ids", "in", company_ids)]
        forwards = self.env["budget.commit.forward"].search(cancel_domain)
        if forwards:
            max_date_commit = max(forwards.mapped("to_date_commit"))
            # Not allow cancel document is past period.
            if max_date_commit and any(
                rec.to_date_commit < max_date_commit for rec in self
            ):
                raise UserError(
                    self.env._(
                        "Unable to cancel this document as it belongs to a past period."
                    )
                )
        done = self._reverse_forward_commit()
        self.write({"state": "cancel"})
        done._recompute_budget_move()

    def action_draft(self):
        done = self._reverse_forward_commit()
        documents = done._get_forward_documents()
        self.write({"state": "draft"})
        self.mapped("forward_line_ids").unlink()
        self._recompute_budget_move(documents)


class BudgetCommitForwardLine(models.Model):
    _name = "budget.commit.forward.line"
    _description = "Budget Commit Forward Line"
    # Lists show the accounts of the row as Dimensions
    _budget_plan_columns_optional = "hide"
    _rec_names_search = ("document_number", "analytic_account_id")

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
    dimension_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        string="Dimensions",
        compute="_compute_dimension_ids",
        help="Accounts of plans without Control Budget of the row, e.g. its fund.",
    )
    to_analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account",
        string="Forward Analytic",
        compute="_compute_to_analytic_account_id",
        store=True,
        readonly=False,
        domain="[('control_budget', '=', True), "
        "('budget_control_scope', '=', 'fiscal')]",
        help="Analytic the commitment is carried forward to: where the analytic "
        "of the line continues in the period by default, see Continues As.",
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
    document_name = fields.Char(
        readonly=True,
        help="Name of the document, to search and group the lines by.",
    )
    forward_changed = fields.Boolean(
        compute="_compute_forward_changed",
        help="The line is carried elsewhere than by default: to another analytic "
        "than where its analytic continues, or to other dimensions.",
    )
    to_dimension_ids = fields.Many2many(
        comodel_name="account.analytic.account",
        relation="budget_commit_forward_line_dimension_rel",
        column1="line_id",
        column2="analytic_id",
        string="Forward Dimensions",
        domain=[("root_plan_id.control_budget", "=", False)],
        help="Accounts of plans without Control Budget, e.g. a fund, the "
        "commitment is carried forward to: those of its row by default.",
    )

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        self.env["account.analytic.plan"]._patch_budget_plan_view(
            arch, view_type, self._name
        )
        return arch, view

    @api.model
    def _get_commit_forward_in_map(self, period_ids, analytic_ids):
        """Commitments the done forwards carried to the analytics,
        ``{(period id, analytic id): amount}``."""
        result = defaultdict(float)
        groups = self.sudo()._read_group(
            [
                ("forward_id.state", "=", "done"),
                ("forward_id.to_budget_period_id", "in", period_ids),
                ("to_analytic_account_id", "in", analytic_ids),
            ],
            ["forward_id", "to_analytic_account_id"],
            ["amount_commit:sum"],
        )
        for forward, analytic, amount in groups:
            result[forward.to_budget_period_id.id, analytic.id] += amount
        return result

    @api.model_create_multi
    def create(self, vals_list):
        # Set once: the document models may load after this module
        for vals in vals_list:
            if isinstance(vals.get("document_number"), str) and not vals.get(
                "document_name"
            ):
                res_model, res_id = vals["document_number"].split(",")
                vals["document_name"] = (
                    self.env[res_model].browse(int(res_id)).display_name
                )
        return super().create(vals_list)

    def _check_forward_open(self):
        """Lines of completed or cancelled forwards are kept as they are:
        reversing a forward reads them."""
        if self.filtered(lambda line: line.forward_id.state in ("done", "cancel")):
            raise UserError(
                self.env._(
                    "Lines of a done or cancelled commitment forward cannot change."
                )
            )

    def write(self, vals):
        self._check_forward_open()
        return super().write(vals)

    def unlink(self):
        self._check_forward_open()
        return super().unlink()

    def action_keep_only_selected(self):
        """Keep these lines in their forwards, remove the others."""
        # A selection of all the search results stops at the ids limit of the
        # web client: the lines past it would be removed
        limit = (
            self.env["ir.config_parameter"].sudo().get_int("web.active_ids_limit")
            or 20000
        )
        if len(self) >= limit:
            raise UserError(
                self.env._(
                    "Select less than %s lines to keep, e.g. by searching them.",
                    limit,
                )
            )
        others = self.forward_id.forward_line_ids - self
        others.unlink()
        return {"type": "ir.actions.client", "tag": "soft_reload"}

    @api.constrains("to_dimension_ids")
    def _check_to_dimensions(self):
        for line in self.sudo():
            dimensions = line.to_dimension_ids
            docline = line.document_id
            company = docline[docline._doc_rel].company_id
            if (
                len(dimensions.root_plan_id) < len(dimensions)
                or dimensions.root_plan_id.filtered("control_budget")
                or dimensions.filtered(
                    lambda account, company=company: (
                        account.company_id
                        and company
                        and account.company_id not in company.parent_ids
                    )
                )
            ):
                raise ValidationError(
                    self.env._(
                        "The forward dimensions of %(line)s take one account of each "
                        "plan without Control Budget, of the company of the "
                        "document.",
                        line=line.display_name,
                    )
                )

    def _get_target_error(self):
        """Why the forward cannot carry this line to its forward analytic,
        if it cannot."""
        self.ensure_one()
        analytic = self.to_analytic_account_id
        period = self.forward_id.to_budget_period_id
        docline = self.document_id
        company = docline[docline._doc_rel].company_id
        if not analytic._is_forward_target(period):
            return self.env._(
                "%(line)s: %(analytic)s cannot take commitments of %(period)s: "
                "choose an analytic of the period, or without Budget Period, open "
                "on %(date)s.",
                line=self.display_name,
                analytic=analytic.display_name,
                period=period.display_name,
                date=format_date(self.env, period.bm_date_from),
            )
        if (
            analytic.company_id
            and company
            and analytic.company_id not in company.parent_ids
        ):
            return self.env._(
                "%(line)s: %(analytic)s is not of the company of the document.",
                line=self.display_name,
                analytic=analytic.display_name,
            )
        if not docline._check_budget_forward_row(self._get_target_row_key()):
            return self.env._(
                "%(line)s: the forward dimensions need an account of each "
                "mandatory plan.",
                line=self.display_name,
            )
        return False

    def _get_target_row_key(self):
        """Row the commitment is carried forward to: the forward analytic with
        the forward dimensions."""
        self.ensure_one()
        return budget_row_key(
            {self.to_analytic_account_id.id, *self.to_dimension_ids.ids}
        )

    def _get_target_column_vals(self, model):
        """Plan columns of ``model`` for the forward dimensions, the others
        empty."""
        self.ensure_one()
        vals = dict.fromkeys(
            [
                fname
                for fname in self.env[model]._fields
                if BUDGET_COLUMN.fullmatch(fname)
            ],
            False,
        )
        vals.update(
            self.env["account.analytic.plan"]._get_budget_column_vals(
                self.to_dimension_ids, model
            )
        )
        return vals

    def _get_budget_row_key(self, analytic=None):
        """Key of the analytic distribution row of this line, on ``analytic``
        (e.g. the carry forward analytic) instead of its own if given."""
        self.ensure_one()
        key = self.env["account.analytic.plan"]._get_budget_row_key(self)
        if analytic is None:
            return key
        account_ids = {int(aid) for aid in key.split(",")}
        account_ids.discard(self.analytic_account_id.id)
        return budget_row_key(account_ids | {analytic.id})

    @api.depends(
        lambda self: [
            "analytic_account_id",
            *(fname for fname in self._fields if BUDGET_COLUMN.fullmatch(fname)),
        ]
    )
    def _compute_dimension_ids(self):
        fnames = [fname for fname in self._fields if BUDGET_COLUMN.fullmatch(fname)]
        for line in self:
            line.dimension_ids = line.dimension_ids.browse().union(
                line[fname] for fname in fnames
            )

    @api.depends("to_analytic_account_id", "to_dimension_ids", "dimension_ids")
    def _compute_forward_changed(self):
        for line in self:
            default = line.analytic_account_id._get_forward_analytic(
                line.forward_id.to_budget_period_id
            )
            line.forward_changed = bool(line.to_analytic_account_id) and (
                line.to_analytic_account_id != default
                or line.to_dimension_ids != line.dimension_ids
            )

    @api.depends(
        "analytic_account_id.next_analytic_id",
        "analytic_account_id.bm_date_from",
        "analytic_account_id.bm_date_to",
        "forward_id.to_budget_period_id",
    )
    def _compute_to_analytic_account_id(self):
        for rec in self:
            # A chosen analytic stays, and done or cancelled forwards keep
            # where they carried their lines
            if rec.to_analytic_account_id or rec.forward_id.state in (
                "done",
                "cancel",
            ):
                continue
            rec.to_analytic_account_id = rec.analytic_account_id._get_forward_analytic(
                rec.forward_id.to_budget_period_id
            )

    @api.depends("document_number", "analytic_account_id")
    def _compute_display_name(self):
        res = super()._compute_display_name()
        for fwd_line in self:
            doc_name = fwd_line.document_number.display_name
            analytic_name = fwd_line.analytic_account_id.name
            fwd_line.display_name = f"{doc_name} - {analytic_name}"
        return res
