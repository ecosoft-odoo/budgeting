# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def post_init_hook(env):
    """Overwrite rule budget control, Everyone can see the budget control,
    with operating unit being the main rule for filtering instead."""
    env.ref("budget_control.rule_budget_control_budget_user").write(
        {"domain_force": "[(1, '=', 1)]"}
    )
