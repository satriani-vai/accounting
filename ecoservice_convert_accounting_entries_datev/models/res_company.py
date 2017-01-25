# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the root directory of this module for full copyright and licensing details.


from openerp.osv import fields, osv
from openerp.tools.translate import _
from datetime import datetime

class ResCompany(osv.osv):
    _inherit = 'res.company'

    _columns = {
                'entries_converted': fields.boolean(string='Entries converted'),
                'entries_convert_msg': fields.text(string='Convert message')
    }

    def convert_account_moves(self, cr, uid, ids, context):
        msg = list()
        account_move_obj = self.pool.get('account.move')
        account_journal_obj = self.pool.get('account.journal')

        for company in self.browse(cr, uid, ids, context=context):
            journal_ids = account_journal_obj.search(cr, uid, [('company_id', '=', company.id)], context=context)
            for journal in account_journal_obj.browse(cr, uid, journal_ids, context=context):
                journal_update_posted_pre = journal.update_posted
                if not journal.update_posted:
                    account_journal_obj.write(cr, uid, journal.id, {'update_posted': True}, context=context)
                if journal.update_posted:
                    move_ids = account_move_obj.search(cr, uid, [('state', '=', 'posted'),
                                                                 ('company_id', '=', company.id),
                                                                 ('journal_id', '=', journal.id)], context=context)

                    for move in account_move_obj.browse(cr, uid, move_ids, context=context):
                        try:
                            account_move_obj.button_cancel(cr, uid, [move.id], context=context)
                            account_move_obj.post(cr, uid, [move.id], context=context)
                        except Exception as E:
                            msg.append(_(u'Exception: {move} --> {exception}\n').format(move=move.name, exception=E[1]))

                if not journal_update_posted_pre:
                    account_journal_obj.write(cr, uid, journal.id, {'update_posted': journal_update_posted_pre}, context=context)

            if msg:
                new_msg = u'{date}\n{msg}\n'.format(date=str(datetime.today().date()), msg='\n'.join(msg))
            else:
                new_msg = u'{date}\nOK!\n'.format(date=str(datetime.today().date()))

            self.write(cr, uid, company.id, {'entries_converted': True,
                                             'entries_convert_msg': u'{pre}\n{msg}'.format(pre=company.entries_convert_msg or '', msg=new_msg)
                                            },
                                            context=context)



