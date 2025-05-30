
<!-- /!\ Non OCA Context : Set here the badge of your runbot / runboat instance. -->
[![Pre-commit Status](https://github.com/ecosoft-odoo/budgeting/actions/workflows/pre-commit.yml/badge.svg?branch=18.0)](https://github.com/ecosoft-odoo/budgeting/actions/workflows/pre-commit.yml?query=branch%3A18.0)
[![Build Status](https://github.com/ecosoft-odoo/budgeting/actions/workflows/test.yml/badge.svg?branch=18.0)](https://github.com/ecosoft-odoo/budgeting/actions/workflows/test.yml?query=branch%3A18.0)
[![codecov](https://codecov.io/gh/ecosoft-odoo/budgeting/branch/18.0/graph/badge.svg)](https://codecov.io/gh/ecosoft-odoo/budgeting)
<!-- /!\ Non OCA Context : Set here the badge of your translation instance. -->

<!-- /!\ do not modify above this line -->

# Budgeting

The Budgeting module for Odoo provides a structured and efficient way to manage budgets within an organization. It allows users to define, track, and control budget allocations while ensuring financial transparency.

<!-- /!\ do not modify below this line -->

<!-- prettier-ignore-start -->

[//]: # (addons)

Available addons
----------------
addon | version | maintainers | summary
--- | --- | --- | ---
[base_tier_validation_check_budget](base_tier_validation_check_budget/) | 18.0.1.0.0 | [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Add option to check budget when a tier is validated
[budget_activity](budget_activity/) | 18.0.1.0.1 | [![kittiu](https://github.com/kittiu.png?size=30px)](https://github.com/kittiu) [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Budget Activity
[budget_activity_advance_clearing](budget_activity_advance_clearing/) | 18.0.1.0.1 | [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Budget Activity - Advance/Clearing
[budget_activity_expense](budget_activity_expense/) | 18.0.1.0.0 | [![kittiu](https://github.com/kittiu.png?size=30px)](https://github.com/kittiu) [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Budget Activity - Expense
[budget_activity_purchase](budget_activity_purchase/) | 18.0.1.0.0 | [![kittiu](https://github.com/kittiu.png?size=30px)](https://github.com/kittiu) [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Budget Activity - Purchase
[budget_activity_purchase_request](budget_activity_purchase_request/) | 18.0.1.0.0 | [![kittiu](https://github.com/kittiu.png?size=30px)](https://github.com/kittiu) | Budget Activity - Purchase Request
[budget_control](budget_control/) | 18.0.1.4.0 | [![kittiu](https://github.com/kittiu.png?size=30px)](https://github.com/kittiu) [![ru3ix-bbb](https://github.com/ru3ix-bbb.png?size=30px)](https://github.com/ru3ix-bbb) [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Budget Control
[budget_control_advance_clearing](budget_control_advance_clearing/) | 18.0.1.2.0 | [![kittiu](https://github.com/kittiu.png?size=30px)](https://github.com/kittiu) [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Budget Control on Expense extension on Advance/Clearing
[budget_control_expense](budget_control_expense/) | 18.0.1.2.0 | [![kittiu](https://github.com/kittiu.png?size=30px)](https://github.com/kittiu) [![ru3ix-bbb](https://github.com/ru3ix-bbb.png?size=30px)](https://github.com/ru3ix-bbb) [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Budget Control on Expense
[budget_control_purchase](budget_control_purchase/) | 18.0.1.2.0 | [![kittiu](https://github.com/kittiu.png?size=30px)](https://github.com/kittiu) [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Budget Control on Purchase
[budget_control_purchase_request](budget_control_purchase_request/) | 18.0.1.2.0 | [![kittiu](https://github.com/kittiu.png?size=30px)](https://github.com/kittiu) [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Budget Control on Purchase Request
[budget_control_revision](budget_control_revision/) | 18.0.1.0.0 | [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Keep track of revised budget control
[budget_plan_detail](budget_plan_detail/) | 18.0.1.1.1 | [![ps-tubtim](https://github.com/ps-tubtim.png?size=30px)](https://github.com/ps-tubtim) [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Allocated budget details
[budget_plan_detail_advance_clearing](budget_plan_detail_advance_clearing/) | 18.0.1.1.1 | [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Budget Allocation - Advance Clearing
[budget_plan_detail_expense](budget_plan_detail_expense/) | 18.0.1.1.1 | [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Budget Plan Details - Expense
[budget_plan_detail_purchase](budget_plan_detail_purchase/) | 18.0.1.1.1 | [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Budget Plan Details - Purchase
[budget_plan_detail_purchase_request](budget_plan_detail_purchase_request/) | 18.0.1.1.1 | [![Saran440](https://github.com/Saran440.png?size=30px)](https://github.com/Saran440) | Budget Plan Details - Purchase Request

[//]: # (end addons)

<!-- prettier-ignore-end -->

## Licenses

This repository is licensed under [AGPL-3.0](LICENSE).

However, each module can have a totally different license, as long as they adhere to Ecosoft
policy. Consult each module's `__manifest__.py` file, which contains a `license` key
that explains its license.

----
<!-- /!\ Non OCA Context : Set here the full description of your organization. -->
