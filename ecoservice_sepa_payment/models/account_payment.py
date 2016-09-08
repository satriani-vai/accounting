# -*- coding: utf-8 -*-

from openerp import api, fields, models, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    state = fields.Selection(selection_add=[('pending', 'Waiting for Payment')])

    # new SEPA workflow
    sepa_block_for_payment_receipt = fields.Boolean('Wait for payment receipt', default=True)
    sepa_was_pending = fields.Boolean('Was Pending')

    @api.multi
    def create_pending(self):
        self.write({'state': 'pending', 'sepa_was_pending': True})
        for rec in self:
            rec.invoice_ids.write({'sepa_payment_sent': True})

    @api.multi
    def post(self):
        # This is by far not the best solution but it enables us to post the payment
        # in a very unintrusive way (the post method needs to be overwritten completely otherwise)
        self.filtered(lambda rec: rec.state == 'sent' and rec.sepa_was_pending).write({'state': 'draft'})
        super(AccountPayment, self).post()
        self.filtered('sepa_was_pending').write({'state': 'sent'})


class AccountRegisterPayments(models.TransientModel):
    _inherit = 'account.register.payments'

    sepa_block_for_payment_receipt = fields.Boolean('', default=True)

    @api.multi
    def create_payment(self):
        payment = self.env['account.payment'].create(self.get_payment_vals())
        if self.sepa_block_for_payment_receipt:
            payment.create_pending()
        else:
            payment.post()
        return {'type': 'ir.actions.act_window_close'}

    def get_payment_vals(self):
        res = super(AccountRegisterPayments, self).get_payment_vals()
        res.update({'sepa_block_for_payment_receipt': self.sepa_block_for_payment_receipt})
        return res
