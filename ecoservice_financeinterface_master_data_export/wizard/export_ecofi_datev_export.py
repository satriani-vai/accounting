# -*- encoding: utf-8 -*-
##############################################################################
#    ecoservice_financeinterface_datev_export
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
#    This program based on Odoo.
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
##############################################################################
""" The export_ecofi_buchungsaetze module provides the wizard object the user calls when exporting
"""
from odoo.osv import fields, osv
import datetime
from odoo.tools.translate import _


class datev_reference_data_export(osv.osv_memory):
    _name = 'datev.reference.data.export'
    _description = 'Reference Data Export'
    """ OSV Memory object the user calls when exporting
    """
    _columns = {
        'export_format_id': fields.many2one('ecofi.datev.formate', 'Export Format', required=True),
        'file_export': fields.binary(string='Export File'),
        'file_export_name': fields.char('Export Filename', size=128),
        'file_export_log': fields.text('Export Log', readonly=True),
    }


    def startexport(self, cr, uid, ids, context=None):
        """ Start the export through the wizard

        :param cr: the current row, from the database cursor
        :param uid: the current user’s ID for security checks
        :param data: the data dictionary
        :param context: context arguments, like lang, time zone
        """
        exportecofi = self.pool.get('ecofi.datev.formate')
        for export in self.browse(cr, uid, ids, context=context):
            export_file = exportecofi.generate_export(cr, uid, [export.export_format_id.id], context=context)
            filename = "%s_%s.csv" % (export.export_format_id.name, datetime.datetime.now().strftime('%d%m%y'))
            self.write(cr, uid, [export.id], {'file_export': export_file['file'],
                                              'file_export_log': export_file['log'],
                                              'file_export_name': filename
                                              })
        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'ecoservice_financeinterface_datev_export', 'datev_export_view')[1]

        return {
                'res_id': ids[0],
                'view_id': [view_id],
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'datev.reference.data.export',
                'type': 'ir.actions.act_window',
                'context': {'step': 'just_anonymized'},
                'target': 'new',
        }
datev_reference_data_export()
