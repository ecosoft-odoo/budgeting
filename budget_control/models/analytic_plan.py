# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

from lxml.builder import E

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

BUDGET_COLUMN = re.compile(r"x_plan(\d+)_id")


def budget_row_key(account_ids):
    """Key of a row of an analytic distribution: its account ids, sorted, as
    in ``{"12,34": 100}``."""
    return ",".join(str(account_id) for account_id in sorted(account_ids))


class AccountAnalyticPlan(models.Model):
    _inherit = "account.analytic.plan"

    control_budget = fields.Boolean(
        default=True,
        help="Check budget on the accounts of this plan. A row of an analytic "
        "distribution can charge only one account of such plans; accounts of "
        "other plans are for reporting only. Only the root plan counts.",
    )

    @api.constrains("control_budget")
    def _check_control_budget(self):
        roots = self.filtered(
            lambda plan: not plan.parent_id and not plan.control_budget
        )
        if not roots:
            return
        controls = (
            self.env["budget.control"]
            .sudo()
            .with_context(active_test=False)
            .search([("analytic_account_id.root_plan_id", "in", roots.ids)], limit=1)
        )
        if controls:
            raise ValidationError(
                self.env._(
                    "Plan %s has budget control sheets, so Control Budget must "
                    "stay ticked.",
                    controls.analytic_account_id.root_plan_id.display_name,
                )
            )

    def _budget_column_name(self):
        """Column of the plan on budget moves and the monitoring report.

        Like core's ``_column_name()``, but the project plan also gets
        ``x_plan<id>_id``: ``account_id`` is the GL account on budget moves.
        Only plans without Control Budget have one: the account of a plan
        with Control Budget is the move's ``analytic_account_id``.
        """
        self.ensure_one()
        return f"x_plan{self.root_id.id}_id"

    @api.model
    def _patch_budget_plan_view(self, arch, view_type, model):
        """Show the plan columns of ``model`` next to its budget analytic, like
        core does for analytic lines (``analytic.plan.fields.mixin``). ``arch``
        can also be the sub-view of a budget move field in another view."""
        if self.env.context.get("studio") or not self.has_access("read"):
            return arch
        fields = self.env[model]._fields
        plans = [
            plan
            for plan in self.sudo().search([("parent_id", "=", False)])
            if plan._budget_column_name() in fields
        ]
        if view_type in ("list", "form"):
            # The columns are as read-only as the budget analytic, unless the
            # model says otherwise
            readonly = getattr(
                self.env[model],
                "_budget_plan_columns_readonly",
                fields["analytic_account_id"].readonly,
            )
            readonly = "1" if readonly else None
            for node in arch.iterfind('.//field[@name="analytic_account_id"]'):
                for plan in reversed(plans):
                    attrs = {
                        "name": plan._budget_column_name(),
                        "domain": repr([("root_plan_id", "=", plan.id)]),
                    }
                    if view_type == "list":
                        attrs["optional"] = getattr(
                            self.env[model], "_budget_plan_columns_optional", "show"
                        )
                    if node.get("readonly", readonly):
                        attrs["readonly"] = node.get("readonly", readonly)
                    node.addnext(E.field(**attrs))
        elif view_type == "search":
            for node in arch.iterfind('.//filter[@name="group_by_analytic_account"]'):
                for plan in reversed(plans):
                    fname = plan._budget_column_name()
                    node.addnext(
                        E.filter(
                            name=f"group_by_{fname}",
                            string=plan.name,
                            context=repr({"group_by": fname}),
                        )
                    )
        return arch

    @api.model
    def _get_budget_column_vals(self, analytics, model):
        """``{x_plan<id>_id: account id}`` for the ``analytics`` that have a
        column on ``model``."""
        fields = self.env[model]._fields
        vals = {}
        for analytic in analytics.sudo():
            fname = analytic.root_plan_id._budget_column_name()
            if fname in fields:
                vals[fname] = analytic.id
        return vals

    @api.model
    def _get_budget_row_key(self, record):
        """Distribution row key of ``record``, a budget move or another record
        with plan columns: its budget analytic and the accounts of its
        columns."""
        account_ids = {
            record[fname].id
            for fname in record._fields
            if fname == "analytic_account_id" or BUDGET_COLUMN.fullmatch(fname)
        }
        account_ids.discard(False)
        return budget_row_key(account_ids)

    @api.model
    def _get_budget_move_models(self):
        names = self.env.registry.descendants(["base.budget.move"], "_inherit")
        return [name for name in sorted(names) if not self.env[name]._abstract]

    @api.model
    def _get_budget_column_models(self):
        """Models that get one analytic column per root plan without Control
        Budget."""
        return self._get_budget_move_models() + [
            "budget.commit.forward.line",
            "budget.monitor.report",
        ]

    @api.model
    def _sync_budget_columns(self):
        """Keep one ``x_plan<id>_id`` field per root plan without Control
        Budget on the budget models, as core's ``_sync_plan_column()`` does for
        analytic lines.

        Modules adding a budget move model call it from their data, like
        ``data/analytic_plan_data.xml``.
        """
        roots = self.sudo().search(
            [("parent_id", "=", False), ("control_budget", "=", False)]
        )
        wanted = {plan._budget_column_name(): plan for plan in roots}
        IrModelFields = self.env["ir.model.fields"].sudo()
        to_create = []
        for model in self._get_budget_column_models():
            Model = self.env[model]
            existing = {
                field.name: field
                for field in IrModelFields.search(
                    [("model", "=", model), ("state", "=", "manual")]
                )
                if BUDGET_COLUMN.fullmatch(field.name)
            }
            index = "btree_not_null" if Model._auto else False
            for fname, field in existing.items():
                plan = wanted.get(fname)
                if plan and field.field_description != plan.name:
                    field.field_description = plan.name
                if plan and field.index != index:
                    field.index = index
            stale = [fname for fname in existing if fname not in wanted]
            if stale:
                IrModelFields.browse(
                    existing[fname].id for fname in stale
                ).with_context(force_delete=True).unlink()
            model_id = self.env["ir.model"]._get_id(model)
            for fname, plan in wanted.items():
                if fname not in existing:
                    to_create.append(
                        {
                            "name": fname,
                            "field_description": plan.name,
                            "state": "manual",
                            "model": model,
                            "model_id": model_id,
                            "ttype": "many2one",
                            "relation": "account.analytic.account",
                            "copied": True,
                            "on_delete": "restrict",
                            "index": index,
                        }
                    )
        if to_create:
            IrModelFields.with_context(update_custom_fields=True).create(to_create)

    @api.model
    def _check_budget_moves_unused(self, analytics, message):
        """Raise ``message`` if budget moves, or other records with plan
        columns, already use ``analytics``, as budget analytic or in a plan
        column."""
        for model in self._get_budget_column_models():
            if not self.env[model]._auto:
                continue
            Model = self.env[model].sudo().with_context(active_test=False)
            fnames = ["analytic_account_id"] + [
                fname for fname in Model._fields if BUDGET_COLUMN.fullmatch(fname)
            ]
            domain = ["|"] * (len(fnames) - 1) + [
                (fname, "in", analytics.ids) for fname in fnames
            ]
            if Model.search_count(domain, limit=1):
                raise UserError(message)

    def write(self, vals):
        if "control_budget" in vals:
            # Budget moves keep the account of a plan either as budget analytic
            # or in the plan column, depending on Control Budget
            changed = self.filtered(
                lambda plan: plan.control_budget != bool(vals["control_budget"])
            )
            for plan in changed:
                self._check_budget_moves_unused(
                    self.env["account.analytic.account"]
                    .with_context(active_test=False)
                    .search([("plan_id", "child_of", plan.id)]),
                    self.env._(
                        "Plan %s is used on budget moves, so Control Budget cannot "
                        "change.",
                        plan.display_name,
                    ),
                )
        if "parent_id" in vals:
            # Budget moves keep their accounts in the column of the root plan
            for plan in self:
                self._check_budget_moves_unused(
                    self.env["account.analytic.account"]
                    .with_context(active_test=False)
                    .search([("plan_id", "child_of", plan.id)]),
                    self.env._(
                        "Plan %s is used on budget moves, so its parent cannot change.",
                        plan.display_name,
                    ),
                )
        res = super().write(vals)
        if "control_budget" in vals or "parent_id" in vals:
            # See account.analytic.account._get_analytic_control_budget()
            self.env.transaction.invalidate_ormcache()
        if "control_budget" in vals:
            self._sync_budget_columns()
        return res

    def _sync_all_plan_column(self):
        res = super()._sync_all_plan_column()
        self._sync_budget_columns()
        return res

    def unlink(self):
        res = super().unlink()
        self.env["account.analytic.plan"]._sync_budget_columns()
        return res
