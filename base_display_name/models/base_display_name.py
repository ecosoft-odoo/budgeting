# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import models


class BaseDisplayName(models.AbstractModel):
    _name = "base.display.name"
    _description = "Display name (abstract)"

    def _get_display(self, field_display):
        return " ".join(field_display)

    def name_get(self):
        res = []
        for rec in self:
            field_display = [rec[field] for field in self._field_display]
            display_name = rec._get_display(field_display)
            if not display_name:
                display_name = rec.name
            name = "{}".format(display_name)
            res.append((rec.id, name))
        return res
