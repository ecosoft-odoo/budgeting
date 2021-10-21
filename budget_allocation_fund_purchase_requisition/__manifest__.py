# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Budget Allocation Fund Purchase Requisition",
    "summary": "Budget module to pass fund, PR -> Tender -> PO",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": [
        "budget_allocation_fund_purchase_request",
        "budget_allocation_fund_purchase",
        "purchase_request_to_requisition",
    ],
    "data": [
        "wizard/purchase_request_line_make_purchase_requisition_view.xml",
        "views/purchase_requisition_view.xml",
    ],
    "installable": True,
    "auto_install": True,
    "maintainers": ["newtratip"],
    "development_status": "Alpha",
}
