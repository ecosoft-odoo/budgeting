# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models

BUDGET_INVENTORY_ACTUAL_SOURCE = [
    ("bill", "Vendor Bill"),
    ("stock_issue", "Stock Issue Valuation"),
]


class ResCompany(models.Model):
    _inherit = "res.company"

    budget_inventory_actual_source = fields.Selection(
        selection=BUDGET_INVENTORY_ACTUAL_SOURCE,
        string="Default Inventory Budget Actual Source",
        required=True,
        default="bill",
        help="Default for storable product categories set to Company Default. "
        "Vendor Bill releases the PO commitment and records actual at bill posting. "
        "Stock Issue keeps the PO commitment through billing, then replaces it with "
        "a stock commitment and records actual from the outgoing valuation entry. "
        "Changes apply only to new transaction snapshots; finish open purchase and "
        "delivery flows before changing this policy. Services and other "
        "non-storable products always use Vendor Bill.",
    )
