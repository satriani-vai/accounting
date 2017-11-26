# -*- coding: utf-8 -*-
""" The res_company module extends the original Odoo res_company objects with different attributes and methods
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
#    This program based on Odoo.
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
##############################################################################


from odoo import models, fields


class ResCompany(models.Model):
    """ Inherits the res.company class and adds methods and attributes

    .. automethod:: _finance_interface_selection
    """
    _inherit = 'res.company'

    finance_interface = fields.Selection(selection=[('none', 'None')])
    journal_ids = fields.Many2many(comodel_name='account.journal',
                                   relation='res_company_account_journal',
                                   column1='res_company_id',
                                   column2='account_journal_id',
                                   string='Journal',
                                   domain="[('company_id', '=', active_id)]")
