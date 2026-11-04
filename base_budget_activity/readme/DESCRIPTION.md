This module defines the Budget Activity (`budget.activity`), the list of activities
shared by budget applications such as budget proposals and budget control, and its
search keywords (`budget.activity.keyword`).

An activity has a name (unique), the company it belongs to (empty: all companies) and
optional keywords to find it by other words.

The module only holds the master data. Budget applications add their own settings to
the activity, e.g. `budget_activity` adds the account and KPI used to commit budget.
