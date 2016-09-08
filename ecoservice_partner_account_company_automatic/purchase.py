# -*- encoding: utf-8 -*-
##############################################################################
#    ecoservice_partner_account_company_automatic
#    Copyright (c) 2014 ecoservice GbR (<http://www.ecoservice.de>).
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

from openerp.osv import fields, osv

class purchase_order(osv.osv):

    _inherit = "purchase.order"

    def create(self, cr, uid, vals, context=None):
        if context == None:
            context = {}
        res = super(purchase_order, self).create(cr, uid, vals, context=context)
        if vals.get('partner_id'):
            partner = self.pool.get('res.partner').read(cr, uid, vals['partner_id'], ['property_account_payable', 'customer', 'supplier'], context=context)
            if partner and partner['customer'] or partner['supplier']:
                partner_default_id = partner['property_account_payable'][0]
                if partner_default_id:
                    partner_default_property_id = self.pool.get('ir.property').search(cr, uid, ['&',('name','=','property_account_payable'), ('res_id','=',None), ('value_reference','=','account.account,%s' %(partner_default_id))])
                    default_property_id = self.pool.get('ir.property').search(cr, uid, ['&',('name','=','property_account_payable'), ('res_id','=',None)])
                    if default_property_id:
                        if default_property_id == partner_default_property_id:
                            context['type'] = 'payable'
                            self.pool.get('res.partner').create_accounts(cr, uid, [vals['partner_id']], context=context)
        return res