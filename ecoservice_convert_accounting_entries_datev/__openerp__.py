# -*- coding: utf-8 -*-
# Part of Odoo. Developed by ecoservice (Uwe Böttcher und Falk Neubert GbR).
# See COPYRIGHT and LICENSE at the root directory of this module for full copyright and licensing details.
# noinspection PyStatementEffect
{
    'name': 'ecoservice: Convert Accounting Entries Datev',
    'summary': 'Convert existing accounting entries to Datev',
    'version': '9.0.1.0.0',
    'author': 'ecoservice',
    'website': 'www.ecoservice.de',
    'licence': 'LGPL-3',
    'category': 'Accounting',
    'depends': [
        'base',
        'account',
        'account_cancel',
        'ecoservice_financeinterface',
        'ecoservice_financeinterface_datev',
    ],
    'data': [
        'views/res_company_view.xml',
    ],
    'installable': True,
}
