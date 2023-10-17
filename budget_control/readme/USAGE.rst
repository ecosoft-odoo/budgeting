Before start using this module, following access right must be set.

   - Budget User for Budget Control Sheet, Budget Report
   - Budget Manager for Budget Period

Followings are sample steps to start with,

1. Create new Budget KPI

   - To create budget KPI using in budget template

2. Create new Budget Template

   - Add new template for controlling Budget following kpi-account

3. Create new Budget Period

    - Choose Budget template
    - Identify date range, i.e., 1 fiscal year
    - Plan Date Range, i.e., Quarter, the slot to fill allocation in budget control will split by quarter
    - Control Budget = True (if not check = not check budget for this period)

4. Create Budget Control Sheet

   To create budget control sheet, you can create by using the helper,
   Action > Create Budget Control Sheet

    - Choose Analytic Group
    - Check All Analytic Accounts, this will list all analytic account in selected groups
    - Uncheck Initial Budget By Commitment, this is used only on following year to
      init budget allocation if they were committed amount carried over.
    - Click "Generate Budget Control Sheet", and then view the newly created control sheets.

5. Allocate amount in Budget Control Sheets

   Each analytic account will have its own sheet. Form Budget Period, click on the
   icon "Budget Control" or by Menu > Budgeting > Budget Control Sheet, to open them.

    - Within the "Plan Date Range" period, the Plan table displays all KPIs split by Plan Date Range
    - If you need to edit the plan, click the "Reset Options" tab, then select the KPIs you want to plan
    - Click the "Soft Reset" button to generate KPIs. The amounts in the plan table will not disappear.
    - Click the "Hard Reset" button to generate KPIs. The amounts in the plan table will disappear.
    - Allocate budget amount as appropriate.
    - Click Submit > Control, state will change to Controlled.

   Note: Make sure the Plan Date Rang period already has date ranges that covers entire budget period.
   Once ready, you can click on "Soft Reset" or "Hard Reset" anytime.

6. Budget Reports

   After some document transaction (i.e., invoice for actuals), you can view report anytime.

    - On Budget Control sheet, click on Monitoring for see this budget report
    - Menu Budgeting > Budget Monitoring, to show budget report in standard Odoo BI view.

7. Budget Checking

   As we have checked Control Budget = True in third step, checking will occur
   every time an invoice is validated. You can test by validate invoice with big amount to exceed.
