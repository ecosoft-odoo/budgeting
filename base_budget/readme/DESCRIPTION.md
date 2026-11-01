This module defines the Budget Period (`budget.period`), the time frame shared by
budget applications such as budget proposals and budget control.

A period has a date range, the companies it applies to (empty: all companies) and a
scope:

- **Fiscal Period**: selected by document date. Fiscal periods of the same
  companies (a company and its branches included) cannot overlap, so a date always
  belongs to one fiscal period per company.
- **Lifetime**: a multi-year budget of one analytic account, which may overlap
  fiscal periods. Lifetime periods are managed by Budget Control.

Budget periods can be configured under Settings > Technical > Budget > Budget
Periods. Each budget application can also add the period to its own configuration
menu and add its own settings to the period.
