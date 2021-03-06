==============
Budget Control
==============

.. !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
   !! This file is generated by oca-gen-addon-readme !!
   !! changes will be overwritten.                   !!
   !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

.. |badge1| image:: https://img.shields.io/badge/maturity-Alpha-red.png
    :target: https://odoo-community.org/page/development-status
    :alt: Alpha
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-OCA%2Faccount--budgeting-lightgray.png?logo=github
    :target: https://github.com/OCA/account-budgeting/tree/14.0/budget_control
    :alt: OCA/account-budgeting
.. |badge4| image:: https://img.shields.io/badge/weblate-Translate%20me-F47D42.png
    :target: https://translation.odoo-community.org/projects/account-budgeting-14-0/account-budgeting-14-0-budget_control
    :alt: Translate me on Weblate
.. |badge5| image:: https://img.shields.io/badge/runbot-Try%20me-875A7B.png
    :target: https://runbot.odoo-community.org/runbot/88/14.0
    :alt: Try me on Runbot

|badge1| |badge2| |badge3| |badge4| |badge5|

This module is the main module from a set of budget control modules.
This module alone will allow you to work in full cycle of budget control process.
Other modules, each one are the small enhancement of this module, to fullfill
additional needs. Having said that, following will describe the full cycle of budget
control already provided by this module,

**Notes:**

Mis Buidler (mis_builder_budget) is used as the core engine to calculate the budgeting
figure. The budget_control modules are aimed to ease the use of budgeting in organization.

In order to understand how this module works, you should first understand
budgeting concept of mis_builder_budget.


Budget Control Core Features:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Budget Commitment (base.budget.move)**

  Probably the most crucial part of budget_control.

  * Budget Balance = Budget Allocated - (Budget Actuals - Budget Commitments)

  Actual amount are from `account.move.line` from posted invoice. Commitments can be sales/purchase,
  expense, purchase request, etc. Document required to be budget commitment can extend base.budget.move.
  For example, the module budget_control_expense will create budget commitment `expense.budget.move`
  for approved expense. These budget commitments will be used as alternate data source on mis_builder_budget.
  Note that, in this budget_control module, there is no extension for budget commitment yet.

* **Budget Period (budget.period)**

  Budget Period is the first thing to do for new budget year, and is used to govern how budget will be
  controlled over the defined date range, i.e.,

  * Duration of budget year
  * KPI to control (mis.report.instance)
  * Document to do budget checking
  * Analytic account in controlled
  * Control Level

  Although not mandatory, an organization will most likely use fiscal year as budget period.
  In such case, there will be 1 budget period per fiscal year, and multiple budget control sheet (one per analytic).

* **Budget Control Sheet (budget.control)**

  Each analytic account can have one budget control sheet per budget period.
  The budget control is used to allocate budget amount in a simpler way.
  In the backend it simply create mis.budget.item, nothing too fancy.
  Once we have budget allocations, the system is ready to perform budget check.

* **Budget Checking**

  By calling function -- check_budget(), system will check whether the confirmation
  of such document can result in negative budget balance. If so, it throw error message.
  In this module, budget check occur during posting of invoice and journal entry.
  To check budget also on more documents, do install budget_control_xxx relevant to that document.

* **Budget Reports**

  Currently there are 2 types of report.

  1. MIS Builder Reports: inherited from MIS Builder, to shows overall budget condition, overall or by each analytic.
  2. Budget Monitor Report: combine all budget related transactions, and show them in Standard Odoo BI view.

* **Budget Commitment Move Forward**

  In case budget commitment is being used. Sometime user has committed budget withing this year
  but not ready to use it and want to move the commitment amount to next year budget.
  Budget Move Forward can be use to change the budget move's date to the designated year.

Extended Modules:
~~~~~~~~~~~~~~~~~

Following are brief explanation of what the extended module will do.

**Budget Transfer**

This module allow transferring allocated budget from one budget control sheet to other

* budget_control_transfer

**Budget Move extension**

These modules extend base.budget.move for other document budget commitment.

* budget_control_expense
* budget_control_purchase
* budget_control_purchase_request
* budget_control_sale

