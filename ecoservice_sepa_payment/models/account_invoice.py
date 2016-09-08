# -*- coding: utf-8 -*-

from openerp import fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    sepa_payment_sent = fields.Boolean('Payment sent', readonly=True)
