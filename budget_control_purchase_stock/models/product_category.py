# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .res_company import BUDGET_INVENTORY_ACTUAL_SOURCE

BUDGET_INVENTORY_ACTUAL_SOURCE_POLICY = [
    ("company", "Company Default"),
    *BUDGET_INVENTORY_ACTUAL_SOURCE,
]


class ProductCategory(models.Model):
    _inherit = "product.category"

    budget_inventory_actual_source = fields.Selection(
        selection=BUDGET_INVENTORY_ACTUAL_SOURCE_POLICY,
        string="Budget Actual Source",
        default="company",
        company_dependent=True,
        help="Controls when storable products in this category become budget "
        "actual. Company Default uses the current company's default policy. "
        "Services and other non-storable products always use Vendor Bill.",
    )

    def _get_budget_inventory_actual_source(self, company):
        """Resolve this category's company-specific recognition policy."""
        self.ensure_one()
        source = self.with_company(company).budget_inventory_actual_source or "company"
        if source == "company":
            return company.budget_inventory_actual_source
        return source

    @api.constrains("budget_inventory_actual_source", "property_valuation")
    def _check_stock_issue_valuation(self):
        for category in self:
            if (
                category.budget_inventory_actual_source == "stock_issue"
                and category.property_valuation != "real_time"
            ):
                raise ValidationError(
                    self.env._(
                        "Stock Issue budget actual requires automated inventory "
                        "valuation. Category '%(category)s' uses manual valuation.",
                        category=category.display_name,
                    )
                )
