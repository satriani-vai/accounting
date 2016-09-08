# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright and licensing details.

from openerp import api, models
from openerp.tools.translate import _


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.multi
    def post(self):
        """
        super()
        Updates the name of all line which are combined. The name of the move is not known earlier.
        """
        result = super(AccountMove, self).post()

        for move in self:
            print '+++', self.name
            if move.name is not '/':
                line_ids = move.line_ids.filtered(lambda l: l.name == "is_combined")
                vals = {
                    "name": _(u"Summarized per Invoice: {}").format(move.name),
                }
                line_ids.write(vals)

        return result
