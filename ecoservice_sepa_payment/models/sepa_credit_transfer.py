# -*- coding: utf-8 -*-

from openerp import models


class AccountSepaCreditTransfer(models.TransientModel):
    _inherit = 'account.sepa.credit.transfer'

    def _payments_filter(self, r):
        return r.payment_method_id.code == 'sepa_ct' and r.state in ('posted', 'sent', 'pending')
