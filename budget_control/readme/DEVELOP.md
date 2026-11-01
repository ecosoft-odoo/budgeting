Extension modules, e.g. budgets of purchases or expenses, build on these
hooks.

**Document lines** inherit `budget.docline.mixin` and set
`_budget_move_model`, `_doc_rel` and `_budget_date_commit_fields`
(`_budget_analytic_field` is `analytic_distribution` by default).

- A row of the analytic distribution commits one budget analytic, an
  account of a plan with Control Budget, with its full percentage. In
  `_init_docline_budget_vals(budget_vals, analytic_id)`, take the
  percentage of the row being committed from
  `_get_budget_analytic_percent(analytic_id)`, not from
  `distribution[str(analytic_id)]`.
- `amount_commit` is keyed by row, `budget_row_key()` of
  `odoo.addons.budget_control.models.analytic_plan`, and
  `return_amount_commit` in context may be such a dict.
- `commit_budget()` creates one budget move per row and calls
  `_update_template_line(budget_move)` for each.
- `recompute_budget_move_batch()`, used by journal items and budget
  adjustments, and the batch precommit of models whose
  `_can_batch_budget_precommit()` is true, do not call `commit_budget()`:
  extend `_prepare_commit_vals()` or `_init_docline_budget_vals()`.
- `_get_budget_company()` is the company of the document, whose budget
  settings apply: use it in `_get_included_tax()`.

**Budget move models** inherit `base.budget.move`. Their plan columns
`x_plan<id>_id`, one per root plan without Control Budget, are created
by `account.analytic.plan._sync_budget_columns()`: call it from the data
of the module, as `data/analytic_plan_data.xml` does.

**Budget check** (`budget.period`):

- `_get_control_budget_moves(budget_period, doclines)` selects the budget
  moves a period checks, and `_prepare_controls()` their controls.
- `_get_where_domain(analytic_id, template_lines)` returns an `SQL`
  object. Extensions adding filters to it also override
  `_can_use_budget_available_cache()` to return `False` for them.
- `_get_analytic_budget_control(analytic, date_commit, company)` of
  document lines gives the budget control sheet; its `currency_id`
  replaces `_get_analytic_budget_currency()`.
- Budget Constraints run a server action with `doclines` in context,
  whose `action` is the list of error messages.

**Continuation**: `account.analytic.account._get_forward_analytic(period)`
gives the analytic the budgets and commitments of an analytic are carried
forward to in a period: itself when `_is_forward_target(period)` (fiscal,
of a plan with Control Budget, of that period or without Budget Period,
open when it starts), else along `next_analytic_id`; none for Lifetime
analytics. The `budget.analytic.continue` wizard extends
(`_extend_budget_analytic()`), links (`_get_next_analytic_matches()`) or
creates (`_prepare_next_analytic_vals()`) them, and
`_get_continue_action(period, analytics)` opens it. Commitment and balance
forward lines default their forward analytic to it.

**Commitment forwards** carry each analytic row to the forward analytic
and the Forward Dimensions of its line (`to_dimension_ids`, those of the
row by default): `_get_target_row_key()` and `_get_target_column_vals()`
give the target row, `_get_budget_row_key()` the source row. On document
lines, `_get_budget_forward_date()` and `_get_budget_rows_at(date)` give
where the done forwards carried the commitment, e.g. to check the rows
of a bill. Before anything changes, `_check_forward_targets()` refuses
the lines `_get_target_error()` returns a message for, e.g. when the
target row fails `_check_budget_forward_row(row_key)` of the document
line: the check of its own `_validate_analytic_distribution()`, such as
its mandatory plans. Rows of Lifetime analytics are not forwarded, and
`budget.commit.forward.line._get_commit_forward_in_map(period_ids,
analytic_ids)` sums the commitments the done forwards carried in.

**Monitoring** (`budget.monitor.report`): its query is `_table_sql`. A
source of consumption is added to `_get_consumed_sources()`, and its
branch to `_get_sql_branches()` with `_get_consumed_sql(amount_type,
where)`, instead of appending SQL text to `_get_sql()`. Branches without
plan columns select `_select_plan_columns_null()`. The monitoring shows
the amount types in the order of their keys, e.g. `30_po_commit` before
`80_actual`: a commitment takes a key before `80_`.
