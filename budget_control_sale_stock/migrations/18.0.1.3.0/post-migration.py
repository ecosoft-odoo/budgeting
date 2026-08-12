# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    """Initialize the Project budget scopes added in this version."""
    cr.execute(
        """
        UPDATE project_project
           SET budget_control_scope = CASE
               WHEN budget_control_scope = 'project' THEN 'lifetime'
               ELSE 'fiscal'
           END
         WHERE budget_control_scope IS NULL
            OR budget_control_scope = 'project'
        """
    )
    cr.execute(
        """
        UPDATE sale_order
           SET generated_project_budget_scope = 'lifetime'
         WHERE generated_project_budget_scope IS NULL
            OR generated_project_budget_scope = 'project'
        """
    )
