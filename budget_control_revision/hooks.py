# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    _logger.info("Assign unrevisioned_name for existing documents")
    query = """
    update budget_control
    set unrevisioned_name = name
    where unrevisioned_name is null
    """
    cr.execute(query)
