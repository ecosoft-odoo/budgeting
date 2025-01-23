# Copyright 2021 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from psycopg2 import sql

from odoo import models

from odoo.addons.report_xlsx_helper.report.report_xlsx_format import (
    FORMATS,
    XLS_HEADERS,
)


class BudgetReportExportXslx(models.AbstractModel):
    _name = "report.budget.report.wizard.xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Budget Export xlsx"

    def _get_export_budget_vals(self, obj):
        return {
            "0010_budget_type": {
                "header": {"value": "Budget Type"},
                "data": {
                    "value": self._render("budget_type"),
                },
                "width": 18,
            },
            "0020_analytic_budget_period": {
                "header": {"value": "Analytic Budget Period"},
                "data": {
                    "value": self._render("analytic_budget_period"),
                },
                "width": 25,
            },
            "0030_ref_analytic_account": {
                "header": {"value": "Analytic Code"},
                "data": {
                    "value": self._render("analytic_account_code"),
                },
                "width": 15,
            },
            "0040_analytic_account": {
                "header": {"value": "Analytic Account"},
                "data": {
                    "value": self._render("analytic_account_name"),
                },
                "width": 25,
            },
            "0050_parent_project": {
                "header": {"value": "Parent Project"},
                "data": {
                    "value": self._render("parent_project"),
                },
                "width": 20,
            },
            "0060_project_code": {
                "header": {"value": "Project Code"},
                "data": {
                    "value": self._render("project_code"),
                },
                "width": 15,
            },
            "0070_project": {
                "header": {"value": "Project"},
                "data": {
                    "value": self._render("project_name"),
                },
                "width": 25,
            },
            "0080_department_code": {
                "header": {"value": "Department Code"},
                "data": {
                    "value": self._render("department_code"),
                },
                "width": 15,
            },
            "0090_department": {
                "header": {"value": "Department"},
                "data": {
                    "value": self._render("department_name"),
                },
                "width": 20,
            },
            "0100_estimated_amount": {
                "header": {"value": "Estimated Amount"},
                "data": {
                    "value": self._render("estimated_amount"),
                    "format": FORMATS["format_tcell_amount_right"],
                },
                "width": 20,
            },
            "0110_budget_amount": {
                "header": {"value": "Budget Amount"},
                "data": {
                    "value": self._render("budget_amount"),
                    "format": FORMATS["format_tcell_amount_right"],
                },
                "width": 15,
            },
            "16_pr_commit": {
                "header": {"value": "PR Commit"},
                "data": {
                    "value": self._render("pr_commit"),
                    "format": FORMATS["format_tcell_amount_right"],
                },
                "width": 15,
            },
            "17_po_commit": {
                "header": {"value": "PO Commit"},
                "data": {
                    "value": self._render("po_commit"),
                    "format": FORMATS["format_tcell_amount_right"],
                },
                "width": 15,
            },
            "18_ct_commit": {
                "header": {"value": "CT Commit"},
                "data": {
                    "value": self._render("ct_commit"),
                    "format": FORMATS["format_tcell_amount_right"],
                },
                "width": 15,
            },
            "19_av_commit": {
                "header": {"value": "AV Commit"},
                "data": {
                    "value": self._render("av_commit"),
                    "format": FORMATS["format_tcell_amount_right"],
                },
                "width": 15,
            },
            "20_ex_commit": {
                "header": {"value": "EX Commit"},
                "data": {
                    "value": self._render("ex_commit"),
                    "format": FORMATS["format_tcell_amount_right"],
                },
                "width": 15,
            },
            "21_actual": {
                "header": {"value": "Actual"},
                "data": {
                    "value": self._render("actual_commit"),
                    "format": FORMATS["format_tcell_amount_right"],
                },
                "width": 15,
            },
            "22_total_amount": {
                "header": {"value": "Total"},
                "data": {
                    "value": self._render("total_amount"),
                    "format": FORMATS["format_tcell_amount_right"],
                },
                "width": 15,
            },
            "23_total_available": {
                "header": {"value": "Available"},
                "data": {
                    "value": self._render("total_available"),
                    "format": FORMATS["format_tcell_amount_right"],
                },
                "width": 15,
            },
        }

    def _get_ws_params(self, wb, data, obj):
        export_budget_template = self._get_export_budget_vals(obj)
        ws_params = {
            "ws_name": "Budget Excel Report",
            "generate_ws_method": "_export_budget_report",
            "title": "Budget Report",
            "wanted_list": [x for x in sorted(export_budget_template.keys())],
            "col_specs": export_budget_template,
        }

        return [ws_params]

    def _filter_commitment(self, obj, result):
        obj_filter = obj.filtered(
            lambda l: l.analytic_account_id.name == result["analytic_account_name"]
            and l.fund_id.name == result["fund_name"]
            and l.x_dimension_budget_type.id == result["x_dimension_budget_type"]
        )
        return obj_filter

    def _get_domain_budget_move(self, obj):
        dom = []
        if obj.date_from:
            dom.append(("date", ">=", obj.date_from))
        if obj.date_to:
            dom.append(("date", "<=", obj.date_to))
        return dom

    def _get_amount_consumtion(self, results, obj):
        pr_total = (
            po_total
        ) = (
            av_total
        ) = (
            ct_total
        ) = (
            ex_total
        ) = (
            actual_total
        ) = (
            total_amount
        ) = total_available = total_budget_amount = total_estimated_amount = 0.0
        PurchaseRequestBudgetMove = self.env["purchase.request.budget.move"]
        PurchaseBudgetMove = self.env["purchase.budget.move"]
        ContractBudgetMove = self.env["contract.budget.move"]
        AdvanceBudgetMove = self.env["advance.budget.move"]
        ExpenseBudgetMove = self.env["expense.budget.move"]
        ActualBudgetMove = self.env["account.budget.move"]
        dom_budget_move = self._get_domain_budget_move(obj)
        for result in results:
            pr_budget_move = PurchaseRequestBudgetMove.search(dom_budget_move)
            po_budget_move = PurchaseBudgetMove.search(dom_budget_move)
            ct_budget_move = ContractBudgetMove.search(dom_budget_move)
            av_budget_move = AdvanceBudgetMove.search(dom_budget_move)
            ex_budget_move = ExpenseBudgetMove.search(dom_budget_move)
            actual_budget_move = ActualBudgetMove.search(dom_budget_move)
            pr_budget_move = self._filter_commitment(pr_budget_move, result)
            pr_commit = sum(pr_budget_move.mapped("debit")) - sum(
                pr_budget_move.mapped("credit")
            )
            po_budget_move = self._filter_commitment(po_budget_move, result)
            po_commit = sum(po_budget_move.mapped("debit")) - sum(
                po_budget_move.mapped("credit")
            )
            ct_budget_move = self._filter_commitment(ct_budget_move, result)
            ct_commit = sum(ct_budget_move.mapped("debit")) - sum(
                ct_budget_move.mapped("credit")
            )
            av_budget_move = self._filter_commitment(av_budget_move, result)
            av_commit = sum(av_budget_move.mapped("debit")) - sum(
                av_budget_move.mapped("credit")
            )
            ex_budget_move = self._filter_commitment(ex_budget_move, result)
            ex_commit = sum(ex_budget_move.mapped("debit")) - sum(
                ex_budget_move.mapped("credit")
            )
            actual_budget_move = self._filter_commitment(actual_budget_move, result)
            actual_commit = sum(actual_budget_move.mapped("debit")) - sum(
                actual_budget_move.mapped("credit")
            )
            consumtion_commit = (
                actual_commit
                + pr_commit
                + po_commit
                + ct_commit
                + av_commit
                + ex_commit
            )

            pr_total += pr_commit
            po_total += po_commit
            ct_total += ct_commit
            av_total += av_commit
            ex_total += ex_commit
            actual_total += actual_commit
            total_amount += consumtion_commit
            total_available += result["released_amount"] - consumtion_commit
            total_budget_amount += result["released_amount"]
            total_estimated_amount += result["estimated_amount"]
        return (
            pr_total,
            po_total,
            ct_total,
            av_total,
            ex_total,
            actual_total,
            total_amount,
            total_available,
            total_budget_amount,
            total_estimated_amount,
        )

    def _get_render_space(self, result, obj):
        # Find analytic tag dimension
        AnalyticTag = self.env["account.analytic.tag"]
        budget_type = AnalyticTag.browse(result["x_dimension_budget_type"])
        # Find period on analytic
        BudgetPeriod = self.env["budget.period"]
        analytic_budget_period = BudgetPeriod.browse(
            result["analytic_budget_period_id"]
        )
        dom_budget_move = self._get_domain_budget_move(obj)
        pr_budget_move = self.env["purchase.request.budget.move"].search(
            dom_budget_move
        )
        pr_budget_move = self._filter_commitment(pr_budget_move, result)
        pr_commit = sum(pr_budget_move.mapped("debit")) - sum(
            pr_budget_move.mapped("credit")
        )

        po_budget_move = self.env["purchase.budget.move"].search(dom_budget_move)
        po_budget_move = self._filter_commitment(po_budget_move, result)
        po_commit = sum(po_budget_move.mapped("debit")) - sum(
            po_budget_move.mapped("credit")
        )
        ct_budget_move = self.env["contract.budget.move"].search(dom_budget_move)
        ct_budget_move = self._filter_commitment(ct_budget_move, result)
        ct_commit = sum(ct_budget_move.mapped("debit")) - sum(
            ct_budget_move.mapped("credit")
        )
        av_budget_move = self.env["advance.budget.move"].search(dom_budget_move)
        av_budget_move = self._filter_commitment(av_budget_move, result)
        av_commit = sum(av_budget_move.mapped("debit")) - sum(
            av_budget_move.mapped("credit")
        )

        ex_budget_move = self.env["expense.budget.move"].search(dom_budget_move)
        ex_budget_move = self._filter_commitment(ex_budget_move, result)
        ex_commit = sum(ex_budget_move.mapped("debit")) - sum(
            ex_budget_move.mapped("credit")
        )

        actual_budget_move = self.env["account.budget.move"].search(dom_budget_move)
        actual_budget_move = self._filter_commitment(actual_budget_move, result)
        actual_commit = sum(actual_budget_move.mapped("debit")) - sum(
            actual_budget_move.mapped("credit")
        )

        total_amount = (
            actual_commit + pr_commit + po_commit + ct_commit + av_commit + ex_commit
        )
        total_available = result["released_amount"] - total_amount

        analytic_account_id = self.env["account.analytic.account"].browse(
            result["analytic_id"]
        )
        return {
            "budget_type": budget_type.name,
            "analytic_budget_period": analytic_budget_period.name,
            "analytic_account_code": result["analytic_account_code"],
            "analytic_account_name": result["analytic_account_name"],
            "operating_unit_code": analytic_account_id.operating_unit_ids.code,
            "operating_unit_name": analytic_account_id.operating_unit_ids.name,
            "parent_project": result["parent_project_name"],
            "project_code": result["project_code"],
            "project_name": result["project_name"],
            "department_code": result["department_code"],
            "department_name": result["department_name"],
            "fund_name": result["fund_name"],
            "fund_group_name": result["fund_group_name"],
            "estimated_amount": result["estimated_amount"],
            "budget_amount": result["released_amount"],
            "actual_commit": actual_commit,
            "pr_commit": pr_commit,
            "po_commit": po_commit,
            "ct_commit": ct_commit,
            "av_commit": av_commit,
            "ex_commit": ex_commit,
            "total_amount": total_amount,
            "total_available": total_available,
        }

    def _get_header_data_list(self, obj):
        return [
            ("Budget Period", obj.budget_period_id.name or "-"),
            ("Date From", obj.date_from and obj.date_from.strftime("%d/%m/%Y") or "-"),
            ("Date To", obj.date_to and obj.date_to.strftime("%d/%m/%Y") or "-"),
            # (
            #     "Budget Type",
            #     obj.budget_type_ids and ", ".join(obj.budget_type_ids.mapped("name")) or "-",
            # ),
            ("Fund", obj.fund_ids and ", ".join(obj.fund_ids.mapped("name")) or "-"),
            (
                "Analytic",
                obj.analytic_account_ids
                and ", ".join(obj.analytic_account_ids.mapped("name"))
                or "-",
            ),
        ]

    def _write_ws_header(self, row_pos, ws, data_list):
        for data in data_list:
            ws.write_row(row_pos, 0, [data[0]], FORMATS["format_theader_blue_left"])
            ws.merge_range(row_pos, 1, row_pos, 7, "")
            ws.write_row(row_pos, 1, [data[1]])
            row_pos += 1
        return row_pos + 1

    def _write_ws_lines(self, row_pos, ws, ws_params, results, obj):
        row_pos = self._write_line(
            ws,
            row_pos,
            ws_params,
            col_specs_section="header",
            default_format=FORMATS["format_theader_blue_center"],
        )
        ws.freeze_panes(row_pos, 0)
        for result in results:
            row_pos = self._write_line(
                ws,
                row_pos,
                ws_params,
                col_specs_section="data",
                render_space=self._get_render_space(result, obj),
                default_format=FORMATS["format_tcell_left"],
            )
        return row_pos

    def _write_ws_footer(self, row_pos, ws, results, obj):
        (
            pr_total,
            po_total,
            ct_total,
            av_total,
            ex_total,
            actual_total,
            total_amount,
            total_available,
            total_budget_amount,
            total_estimated_amount,
        ) = self._get_amount_consumtion(results, obj)
        ws.merge_range(row_pos, 0, row_pos, 12, "")
        ws.write_row(row_pos, 0, [""], FORMATS["format_theader_blue_right"])
        ws.write_row(
            row_pos,
            13,
            [
                total_estimated_amount,
                total_budget_amount,
                pr_total,
                po_total,
                ct_total,
                av_total,
                ex_total,
                actual_total,
                total_amount,
                total_available,
            ],
            FORMATS["format_theader_blue_amount_right"],
        )
        return row_pos

    def _export_budget_report(self, workbook, ws, ws_params, data, obj):
        ws.set_portrait()
        ws.fit_to_pages(1, 0)
        ws.set_header(XLS_HEADERS["xls_headers"]["standard"])
        ws.set_footer(XLS_HEADERS["xls_footers"]["standard"])
        self._set_column_width(ws, ws_params)
        row_pos = 0
        header_data_list = self._get_header_data_list(obj)
        results = self._get_query_budget_report(obj)
        row_pos = self._write_ws_title(ws, row_pos, ws_params, merge_range=True)
        row_pos = self._write_ws_header(row_pos, ws, header_data_list)
        row_pos = self._write_ws_lines(row_pos, ws, ws_params, results, obj)
        row_pos = self._write_ws_footer(row_pos, ws, results, obj)
        return row_pos

    def _get_budget_period(self, date):
        return self.env["budget.period"].search(
            [("bm_date_from", "<=", date), ("bm_date_to", ">=", date)]
        )

    def _get_domain_where_query(self, obj):
        domain = []
        self.env["account.analytic.tag"].search([])
        if obj.budget_period_id:
            domain.append("bal.budget_period_id = {}".format(obj.budget_period_id.id))
        period_from = self._get_budget_period(obj.date_from)
        period_to = self._get_budget_period(obj.date_to)
        periods = period_from + period_to
        if periods:
            if len(tuple(periods.ids)) > 1:
                domain.append("bal.budget_period_id in {}".format(tuple(periods.ids)))
            else:
                domain.append("bal.budget_period_id = {}".format(periods.id))
        # if obj.budget_type_ids:
        #     budget_type = (
        #         len(obj.budget_type_ids.ids) != 1
        #         and "in {}".format(tuple(obj.budget_type_ids.ids))
        #         or "= {}".format(obj.budget_type_ids.id)
        #     )
        #     domain.append("bal.x_dimension_budget_type {}".format(budget_type))
        if obj.analytic_account_ids:
            analytic = (
                len(obj.analytic_account_ids.ids) != 1
                and "in {}".format(tuple(obj.analytic_account_ids.ids))
                or "= {}".format(obj.analytic_account_ids.id)
            )
            domain.append("bal.analytic_account_id {}".format(analytic))
        if obj.fund_ids:
            fund = (
                len(obj.fund_ids.ids) != 1
                and "in {}".format(tuple(obj.fund_ids.ids))
                or "= {}".format(obj.fund_ids.id)
            )
            domain.append("bal.fund_id {}".format(fund))
        # convert domain list to string
        domain_str = domain and " and ".join(domain) or ""
        domain_str = domain_str and "WHERE {}".format(domain_str) or ""
        return domain_str

    def _get_query_budget_report(self, obj):
        domain_str = self._get_domain_where_query(obj)
        self.env.cr.execute(
            sql.SQL(
                """
                SELECT bal.x_dimension_budget_type,
                    CASE WHEN bal.released_amount is not null
                        THEN bal.released_amount
                        ELSE 0
                    END as released_amount,
                    bal.estimated_amount as estimated_amount,
                    aa.id as analytic_id,
                    aa.budget_period_id as analytic_budget_period_id,
                    aa.code as analytic_account_code,
                    aa.name as analytic_account_name,
                    sf.name as fund_name,
                    sf_group.name as fund_group_name,
                    rp.parent_project_name,
                    rp.code as project_code,
                    rp.name as project_name,
                    hr.name as department_name,
                    hr.code as department_code
                FROM budget_allocation_line bal
                LEFT JOIN budget_allocation ba on ba.id = bal.budget_allocation_id
                LEFT JOIN account_analytic_account aa on aa.id = bal.analytic_account_id
                LEFT JOIN res_project rp on rp.id = aa.project_id
                LEFT JOIN hr_department hr on hr.id = aa.department_id
                LEFT JOIN budget_source_fund sf on sf.id = bal.fund_id
                LEFT JOIN budget_source_fund_group sf_group on sf_group.id = sf.fund_group_id
                LEFT JOIN budget_period bp on bp.id = bal.budget_period_id
                {}
                ORDER BY bal.x_dimension_budget_type
            """.format(
                    domain_str
                )
            )
        )
        return self.env.cr.dictfetchall()
