# Copyright 2024 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import ast

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class RequestDocument(models.Model):
    _inherit = "request.document"

    budget_move_ids = fields.One2many(
        comodel_name="request.budget.move",
        inverse_name="request_document_id",
    )
    line_data_amount = fields.Text()

    def _budget_field(self):
        return "budget_move_ids"

    def _get_lines_request(self):
        mapping_type = self._get_origin_lines()
        request_line = mapping_type.get(self.request_type, False)
        if not request_line:
            raise UserError(
                self.env._(f"Request type '{self.request_type}' is not implemented.")
            )
        return self.mapped(request_line).with_context(
            alt_budget_move_model="request.budget.move",
            alt_budget_move_field="budget_move_ids",
        )

    def _get_origin_lines(self):
        return {}

    def _get_data_amount(self, request_line):
        return []

    def _get_line_amount_map(self):
        line_amount_map = {}
        if self.line_data_amount:
            list_amount = ast.literal_eval(self.line_data_amount)
            for item in list_amount:
                line_amount_map.update(item)
        return line_amount_map

    def recompute_budget_move(self):
        self.mapped("budget_move_ids").unlink()
        for rec in self:
            if rec.state in ("draft", "cancel"):
                continue

            request_line = rec._get_lines_request().with_context(
                force_commit=True,
                alt_budget_move_model="request.budget.move",
                alt_budget_move_field="budget_move_ids",
            )

            line_amount_map = rec._get_line_amount_map()

            # Commit budget
            for line in request_line:
                if rec.line_data_amount and line.id not in line_amount_map:
                    continue

                ctx = (
                    {"fwd_amount_commit": line_amount_map.get(line.id)}
                    if line.id in line_amount_map
                    else {}
                )
                budget_move = line.with_context(**ctx).commit_budget()
                line.amount_commit = budget_move.debit - budget_move.credit

            # Uncommit budget
            rec.uncommit_request_budget(request_line)

    def close_budget_move(self):
        rounding = self.currency_id.rounding
        budget_moves = self.env["request.budget.move"]
        for rec in self:
            totals = rec.budget_move_ids.read(["debit", "credit"])
            debit = sum(x["debit"] for x in totals)
            credit = sum(x["credit"] for x in totals)
            if float_is_zero(debit - credit, precision_rounding=rounding):
                continue

            request_line = rec._get_lines_request().with_context(
                force_commit=True,
                alt_budget_move_model="request.budget.move",
                alt_budget_move_field="budget_move_ids",
                commit_note=self.env._("Auto adjustment on close budget"),
                adj_commit=True,
            )

            line_amount_map = rec._get_line_amount_map()

            for line in request_line:
                if rec.line_data_amount and line.id not in line_amount_map:
                    continue
                ctx = (
                    {"fwd_amount_commit": line_amount_map.get(line.id)}
                    if line.id in line_amount_map
                    else {}
                )
                budget_move = line.with_context(**ctx).commit_budget(reverse=True)
                budget_moves += budget_move
        return budget_moves

    def uncommit_request_budget(self, request_line):
        return False
