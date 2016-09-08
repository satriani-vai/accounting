# -*- encoding: utf-8 -*-
""" The export_ecofi_buchungsaetze module provides the wizard object the user calls when exporting
"""
##############################################################################
#    ecoservice_financeinterface
#    Copyright (c) 2013 ecoservice GbR (<http://www.ecoservice.de>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    This program based on OpenERP.
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
##############################################################################
import time
from openerp.osv import osv, fields


class export_ecofi(osv.osv_memory):
    _name = 'export.ecofi'
    _description = 'Financeexport'
    """ OSV Memory object the user calls when exporting
    """

    def _get_default_journal(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, [uid], context)[0]
        journal_ids = []
        if user.company_id.finance_interface:
            for journal in user.company_id.journal_ids:
                journal_ids.append(journal.id)
        return journal_ids

    def _get_default_vorlauf(self, cr, uid, context={}):
        vorlauf = False
        if 'active_model' in context and 'active_id' in context:
            if context['active_model'] == 'ecofi':
                vorlauf = context['active_id']
        return vorlauf

    def _get_export_types(self, cr, uid, context=None):
        """Method that can be used by other Modules to add their export type to the selection of possible export types

        :param cr: the database cursor
        :param uid: the current user’s ID for security checks
        :param context: context arguments, like lang, time zone
        """
        return [('date', 'Datum')]

    _columns = {
        'vorlauf_id': fields.many2one('ecofi', 'Vorlauf', readonly=True),
        'journal_id': fields.many2many('account.journal', 'export_ecofi_journal_rel', 'export_ecofi_id', 'journal_id', 'Journal'),
        'export_type': fields.selection(_get_export_types, 'Export Type', required=True),
        'date_from': fields.date('Date From'),
        'date_to': fields.date('Date To'),
    }

    _defaults = {
        'vorlauf_id': lambda self, cr, uid, c: self._get_default_vorlauf(cr, uid, context=c),
        'journal_id': lambda self, cr, uid, c: self._get_default_journal(cr, uid, context=c),
        'export_type': 'date',
        'date_from': lambda *a: time.strftime('%Y-%m-01'),
        'date_to': lambda *a: time.strftime('%Y-%m-%d'),
    }

    def startexport(self, cr, uid, ids, context=None):
        """ Start the export through the wizard

        :param cr: the current row, from the database cursor
        :param uid: the current user’s ID for security checks
        :param data: the data dictionary
        :param context: context arguments, like lang, time zone
        """
        exportecofi = self.pool.get('ecofi')
        for export in self.browse(cr, uid, ids, context):
            thisvorlauf = export.vorlauf_id and export.vorlauf_id.id or False
            date_from = False
            date_to = False
            if export.export_type == 'date':
                date_from = export.date_from
                date_to = export.date_to
            journal_ids = []
            for journal in export.journal_id:
                journal_ids.append(journal.id)
            vorlauf = exportecofi.ecofi_buchungen(cr, uid, journal_ids=journal_ids, vorlauf_id=thisvorlauf, context=context, date_from=date_from, date_to=date_to)
        return {
            'name': 'Financial Export Invoices',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'ecofi',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': vorlauf,
        }
export_ecofi()
