# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Assign controls when an analytic/period pair belongs to one plan only."""
    cr.execute(
        """
        WITH unique_plan AS (
            SELECT
                line.analytic_account_id,
                plan.budget_period_id,
                MIN(plan.id) AS budget_plan_id
            FROM budget_plan_line line
            JOIN budget_plan plan ON plan.id = line.plan_id
            WHERE line.analytic_account_id IS NOT NULL
              AND plan.budget_period_id IS NOT NULL
            GROUP BY line.analytic_account_id, plan.budget_period_id
            HAVING COUNT(DISTINCT plan.id) = 1
        )
        UPDATE budget_control control
           SET budget_plan_id = unique_plan.budget_plan_id
          FROM unique_plan
         WHERE control.budget_plan_id IS NULL
           AND control.analytic_account_id = unique_plan.analytic_account_id
           AND control.budget_period_id = unique_plan.budget_period_id
        """
    )
    _logger.info("Assigned Budget Plan ownership to %s controls", cr.rowcount)

    cr.execute(
        """
        SELECT COUNT(*)
          FROM (
              SELECT line.analytic_account_id, plan.budget_period_id
                FROM budget_plan_line line
                JOIN budget_plan plan ON plan.id = line.plan_id
               WHERE line.analytic_account_id IS NOT NULL
                 AND plan.budget_period_id IS NOT NULL
               GROUP BY line.analytic_account_id, plan.budget_period_id
              HAVING COUNT(DISTINCT plan.id) > 1
          ) ambiguous
        """
    )
    ambiguous_count = cr.fetchone()[0]
    if ambiguous_count:
        _logger.warning(
            "%s analytic/period pairs have multiple Budget Plans; their controls "
            "were left without an owner",
            ambiguous_count,
        )
