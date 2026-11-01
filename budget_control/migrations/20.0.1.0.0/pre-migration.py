# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)

PLAN_MODELS = ("budget.plan", "budget.plan.line", "budget.plan.analytic.select")
PLAN_XMLIDS = (
    "access_budget_plan",
    "access_budget_plan_analytic_select",
    "access_budget_plan_line",
    "rule_budget_plan_budget_multi_company",
    "rule_budget_plan_line_budget_multi_company",
    "budget_plan_action",
    "budget_plan_menu",
    "budget_plan_filter",
    "view_budget_plan_analytic_select_form",
    "view_budget_plan_form",
    "view_budget_plan_form_without_header",
    "view_budget_plan_line_form",
    "view_budget_plan_line_list",
    "view_budget_plan_list",
)


def _move_plan_to_budget_plan(cr):
    """Budget plans moved to the module budget_plan. Install it in this
    upgrade and hand the plan records over to it, so that the update of
    budget_control does not delete them."""
    cr.execute("SELECT 1 FROM ir_model WHERE model = 'budget.plan'")
    if not cr.rowcount:
        return
    cr.execute(
        """
        UPDATE ir_module_module SET state = 'to install'
         WHERE name = 'budget_plan' AND state IN ('uninstalled', 'to remove')
        """
    )
    if not cr.rowcount:
        _logger.warning("Module budget_plan not found: install it to keep plans.")
    queries = [
        # Models and their fields, selections and mixins
        """
        UPDATE ir_model_data d SET module = 'budget_plan'
          FROM ir_model m
         WHERE d.model = 'ir.model' AND d.res_id = m.id AND m.model IN %(models)s
           AND d.module = 'budget_control'
        """,
        """
        UPDATE ir_model_data d SET module = 'budget_plan'
          FROM ir_model_fields f
         WHERE d.model = 'ir.model.fields' AND d.res_id = f.id
           AND (f.model IN %(models)s
                OR (f.model = 'budget.control' AND f.name = 'budget_plan_id'))
           AND d.module = 'budget_control'
        """,
        """
        UPDATE ir_model_data d SET module = 'budget_plan'
          FROM ir_model_fields_selection s
          JOIN ir_model_fields f ON f.id = s.field_id
         WHERE d.model = 'ir.model.fields.selection' AND d.res_id = s.id
           AND f.model IN %(models)s AND d.module = 'budget_control'
        """,
        """
        UPDATE ir_model_data d SET module = 'budget_plan'
          FROM ir_model_inherit i
          JOIN ir_model m ON m.id = i.model_id
         WHERE d.model = 'ir.model.inherit' AND d.res_id = i.id
           AND m.model IN %(models)s AND d.module = 'budget_control'
        """,
        # Views, actions, menus and access rules
        """
        UPDATE ir_model_data SET module = 'budget_plan'
         WHERE module = 'budget_control' AND name IN %(xmlids)s
        """,
    ]
    cr.execute(
        """
        SELECT name, id FROM ir_module_module
         WHERE name IN ('budget_control', 'budget_plan')
        """
    )
    module_ids = dict(cr.fetchall())
    if "budget_plan" in module_ids:
        # Database constraints and many2many tables, dropped on uninstall
        queries += [
            """
            UPDATE ir_model_constraint c SET module = %(plan_module)s
              FROM ir_model m
             WHERE c.model = m.id AND c.module = %(control_module)s
               AND (m.model IN %(models)s
                    OR c.name = 'budget_control_budget_plan_id_fkey')
            """,
            """
            UPDATE ir_model_relation r SET module = %(plan_module)s
              FROM ir_model m
             WHERE r.model = m.id AND r.module = %(control_module)s
               AND m.model IN %(models)s
            """,
        ]
    params = {
        "models": PLAN_MODELS,
        "xmlids": PLAN_XMLIDS,
        "plan_module": module_ids.get("budget_plan"),
        "control_module": module_ids.get("budget_control"),
    }
    for query in queries:
        cr.execute(query, params)


def migrate(cr, version):
    if not version:
        return
    _move_plan_to_budget_plan(cr)
