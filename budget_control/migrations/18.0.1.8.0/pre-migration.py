# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def migrate(cr, version):
    cr.execute(
        """
        CREATE TABLE IF NOT EXISTS budget_control_assignee_rel (
            budget_control_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (budget_control_id, user_id)
        )
    """
    )
    cr.execute(
        """
        INSERT INTO budget_control_assignee_rel (budget_control_id, user_id)
        SELECT id, assignee_id
        FROM budget_control
        WHERE assignee_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """
    )
