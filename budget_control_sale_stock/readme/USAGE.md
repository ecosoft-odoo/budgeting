To control one total cost budget for a Project that may span several years:

1. Configure a service product with **Create on Order = Project** (or
   **Project & Task**).
2. Add that product to one Sale Order. Leave **Project Budget Scope** as
   **Lifetime** and confirm the order.
3. Odoo creates the Project and Analytic Account. This module copies the fiscal
   period's control configuration into a private Lifetime period and
   creates one draft Budget Control for the total SO cost.
4. Open the generated Project and enter both Planned Start and End dates. The
   draft Budget Control follows those dates automatically.
5. Open the Budget smart button, select the KPIs, prepare plan amounts equal to
   the total estimated cost, then submit and control the budget.
6. Use the same Project Analytic Account on purchases, stock moves, expenses,
   and bills. Documents in every year within the Planned Dates consume the same
   Project balance.
7. Use the Project's **Budget Controls** smart button for monitoring.

The Project Lifetime Budget cannot be submitted until both Planned Dates are
set. Once submitted, set it back to Draft before changing the Project dates.
It does not use Forward Budget Balance.

The allocated amount is a snapshot of the Sale Order line costs at the time
the Budget Control is created. Later Sale Order edits do not silently rewrite
an approved budget.

For annual Project budgeting, choose **Fiscal Period** on the SO before
confirmation. Create or link real SOs/Budget Plans in each fiscal period. Use a
Forward Budget Balance document when unused annual balance may continue.
