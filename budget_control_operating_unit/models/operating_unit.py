# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, models


class OperatingUnit(models.Model):
    _inherit = "operating.unit"

    def _read(self, fields):
        """ Make sure that user can reverse with other OU """
        if self._context.get("access_sudo", False) or self._context.get(
            "from_review_systray", False
        ):  # support with tier validation
            self = self.sudo()
        return super()._read(fields)

    @api.model
    def name_search(self, name, args=None, operator="ilike", limit=100):
        if self._context.get("access_sudo", False):
            self = self.sudo()
        return super().name_search(name, args, operator, limit)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        if self._context.get("access_sudo", False):
            self = self.sudo()
        return super().search(args, offset, limit, order, count)
