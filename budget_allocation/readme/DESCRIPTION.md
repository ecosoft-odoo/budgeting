This module is the main module for manage allocation until set budget
control. For this module, budget constraints will be used to check the
allocation to ensure that the budget is not exceeded beyond the
allocated amount.

Example usage:

``` python
Budget allocation has allocation:
  Allocation Line | Analytic Account | Fund  | Tags | Allocated | ...
  --------------------------------------------------------------
  1               |               A  | Fund1 | Tag1 |     100.0 | ...
  2               |               A  | Fund2 | Tag2 |     100.0 | ...

Condition constraint (e.g. invoice lines)
  - User can use:
  Document | Line | Analytic Account | Fund  | Tags | Amount |
  -----------------------------------------------------------------------
  INV001   |    1 |             A    | Fund1 | Tag1 | 130.0  | >>> Error (-30)
  -----------------------------------------------------------------------
  INV002   |    1 |             A    | Fund1 |      | 10.0 | >>> Not allocated
  INV002   |    1 |             A    | Fund1 | Tag1 | 10.0 | >>> balance 90
  INV002   |    2 |             A    | Fund1 | Tag1 | 60.0 | >>> balance 30
  ----------------------------Confirm----------------------------
  INV003   |    1 |             A    | Fund1 | Tag1 | 10.0 | >>> balance 20
  INV003   |    2 |             A    | Fund1 | Tag1 | 60.0 | >>> Error (-40)
  ---------------------------------------------------------------
  INV004   |    1 |             A    | Fund2 | Tag1 |120.0 | >>> Not allocated
  INV004   |    1 |             A    | Fund2 | Tag2 |120.0 | >>> Error (-20)
```

## Budget Allocation Core Features:

- **Budget Allocation (budget.allocation)**  
  A new menu for detailed allocation, such as projects that receive
  funding from multiple sources and different amounts of money, must
  have budget control according to the source of funds to avoid
  exceeding what has been received. Budget allocation will help manage
  this.

- **Source of Fund (budget.source.fund)**  
  Adding new master data Source of Fund

- **Budget Source Fund Monitoring (budget.source.fund.report)**  
  Add a menu for monitoring reports by source of funds.

- **Analytic Tag Dimension**  
  Add a new Tag so that users can add additional perspectives for
  viewing reports.
