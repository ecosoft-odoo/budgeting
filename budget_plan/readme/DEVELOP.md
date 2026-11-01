- `budget.plan._prepare_budget_control_sheet()` gives the values of the
  sheets a plan creates.
- `budget.control._get_budget_allocations()` gives the details of the plan
  managing a sheet, for its analytic account.
- `budget.plan.line._get_budget_mandatory_fnames()` gives the plan columns
  each detail of a line needs.
- `budget.plan.line.detail._get_budget_consumptions(budget_period,
  analytic, fnames)` sums the commitments and actuals of an analytic
  account by dimension, and `_check_budget_allocation(budget_period,
  budget_moves)` returns the messages of the allocation check, run on the
  budget moves of `budget.period._get_control_budget_moves()`.
- `budget.commit.forward._check_forward_allocation()` runs the check on
  the commitments a forward carries to its period.
- `budget.plan._get_eligible_analytic_domain()` gives the analytics a plan
  takes when updated, and `budget.plan.line._check_details_allocated()`
  checks that the details of a line allocate its New Budget and Forward
  Balance.
