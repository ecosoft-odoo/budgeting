Before start using this module, following access right must be set.  
- Budget User for Budget Control Sheet, Budget Report
- Budget Manager for Budget Period

Followings are sample steps to start with,

0.  Set up the analytic plans

    - Keep **Control Budget** ticked on the root plans whose accounts own
      budgets (e.g. Departments, Projects) and untick it on plans used for
      reporting only (e.g. Fund).
    - One row of an analytic distribution can hold only one account of a
      controlled plan, and one account of each plan. To charge two budgets,
      split the line into rows by percentage. The same account may be in
      several rows, e.g. Department 1 / Fund A 60% and Department 1 /
      Fund B 40%: each row commits its own part.
    - Budget moves and the Budget Monitoring report get one column per root
      plan without Control Budget, so they can be grouped by it, e.g. by
      Fund. The account of a controlled plan is the Analytic Account of the
      move. Control Budget cannot change once budget moves use the plan.

    - Budgets follow the company of their analytic account, as in Odoo: an
      analytic account without company can be used by every company, one with
      a company by that company and its branches. To share a budget between
      some companies only, use an analytic account without company and set the
      **Allowed Companies** of its budget control sheet; documents of other
      companies cannot consume it.

1.  Create new Budget KPI

    To create budget KPI using in budget template

2.  Create new Budget Template

    - Add new template for controlling Budget following kpi-account

3.  Create new Budget Period

    > - Choose Budget template
    > - Identify date range, i.e., 1 fiscal year
    > - Plan Date Range, i.e., Quarter, the slot to fill allocation in
    >   budget control will split by quarter
    > - Control Budget = True (if not check = not check budget for this
    >   period)

    Normal periods use the **Fiscal Period** scope. Lifetime periods are
    restricted to one analytic account and may overlap fiscal periods safely.

4.  Create Budget Control Sheet

    Menu \> Budgeting \> Budget Control Sheet, create one sheet per
    analytic account and budget period, with its Allocated amount. Its
    name and Plan Date Range come from the period. Choose its KPIs and click
    **Soft Reset** to create the plan table.

    With the module budget_plan, sheets are created from a Budget Plan
    instead, which then manages their Allocated amount.

5.  Allocate amount in Budget Control Sheets

    Each analytic account will have its own sheet. Form Budget Period,
    click on the icon "Budget Control Sheets" or by Menu \> Budgeting \>
    Budget Control Sheet, to open them.

    > - Based on "Plan Date Range" period, Plan table will show all KPI
    >   split by Plan Date Range
    > - Allocate budget amount as appropriate.
    > - Click Control button, state will change to Controlled.

    Note: Make sure the Plan Date Rang period already has date ranges
    that covers entire budget period. Once ready, you can click on
    "Reset Plan" anytime.

6.  Budget Reports

    After some document transaction (i.e., invoice for actuals), you can
    view report anytime.

    > - On Budget Control sheet, click on Monitoring for see this budget
    >   report
    > - Menu Budgeting \> Budget Monitoring, to show budget report in
    >   standard Odoo BI view.

7.  Budget Checking

    As we have checked Control Budget = True in third step, checking
    will occur every time an invoice is validated. You can test by
    validate invoice with big amount to exceed.

8.  Create a Lifetime budget without a Project

    - Open the Analytic Account and click **Create Lifetime Budget**.
    - Enter the fixed Start Date, End Date, Budget Template, planning range, and
      Total Budget.
    - Ensure the selected planning range has Date Ranges covering the complete
      Lifetime duration. The setup stops without creating partial records when a
      range is missing.
    - The system creates one dedicated Lifetime Period and one draft Budget
      Control. Distribute the total on its control lines, then submit and
      control it normally.

    Lifetime is suitable for a campaign, grant, contract, or other one-off
    initiative that can span several fiscal years. It does not use a Budget
    Plan or carry forward. Lifetime analytics are therefore excluded from
    Fiscal Budget Plan allocation, including the **Refresh** and **Get All
    Analytic Accounts** actions; allocate them directly on their dedicated
    Budget Control instead.

9.  Close a year: carry commitments and balances to the next period

    An analytic is used in one of two ways:

    - **Continuing**: the same analytic for years, without Budget Period. It
      continues as itself while it is open: leave its Date To empty, or extend
      it. Each period has its own Budget Control Sheet for it.
    - **Yearly**: a new analytic each period, with that Budget Period. It
      continues as the analytic in its **Continues As** field, an analytic of
      the next period.

    **Continue in Budget Period**, from the analytics list (Action) or the
    forwards (**Continue Analytics**), proposes it for the analytics that do
    not continue yet: it extends continuing analytics that end before the
    period, links yearly ones to the only analytic of the period with the
    same name, code, root plan and company, or creates their copy for the
    period. Choose the analytic when several match.

    Then:

    - **Forward Budget Commitment** carries the open commitments to the
      period, on the analytic each continues as (editable by line, e.g. to
      carry some documents elsewhere) and their Forward Dimensions. A
      commitment not used in that period is carried again by the next one.
    - **Forward Budget Balance** carries the available balance of each
      analytic, after the commitments are forwarded: their budget comes with
      them. Its preview warns of commitments still in the period. Adjust the
      amounts or remove lines that must lapse before completing the forward.
    - Create the target-period Budget Plan. It takes the yearly analytics of
      the period and the continuing ones budgeted the period before, and its
      Forward Balance is included in the amount available for the new Budget
      Control Sheet.

    Lifetime analytics are not carried forward: their commitments and
    balance remain available for their complete duration.
