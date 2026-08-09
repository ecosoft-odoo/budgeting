# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Initialize the generic budget scopes added in this version."""
    cr.execute(
        """
        UPDATE budget_period
           SET budget_scope = CASE
               WHEN budget_scope = 'project' THEN 'lifetime'
               ELSE 'fiscal'
           END
         WHERE budget_scope IS NULL OR budget_scope = 'project'
        """
    )
    cr.execute(
        """
        UPDATE account_analytic_account
           SET budget_control_scope = CASE
               WHEN budget_control_scope = 'project' THEN 'lifetime'
               ELSE 'fiscal'
           END
         WHERE budget_control_scope IS NULL
            OR budget_control_scope = 'project'
        """
    )
