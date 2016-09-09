# -*- encoding: utf-8 -*- # pylint: disable-msg=C0111
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
{  # pylint: disable-msg=W0104
    "name": "ecoservice: Financial Interface",
    "version": "1.0",
    "depends": ["base", "account"],
    "author": "ecoservice",
    "website": "http://www.ecoservice.de",
    "summary": "Main Modul for export of accounting moves",
    "description": """The main modul ecoservice_finance provides the basic methods for the finance interface.

Further information under
* https://www.ecoservice.de/page/odoo-datev

ecoservice
Karl-Kellner-Str. 105J
30853 Langenhagen
Germany

Phone: +49.511.700376-20
""",
    "category": "Accounting",
    "init_xml": [],
    "data": [
                    'security/ecofi_security.xml',
                    'security/ir.model.access.csv',
                    'account_view.xml',
                    'account_invoice_view.xml',
                    'ecofi_sequence.xml',
                    'ecofi_view.xml',
                    'res_company_view.xml',
                    'wizard/wizard_view.xml'
                    ],
    "demo_xml": [],
    "test": [],
    "active": False,
    "installable": True
}
