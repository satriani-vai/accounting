# coding=utf-8
##############################################################################
#    ecoservice_payment_term
#    Copyright (c) 2016 ecoservice GbR (<http://www.ecoservice.de>).
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
# noinspection PyStatementEffect
{
    'name': 'ecoservice: Due Date',
    'author': 'ecoservice',
    'website': 'www.ecoservice.de',
    'category': 'Base',
    'version': '9.0.1.0',
    "description": """
                    * Prevents overwriting due date if manually created
                    * Adds Description and Default in payment term
                    * Computes due date from the default payment term
                    * Shows the due dates with due amount and Description
                     """,
    'depends': [
        'base',
        'purchase',
        'sale',
        'account',
    ],
    'data': [
        'views/account_invoice_view.xml',
    ],
    'application': False,
}
