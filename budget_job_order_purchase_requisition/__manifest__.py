# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    "name": "Budget Job Order Purchase Requisition",
    "summary": "Bridget module to pass activity, PR -> Tende -> PO",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/account-budgeting",
    "depends": [
        "budget_job_order_purchase_request",
        "budget_job_order_purchase",
        "budget_control_purchase_requisition",
    ],
    "data": [
        "wizard/purchase_request_line_make_purchase_requisition_view.xml",
        "views/purchase_requisition_view.xml",
    ],
    "installable": True,
    "auto_install": True,
    "maintainers": ["kittiu"],
    "development_status": "Alpha",
}
