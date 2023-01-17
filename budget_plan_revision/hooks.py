# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    _logger.info("Assign unrevisioned_name for existing documents")
    query = """
    update budget_plan
    set unrevisioned_name = name
    where unrevisioned_name is null
    """
    cr.execute(query)
    # Disable action revision in budget control menu (use it in the budget plan instead)
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.ref("budget_control_revision.action_revision_budget_control").unlink_action()
