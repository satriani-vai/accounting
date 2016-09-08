# -*- coding: utf-8 -*-
{
    'name': 'Ecoservice Financial Interface',
    'version': '8.0.1.0.2',
    'depends': [
        'base',
        'account'
    ],
    'author': 'ecoservice',
    'website': 'https://www.ecoservice.de',
    'description': """The main modul ecoservice_finance provides the basic methods for the finance interface.

Further information under
* Github: https://github.com/ecoservice/ecoservice
* Ecoservice Website https://www.ecoservice.de
""",
    'category': 'Accounting',
    'data': [
        'security/ecofi_security.xml',
        'security/ir.model.access.csv',
        'data/ecofi_sequence.xml',
        'views/account_view.xml',
        'views/account_invoice_view.xml',
        'views/ecofi_view.xml',
        'views/res_company_view.xml',
        'wizard/wizard_view.xml'
    ],
    'demo': [],
    'test': [],
    'active': False,
    'installable': True,
    'application': True
}
