# Copyright 2021 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from psycopg2 import sql

from odoo import models

from odoo.addons.report_xlsx_helper.report.report_xlsx_format import (
    FORMATS,
    XLS_HEADERS,
)


class BudgetConsumptionExportXslx(models.AbstractModel):
    _name = "report.budget.consumption.xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Budget Export xlsx"

    def _get_export_budget_vals(self, obj):
        return {
            "0010_date": {
                "header": {"value": "Date"},
                "data": {
                    "value": self._render("date"),
                    "format": FORMATS["format_tcell_date_left"],
                },
                "width": 15,
            },
            "0020_type": {
                "header": {"value": "Type"},
                "data": {
                    "value": self._render("type"),
                },
                "width": 10,
            },
            "0030_analytic_period": {
                "header": {"value": "Analytic Period"},
                "data": {
                    "value": self._render("analytic_period"),
                },
                "width": 15,
            },
            "0040_analytic_account_code": {
                "header": {"value": "Analytic Code"},
                "data": {
                    "value": self._render("analytic_code"),
                },
                "width": 10,
            },
            "0050_analytic_account": {
                "header": {"value": "Analytic Account"},
                "data": {
                    "value": self._render("analytic_account"),
                },
                "width": 20,
            },
            "0060_kpi": {
                "header": {"value": "KPI"},
                "data": {
                    "value": self._render("kpi_name"),
                },
                "width": 15,
            },
            "0070_account_code": {
                "header": {"value": "Account Code"},
                "data": {
                    "value": self._render("account_code"),
                },
                "width": 15,
            },
            "0080_account_name": {
                "header": {"value": "Account Name"},
                "data": {
                    "value": self._render("account_name"),
                },
                "width": 20,
            },
            "0090_doc_name": {
                "header": {"value": "Reference"},
                "data": {
                    "value": self._render("doc_name"),
                },
                "width": 20,
            },
            "0100_doc_ref_next": {
                "header": {"value": "Uncommit From"},
                "data": {
                    "value": self._render("doc_ref_next"),
                },
                "width": 15,
            },
            "0110_amount": {
                "header": {"value": "Amount Commit"},
                "data": {
                    "value": self._render("amount"),
                    "format": FORMATS["format_tcell_amount_right"],
                },
                "width": 15,
            },
            "0120_name": {
                "header": {"value": "Description"},
                "data": {
                    "value": self._render("name"),
                },
                "width": 25,
            },
            "0130_budget_type": {
                "header": {"value": "Budget Type"},
                "data": {
                    "value": self._render("budget_type"),
                },
                "width": 15,
            },
            "0140_project": {
                "header": {"value": "Project"},
                "data": {
                    "value": self._render("project"),
                },
                "width": 30,
            },
            "0150_parent_project": {
                "header": {"value": "Parent Project"},
                "data": {
                    "value": self._render("parent_project"),
                },
                "width": 30,
            },
            "0160_department": {
                "header": {"value": "Department"},
                "data": {
                    "value": self._render("department"),
                },
                "width": 30,
            },
            "0170_note": {
                "header": {"value": "Note"},
                "data": {
                    "value": self._render("note"),
                },
                "width": 15,
            },
        }

    def _get_ws_params(self, wb, data, obj):
        export_budget_template = self._get_export_budget_vals(obj)
        ws_params = {
            "ws_name": "Budget Consumption Excel Report",
            "generate_ws_method": "_export_budget_report",
            "title": "Budget Consumption Report",
            "wanted_list": [x for x in sorted(export_budget_template.keys())],
            "col_specs": export_budget_template,
        }

        return [ws_params]

    def _get_render_space(self, result):
        # Find type
        amount_type = [
            x["type"][1]
            for x in self.env["budget.monitor.report"]._get_consumed_sources()
            if x["type"][0] == result["amount_type"]
        ]
        # Find period on analytic
        BudgetPeriod = self.env["budget.period"]
        budget_period = BudgetPeriod.browse(result["budget_period_id"])
        # Find account
        AccountAccount = self.env["account.account"]
        account = AccountAccount.browse(result["account_id"])
        # Find analytic tag dimension
        AnalyticTag = self.env["account.analytic.tag"]
        budget_type = AnalyticTag.browse(result["x_dimension_budget_type"])
        return {
            "date": result["date"] or "",
            "type": amount_type[0] or "",
            "analytic_period": budget_period.name or "",
            "activity": result["activity_name"] or "",
            "kpi_name": result["kpi_name"] or "",
            "account_code": account.code or "",
            "account_name": account.name or "",
            "analytic_account": result["analytic_name"] or "",
            "analytic_code": result["analytic_code"] or "",
            "doc_name": result["doc_name"] or "",
            "doc_ref_next": result["doc_ref_next"] or "",
            "amount": result["debit"] or -1 * result["credit"] or 0,
            "name": result["name"] or "",
            "budget_type": budget_type.name or "",
            "project": result["project_name"] or "",
            "parent_project": result["parent_project_name"] or "",
            "department": result["department_name"] or "",
            "operating_unit": result["ou_name"] or "",
            "fund": result["fund_name"] or "",
            "fund_group": result["fund_group_name"] or "",
            "note": result["note"] or "",
        }

    def _get_header_data_list(self, obj):
        amount_type = [
            x["type"][1]
            for x in self.env["budget.monitor.report"]._get_consumed_sources()
            if x["type"][0] == obj.amount_type
        ]
        return [
            ("Type", obj.amount_type and amount_type[0] or "-"),
            ("Date From", obj.date_from and obj.date_from.strftime("%d/%m/%Y") or "-"),
            ("Date To", obj.date_to and obj.date_to.strftime("%d/%m/%Y") or "-"),
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

    def _write_ws_lines(self, row_pos, ws, ws_params, results):
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
                render_space=self._get_render_space(result),
                default_format=FORMATS["format_tcell_left"],
            )
        return row_pos

    def _write_ws_footer(self, row_pos, ws, results):
        ws.merge_range(row_pos, 0, row_pos, 11, "")
        ws.write_row(row_pos, 0, [""], FORMATS["format_theader_blue_right"])
        amount_total = sum(
            result["debit"] or -1 * result["credit"] for result in results
        )
        ws.write_row(
            row_pos,
            12,
            [amount_total],
            FORMATS["format_theader_blue_amount_right"],
        )
        ws.merge_range(row_pos, 13, row_pos, 20, "")
        ws.write_row(row_pos, 13, [""], FORMATS["format_theader_blue_right"])
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
        row_pos = self._write_ws_lines(row_pos, ws, ws_params, results)
        row_pos = self._write_ws_footer(row_pos, ws, results)
        return row_pos

    def _get_domain(self, obj):
        domain = []
        self.env["account.analytic.tag"].search([])
        if obj.date_from:
            domain.append("a.date >= '{}'".format(obj.date_from))
        if obj.date_to:
            domain.append("a.date <= '{}'".format(obj.date_to))
        if obj.analytic_account_ids:
            analytic = (
                len(obj.analytic_account_ids.ids) != 1
                and "in {}".format(tuple(obj.analytic_account_ids.ids))
                or "= {}".format(obj.analytic_account_ids.id)
            )
            domain.append("a.analytic_account_id {}".format(analytic))
        return domain

    def _get_domain_where_query(self, obj):
        domain = self._get_domain(obj)
        # convert domain list to string
        domain_str = domain and " and ".join(domain) or ""
        domain_str = domain_str and "WHERE {}".format(domain_str) or ""
        return domain_str

    def _get_doc_partner_table(self, budget_table):
        """Expense, Advance, Clearing use employee field.
        We need to change employee to partner
        """
        doc_partner_table = "res_partner"
        if budget_table in ("advance_budget_move", "expense_budget_move"):
            doc_partner_table = "hr_employee"
        return doc_partner_table

    def _get_doc_partner_field(self, budget_table):
        doc_partner_field = "b.partner_id"
        if budget_table in ("advance_budget_move", "expense_budget_move"):
            doc_partner_field = "b.employee_id"
        if budget_table == "purchase_request_budget_move":
            doc_partner_field = "ru.partner_id"
        if budget_table == "account_budget_move":
            doc_partner_field = "aml.partner_id"
        return doc_partner_field

    def _get_select_addon(self, budget_table):
        """Addon field reference and next commit
        - AV > CAV
        - CAV or EX > Move
        - PR > PO
        - Actual (no next)
        - CT > Move
        - PO > Move
        """
        select_addon = ""
        if budget_table == "advance_budget_move":
            select_addon = """
                exp.name,
                CASE WHEN cav.number is not null THEN cav.number
                ELSE am.name
                END as doc_ref_next
            """
        if budget_table == "expense_budget_move":
            select_addon = "exp.name, am.name as doc_ref_next"
        if budget_table == "purchase_request_budget_move":
            select_addon = "prl.name, po.name as doc_ref_next"
        if budget_table == "account_budget_move":
            select_addon = "aml.name, null::char as doc_ref_next"
        if budget_table == "contract_budget_move":
            select_addon = "b.name, am.name as doc_ref_next"
        if budget_table == "purchase_budget_move":
            select_addon = "pol.name, am.name as doc_ref_next"
        return select_addon

    def _get_table_addon(self, budget_table):
        table_addon = ""
        if budget_table == "advance_budget_move":
            table_addon = """
                LEFT OUTER JOIN hr_expense exp on exp.id = a.expense_id
                LEFT OUTER JOIN hr_expense ex_cav on ex_cav.id = a.clearing_id
                LEFT OUTER JOIN hr_expense_sheet cav on cav.id = ex_cav.sheet_id
                LEFT OUTER JOIN account_move_line aml on aml.id = a.move_line_id
                LEFT OUTER JOIN account_move am on am.id = aml.move_id
            """
        if budget_table == "expense_budget_move":
            table_addon = """
                LEFT OUTER JOIN hr_expense exp on exp.id = a.expense_id
                LEFT OUTER JOIN account_move_line aml on aml.id = a.move_line_id
                LEFT OUTER JOIN account_move am on am.id = aml.move_id
            """
        if budget_table == "purchase_request_budget_move":
            table_addon = """
                LEFT OUTER JOIN res_users ru on ru.id = b.requested_by
                LEFT OUTER JOIN purchase_request_line prl
                    on prl.id = a.purchase_request_line_id
                LEFT OUTER JOIN purchase_order_line pol
                    on pol.id = a.purchase_line_id
                LEFT OUTER JOIN purchase_order po
                    on po.id = pol.order_id
            """
        if budget_table == "account_budget_move":
            table_addon = (
                "LEFT OUTER JOIN account_move_line aml on aml.id = a.move_line_id"
            )
        if budget_table == "contract_budget_move":
            table_addon = """
                LEFT OUTER JOIN account_move am on am.id = a.move_id
            """
        if budget_table == "purchase_budget_move":
            table_addon = """
                LEFT OUTER JOIN purchase_order_line pol
                    on pol.id = a.purchase_line_id
                LEFT OUTER JOIN account_move am on am.id = a.move_id
            """
        return table_addon

    def _get_budget_consumed(self, consumed_sources, domain_str):
        sql_select = {}
        for source in consumed_sources:
            amount_type = source["type"][0]  # i.e., 8_actual
            budget_table = source["budget_move"][0]  # i.e., account_budget_move
            doc_table = source["source_doc"][0]  # i.e., account_move
            doc_field = source["source_doc"][1]  # i.e., move_id
            doc_partner_table = self._get_doc_partner_table(budget_table)
            doc_partner_field = self._get_doc_partner_field(budget_table)
            select_addon = self._get_select_addon(budget_table)
            table_addon = self._get_table_addon(budget_table)

            sql_select[
                amount_type
            ] = """
                SELECT {}000000000 + a.id as id, '{}' as amount_type, a.reference as doc_name,
                {}, a.debit, a.credit, c.name as partner, a.date, a.account_id,
                aa.code as analytic_code, aa.name as analytic_name,
                aa.budget_period_id as budget_period_id,
                ba.name as activity_name, kpi.name as kpi_name,
                pj.name as project_name, pj.parent_project_name,
                d.name as department_name, ou.name as ou_name,
                f.name as fund_name, fg.name as fund_group_name,
                a.x_dimension_budget_type,
                a.note
                FROM {} a
                LEFT OUTER JOIN {} b on b.id = a.{}
                {}
                LEFT OUTER JOIN {} c on c.id = {}
                LEFT OUTER JOIN budget_activity ba on ba.id = a.activity_id
                LEFT OUTER JOIN budget_kpi kpi
                    on kpi.id = ba.kpi_id
                LEFT OUTER JOIN account_analytic_account aa
                    on aa.id = a.analytic_account_id
                LEFT OUTER JOIN res_project pj on pj.id = aa.project_id
                LEFT OUTER JOIN hr_department d on d.id = a.department_id
                LEFT OUTER JOIN operating_unit ou on ou.id = a.operating_unit_id
                LEFT OUTER JOIN budget_source_fund f on f.id = a.fund_id
                LEFT OUTER JOIN budget_source_fund_group fg on fg.id = a.fund_group_id
                {}
                """.format(
                amount_type[:1],
                amount_type,
                select_addon,
                budget_table,
                doc_table,
                doc_field,
                table_addon,
                doc_partner_table,
                doc_partner_field,
                domain_str,
            )
        return sql_select

    def _get_query_budget_report(self, obj):
        domain_str = self._get_domain_where_query(obj)
        consumed_sources = self.env["budget.monitor.report"]._get_consumed_sources()
        if obj.amount_type:
            consumed_sources = [
                x for x in consumed_sources if x["type"][0] == obj.amount_type
            ]

        sql_select = self._get_budget_consumed(consumed_sources, domain_str)
        query = [sql_select.get(x["type"][0]) for x in consumed_sources]
        all_query = "UNION".join(query)
        self.env.cr.execute(
            sql.SQL(
                """
                SELECT *
                FROM ({}) consumption
                ORDER BY consumption.amount_type,
                    consumption.doc_name, consumption.date
            """.format(
                    all_query
                )
            )
        )
        return self.env.cr.dictfetchall()
