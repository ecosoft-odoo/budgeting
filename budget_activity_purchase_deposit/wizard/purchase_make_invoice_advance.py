# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class PurchaseAdvancePaymentInv(models.TransientModel):
    _inherit = "purchase.advance.payment.inv"

    purchase_deposit_activity_id = fields.Many2one(
        comodel_name="budget.activity",
        string="Deposit Payment Activity",
        index=True,
    )

    def _prepare_advance_purchase_line(self, order, product, tax_ids, amount):
        res = super()._prepare_advance_purchase_line(order, product, tax_ids, amount)
        activity_purchase_deposit = self.env.ref(
            "budget_activity_purchase_deposit.activity_purchase_deposit"
        )
        res.update({"activity_id": activity_purchase_deposit.id})
        return res

    def create_invoices(self):
        IrDefault = self.env["ir.default"].sudo()
        # Create deposit activity and product first time
        activity = self.purchase_deposit_activity_id
        if not activity:
            activity_purchase_deposit = self.env.ref(
                "budget_activity_purchase_deposit.activity_purchase_deposit"
            )
            product = self.env.ref(
                "budget_activity_purchase_deposit.product_purchase_deposit"
            )
            IrDefault.set(
                "purchase.advance.payment.inv",
                "purchase_deposit_activity_id",
                activity_purchase_deposit.id,
            )
            IrDefault.set(
                "purchase.advance.payment.inv",
                "purchase_deposit_product_id",
                product.id,
            )
            self.purchase_deposit_activity_id = activity_purchase_deposit
            self.purchase_deposit_product_id = product
        return super().create_invoices()

    def _prepare_deposit_val(self, order, po_line, amount):
        """Update activity and account on invoice lines"""
        res = super()._prepare_deposit_val(order, po_line, amount)
        ir_property_obj = self.env["ir.property"]
        product = self.env.ref(
            "budget_activity_purchase_deposit.product_purchase_deposit"
        )
        activity = self.purchase_deposit_activity_id
        if activity.id:
            account_id = (
                activity.account_id.id
                or product.property_account_expense_id.id
                or product.categ_id.property_account_expense_categ_id.id
            )
        if not account_id:
            inc_acc = ir_property_obj._get(
                "property_account_expense_categ_id", "product.category"
            )
            account_id = (
                inc_acc and order.fiscal_position_id.map_account(inc_acc).id or False
            )
            if not account_id:
                raise UserError(
                    _(
                        "There is no purchase account defined for this activity: %s."
                        "\nYou may have to install a chart of account from "
                        "Accounting app, settings menu."
                    )
                    % (activity.name,)
                )

        res["invoice_line_ids"][0][2].update(
            {
                "account_id": account_id,
                "activity_id": activity.id,
            }
        )
        return res
