# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models


class OperatingUnit(models.Model):
    _inherit = "operating.unit"

    def _read(self, fields):
        """ Make sure that user can reverse with other OU """
        if self._context.get("access_sudo", False) or self._context.get(
            "from_review_systray", False
        ):  # support with tier validation
            self = self.sudo()
        return super()._read(fields)
