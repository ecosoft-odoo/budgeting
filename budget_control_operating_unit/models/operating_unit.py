# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class OperatingUnit(models.Model):
    _inherit = "operating.unit"

    def _read(self, fields):
        """Make sure that user can transfer/reverse with other OU"""
        if self._context.get("budget_transfer_access_sudo", False) or self._context.get(
            "from_review_systray", False
        ):  # support with tier validation
            self = self.sudo()
        return super()._read(fields)
