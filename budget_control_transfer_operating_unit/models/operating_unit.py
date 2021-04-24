# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models


class OperatingUnit(models.Model):
    _inherit = "operating.unit"

    def _read(self, fields):
        """ Add permission to read operating unit for do something. """
        if self._context.get("access_sudo", False):
            self = self.sudo()
        return super()._read(fields)
