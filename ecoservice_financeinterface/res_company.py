# -*- coding: utf-8 -*-
""" The res_company module extends the original OpenERP res_company objects with different attributes and methods
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

from openerp.osv import orm, fields


class res_company(orm.Model):
    """ Inherits the res.company class and adds methods and attributes
    
    .. automethod:: _finance_interface_selection
    """
    _inherit = 'res.company'

    def _finance_interface_selection(self, cr, uid, context=None):
        """Method that can be used by other Modules to add their interface to the selection of possible export formats 
        the stored value will be used as context variable export_interface
        
        .. seealso:: 
            :class:`ecoservice_financeinterface.ecofi.ecofi.ecofi_buchungen`
        """
        return [('none', 'None')]

    _columns = {
        'finance_interface': fields.selection(_finance_interface_selection, 'Finance Interface'),
        'journal_ids': fields.many2many('account.journal', 'res_company_account_journal',
                                        'res_company_id', 'account_journal_id', 'Journal',
                                        domain="[('company_id', '=', active_id)]"),
    }
