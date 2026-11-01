1.  Menu \> Budgeting \> Budget Planning \> Budget Plan, create a plan for a
    fiscal Budget Period.
2.  Add the analytic accounts with **Get All Analytic Accounts** or by hand,
    and enter their New Budget. The Forward Balance of the period is added
    to the Allocated amount. Confirming the plan adds the yearly analytics
    of its period, and the analytics without Budget Period open in it that
    are dated or had a Budget Control Sheet the period before.
3.  Confirm the plan, then click **Create/Update Budget Control** to create
    the Budget Control Sheets or update their Allocated amount.

A plan line can be allocated by dimension with its **Details** button,
e.g. Department 1 gets Fund A 100 and Fund B 50 (accounts of plans
without Control Budget): they allocate its New Budget and Forward
Balance, the New Budget being their sum less the forward balance, and
its Budget Control Sheet stays one for the analytic account. A forward
balance completed after them is left Unallocated: the plan is confirmed,
and its sheets created or updated, once the details allocate it. A detail may leave out the
account of a plan, e.g. Fund A and Fund A / Type 1: documents match the
detail with exactly their accounts, Fund A without a type or Fund A /
Type 1, unless the plan is mandatory in budget plans (its default
applicability, or an applicability for the Budget Plan domain): each
detail then needs one. With **Control Allocation**
of the Budget Period (ticked by default), the budget check then blocks
documents whose analytic rows charge an allocation that does not exist,
or that the commitments and actuals of the period exceed. Untick it to
allocate by dimension for information only. The **Allocations** page of
the sheet shows them with their Consumed and Available amounts. While
the period controls them, the details must cover the commitments and
actuals of the period by their dimensions, also when the plan is set to
draft to revise them: an account cannot be added to the only detail of
a consumed combination, nor can all the details be removed once the
analytic account has been consumed. Commitments carried forward to a
period, with their Forward Dimensions, must fit its allocations too.