**Budget Source of Fund**

This module allow create Master Data source of fund.
there is relation between source of fund and budget control sheet
for allocated source of fund from one budget control sheet to many source of fund.
Users can view source of fund monitoring report

* budget_source_fund

**Tier Validation**

Extend base_tier_validation for budget control sheet

* budget_control_tier_validation

**Analytic Tag Dimension Enhancements**

When 1 dimension (analytic account) is not enough,
we can use dimension to create persistent dimension columns

- analytic_tag_dimension
- account_tag_dimension_enhanced

Following modules ensure that, analytic_tag_dimension will work with all new
budget control objects. These are important for reporting purposes.

* budget_control_tag_dimension
* budget_control_expense_tag_dimension
* budget_control_purchase_tag_dimension

.. IMPORTANT::
   This is an alpha version, the data model and design can change at any time without warning.
   Only for development or testing purpose, do not use in production.
   `More details on development status <https://odoo-community.org/page/development-status>`_

**Table of contents**

.. contents::
   :local:

Usage
=====

Before start using this module, following access right must be set.
  - Budget User for Budget Control Sheet, Budget Report
  - Budget Manager for Budget Period

Followings are sample steps to start with,

1. Create new Budget Period

    - Choose KPI template (KPI should filter 'not_affect_budget' in KPI i.e., balp[510000]['|', ('move_id', '=', False), ('move_id.not_affect_budget', '=', False)])
    - Identify date range, i.e., 1 fiscal year
    - Plan Date Range, i.e., Quarter, the slot to fill allocation in budget control will split by quarter
    - Budget Control - On Account = True

   Note: Upon creation, the MIS Budget (mis.budget) will be created automatically.
   The following steps will create mis.budget.item for it.

2. Create Budget Control Sheet

   To create budget control sheet, you can either create manually one by one or by using the helper,
   Action > Create Budget Control Sheet

    - Choose Analytic budget_control_purchase_tag_dimension
    - Check All Analytic Account, this will list all analytic account in selected groups
    - Uncheck Initial Budget By Commitment, this is used only on following year to
      init budget allocation if they were committed amount carried over.
    - Click "Create Budget Control Sheet", and then view the newly created control sheets.

3. Allocate amount in Budget Control Sheets

   Each analytic account will have its own sheet. Form Budget Period, click on the
   icon "Budget Control Sheets" or by Menu > Budgeting > Budget Control Sheet, to open them.

    - Based on "Plan Date Range" period, Plan table will show all KPI split by Plan Date Range
    - Allocate budget amount as appropriate.
    - Click Control button, state will change to Controlled.

   Note: Make sure the Plan Date Rang period already has date ranges that covers entire budget period.
   Once ready, you can click on "Reset Plan" anytime.

4. Budget Reports

   After some document transaction (i.e., invoice for actuals), you can view report anytime.

    - On both Budget Period and Budget Control sheet, click on Preview/Run/Export for MIS Report
    - Menu Budgeting > Budget Monitoring, to show budget report in standard Odoo BI view.

5. Budget Checking

   As we have checked Budget Control - On Account = True in first step, checking will occur
   every time an invoice is validated. You can test by validate invoice with big amount to exceed.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/account-budgeting/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed
`feedback <https://github.com/OCA/account-budgeting/issues/new?body=module:%20budget_control%0Aversion:%2014.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Do not contact contributors directly about support or help with technical issues.

Credits
=======

Authors
~~~~~~~

* Ecosoft

Contributors
~~~~~~~~~~~~

* Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
* Saran Lim. <saranl@ecosoft.co.th>

Maintainers
~~~~~~~~~~~

This module is maintained by the OCA.

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

.. |maintainer-kittiu| image:: https://github.com/kittiu.png?size=40px
    :target: https://github.com/kittiu
    :alt: kittiu

Current `maintainer <https://odoo-community.org/page/maintainer-role>`__:

|maintainer-kittiu|

This module is part of the `OCA/account-budgeting <https://github.com/OCA/account-budgeting/tree/14.0/budget_control>`_ project on GitHub.

You are welcome to contribute. To learn how please visit https://odoo-community.org/page/Contribute.
