# Copyright 2018 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    _logger.info("Assign unrevisioned_name for existing documents")

    query = """
    update budget_plan
    set unrevisioned_name = name
    where unrevisioned_name is null
    """
    cr.execute(query)
