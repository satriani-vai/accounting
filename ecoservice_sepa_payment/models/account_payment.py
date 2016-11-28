# -*- coding: utf-8 -*-
##############################################################################
#
#    ecoservice_interrogare
#    Copyright (C) 2016 ecoservice GbR (<http://www.ecoservice.de>).
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
##############################################################################

import datetime

from openerp import api, fields, models


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

    def get_skonto_by_date(self, date_invoice, residual_amount, payment_term_id):
        payment_term_lines = self.env['account.payment.term'].browse(payment_term_id).line_ids
        datetime_now = datetime.datetime.now()

        if type(date_invoice) is str:
            date_invoice = datetime.datetime.strptime(date_invoice, '%Y-%m-%d')

        _skonto = ["", residual_amount]
        for ptl in payment_term_lines:
            # Get the max-difference in days to reach a common base, start with top ptl
            _date_until = ptl.days
            if ptl.option in ('last_day_current_month', 'last_day_following_month'):
                next_month = datetime_now.replace(day=28) + datetime.timedelta(days=4)
                _date_until = next_month - datetime.timedelta(days=next_month.day)
                if ptl.option == 'last_day_following_month':
                    next_month = datetime_now.replace(day=28) + datetime.timedelta(days=34)
                    _date_until = next_month - datetime.timedelta(days=next_month.day)
                _date_until = (_date_until.date() - date_invoice.date()).days

            # Add the difference on the invoice date
            _max_date = date_invoice + datetime.timedelta(days=_date_until)
            # Check if current date is within, escape if so.
            if datetime_now.date() <= _max_date.date():
                _skonto = [ptl.note, residual_amount * ptl.value_amount]
                break
        return _skonto

    @api.model
    def default_get(self, fields):
        rec = super(AccountPayment, self).default_get(fields)
        invoice_defaults = self.resolve_2many_commands('invoice_ids', rec.get('invoice_ids'))
        if invoice_defaults and len(invoice_defaults) == 1:
            invoice = invoice_defaults[0]
            _skonto = ["", invoice['residual']]  # prevent empty list for communication field
            if invoice.get('payment_term_id'):
                _skonto = self.get_skonto_by_date(invoice['date_invoice'], invoice['residual'], invoice['payment_term_id'][0])
            rec['communication'] = u"{} - {}".format(unicode(invoice['reference']), _skonto[0]) if invoice.get('reference') and _skonto[0] else invoice.get('reference') or _skonto[0]
            rec['amount'] = _skonto[1]
        return rec


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
