# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Budget Activity - Purchase Requisition",
    "summary": "Bridget module to pass activity, PR -> Tende -> PO",
    "version": "15.0.1.0.0",
    "category": "Accounting",
    "license": "AGPL-3",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/ecosoft-odoo/budgeting",
    "depends": [
        "budget_activity_purchase_request",
        "budget_control_purchase_requisition",
    ],
    "data": [
        "views/purchase_requisition_view.xml",
    ],
    "installable": True,
    "auto_install": True,
    "maintainers": ["kittiu"],
    "development_status": "Alpha",
}
