This module is a bridge between budget_control_stock and sale_stock.

When a Sale Order is confirmed, the system auto-creates a Delivery Order (DO).
At this point, the Budget Control may not yet be confirmed (the user needs to
set KPIs first). This module bypasses the stock budget commit check during SO
confirmation so the DO can be created without a budget error.

After SO confirmation, all subsequent DO operations (validate, unreserve, etc.)
enforce the budget check normally, requiring the user to confirm the Budget
Control before the DO can be processed.

An SO that creates a new Project defaults to **Lifetime** budgeting.
The system creates one Project-scoped Budget Period and one Budget Control for
the total estimated SO cost. After the user enters the Project Planned Dates,
the draft period follows those dates. Commitments and actual costs in every
fiscal year inside that range consume the same total Project balance.

The SO can instead select **Fiscal Period** before confirmation. That mode keeps
the annual behavior: one Budget Control per fiscal period, with audited carry
forward between Fiscal Periods when required.

Lifetime periods are exclusive to one analytic account, so they may
overlap the normal fiscal periods used by departments. They do not use carry
forward because the Project balance does not reset at fiscal year end.

This also supports department analytics that are not linked to a Project. If a
control is managed by a Budget Plan, the plan remains the owner of its allocated
amount; a Sale Order only links to that control.

The Sale Order cost added to a Budget Control is a planning snapshot taken when
the order is linked. Later quantity, cost, or cancellation changes do not
silently rewrite an approved budget; a budget manager reopens and adjusts the
control explicitly when required.

One Sale Order may create only one budgeted Project. Splitting an SO that would
generate several Projects keeps cost ownership explicit.
