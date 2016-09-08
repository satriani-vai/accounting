# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright and licensing details.

from openerp.osv import orm
from openerp.tools.translate import _


class account_move(orm.Model):
    _inherit = "account.move"

    def post(self, cr, uid, ids, context=None):
        """
        super()
        Updates the name of all line which are combined. The name of the move is not known earlier.
        """
        result = super(account_move, self).post(cr, uid, ids, context=context)

        for move in self.browse(cr, uid, ids, context=context):
            if move.name is not '/':
                line_id_list = list()
                for line in move.line_id:
                    if line.name == "is_combined":
                        line_id_list.append(line.id)

                vals = {
                    "name": _(u"Summarized per Invoice: {}").format(move.name),
                }
                self.pool.get('account.move.line').write(cr, uid, line_id_list, vals)

        return result
