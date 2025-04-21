# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    _logger.info("Assign unrevisioned_name for existing documents")
    query = """
    UPDATE budget_control
    SET unrevisioned_name = name
    WHERE unrevisioned_name IS NULL
    """
    env.cr.execute(query)
