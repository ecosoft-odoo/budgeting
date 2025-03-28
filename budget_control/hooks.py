# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def update_data_hooks(env):
    # Enable Analytic Account
    env.ref("base.group_user").write(
        {"implied_ids": [(4, env.ref("analytic.group_analytic_accounting").id)]}
    )


def uninstall_hook(env):
    """Delete all data related to budget control"""
    env["budget.template"].search([]).unlink()
    env["budget.period"].search([]).unlink()
    env["budget.control"].search([]).unlink()
