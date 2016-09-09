# -*- coding: utf-8 -*-

{
    'name': 'ecoservice: SEPA Payment',
    'version': '9.0.0.1.0',
    'category': 'Accounting & Finance',
    'summary': u"SEPA extension to block a payment from being booked.",
    'description': u"""
        When a payment is created from an invoice, it is booked (posted) immediately.
        With this module you can specify that you want the payment to be booked later when the actual payment e.g. arrived on your bank account
        either manually or some automated method.
    """,
    'author': 'ecoservice GbR',
    'website': 'https://www.ecoservice.de',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'ecoservice_sepa_pain',
    ],
    'data': [
        'views/account_invoice_view.xml',
        'views/account_payment_view.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False
}
