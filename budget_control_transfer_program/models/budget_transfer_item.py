# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BudgetTransferItem(models.Model):
    _inherit = "budget.transfer.item"

    target_program_id = fields.Many2one(
        comodel_name="res.program",
        string="Target Program",
        compute="_compute_program_id",
        store="True",
        readonly=False,
        required=True,
    )
    target_program_all = fields.Many2many(
        comodel_name="res.program",
        relation="target_transfer_program_rel",
        column1="transfer_id",
        column2="target_program_id",
        compute="_compute_program_all",
        compute_sudo=True,
    )
    source_program_id = fields.Many2one(
        comodel_name="res.program",
        compute="_compute_program_id",
        store="True",
        readonly=False,
        required=True,
    )
    source_program_all = fields.Many2many(
        comodel_name="res.program",
        relation="source_transfer_program_rel",
        column1="transfer_id",
        column2="source_program_id",
        compute="_compute_program_all",
        compute_sudo=True,
    )

    def _get_program(self, budget_control):
        program = budget_control.fund_constraint_ids.mapped("program_id")
        return program

    @api.depends("target_budget_control_id", "source_budget_control_id")
    def _compute_program_id(self):
        for rec in self:
            target_program = rec._get_program(rec.target_budget_control_id)
            source_program = rec._get_program(rec.source_budget_control_id)
            rec.target_program_id = (
                len(target_program) == 1 and target_program.id or False
            )
            rec.source_program_id = (
                len(source_program) == 1 and source_program.id or False
            )

    @api.depends("target_budget_control_id", "source_budget_control_id")
    def _compute_program_all(self):
        for rec in self:
            rec.target_program_all = rec._get_program(
                rec.target_budget_control_id
            )
            rec.source_program_all = rec._get_program(
                rec.source_budget_control_id
            )

    def _check_fund_constraint_ids(self):
        """
        Check fund constraint can cross over constraint.
        i.e.
        Analytic | Program | Fund Constraint | Cross Over
        ==================================================
        A        | A       | A               | B, C
        B        | B       | B               |
        C        | C       | C               |
        ==================================================
        Normally, you can't transfer Program A to other program.
        If you config Fund Constraint cross over Program B, C on A,
        you can transfer Program A to B or C.
        """
        for rec in self:
            source_budget = rec.source_budget_control_id.sudo()
            target_budget = rec.target_budget_control_id.sudo()
            source_fund_constraint_ids = (
                source_budget.fund_constraint_ids.filtered(
                    lambda l: l.program_id == rec.source_program_id
                )
            )
            target_fund_constraint_ids = (
                target_budget.fund_constraint_ids.filtered(
                    lambda l: l.program_id == rec.target_program_id
                )
            )
            cross_constraint = (
                source_fund_constraint_ids.fund_constraint_line.filtered(
                    lambda l: target_fund_constraint_ids.id == l.id
                )
            )
            if not cross_constraint and (
                rec.source_program_id != rec.target_program_id
            ):
                raise UserError(_("Must be the same program."))
