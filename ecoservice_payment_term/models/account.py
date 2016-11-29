# -*- encoding: utf-8 -*-
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
#    OpenERP, Open Source Managemnt Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
##############################################################################
from inspect import getmembers
from pprint import pprint

from openerp import fields, models, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time

from babel import numbers, dates


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    due_amount_text = fields.Text(string='Overdue Payments', compute='compute_due_amount_text')

    @api.one
    @api.onchange('payment_term_id', 'date_invoice')
    def compute_due_amount_text(self):
        payment_term = self.payment_term_id
        if payment_term and self.date_invoice:
            terms = list()
            for term in payment_term.line_ids:
                due_date = datetime.strptime(self.date_invoice, '%Y-%m-%d') + relativedelta(
                    days=term.days)
                value_amount = term.value_amount
                if value_amount == 0:
                    value_amount = 1
                due_amount_de = numbers.format_currency(value_amount * self.amount_total,
                                                        currency=self.currency_id.name,
                                                        locale=self._context.get('lang', 'de_DE'))
                terms.append(_(u'Until {date} with {note} = {amount}').format(
                    date=dates.format_date(due_date, format='short', locale=self._context.get('lang', 'de_DE')),
                    # date=due_date,
                    note=term.note or u'',
                    amount=due_amount_de
                ))
            self.due_amount_text = u'\n'.join(terms)

    @api.onchange('payment_term_id', 'date_invoice')
    def _onchange_payment_term_date_invoice(self):
        date_invoice = self.date_invoice
        if not date_invoice:
            date_invoice = fields.Date.context_today(self)
        if not self.payment_term_id:
            # When no payment term defined
            self.date_due = self.date_due or self.date_invoice
        if self.date_due:
            # Don't change the due date if it already exists
            pass
        else:
            pterm = self.payment_term_id
            if pterm:
                if self.journal_id.type == 'purchase':
                    pterm_list = \
                        pterm.with_context(currency_id=self.currency_id.id).compute_for_purchase_invoice(value=1,
                                                                                                         date_ref=date_invoice)[
                            0]
                else:
                    pterm_list = \
                        pterm.with_context(currency_id=self.currency_id.id).compute(value=1, date_ref=date_invoice)[0]
                if pterm_list:
                    self.date_due = max(line[0] for line in pterm_list)
                else:
                    raise except_orm(_('Insufficient Data!'),
                                     _('The payment term of supplier does not have a payment term line.'))


class AccountPaymentTermLine(models.Model):
    _inherit = 'account.payment.term.line'

    note = fields.Text(string='Note', translate=True)
    default = fields.Boolean(string='Default')

    @api.onchange('default')
    def check_defaults(self):
        for record in self._origin.payment_id.line_ids:
            if record.id != self._origin.id:
                record.write({
                    'default': False,
                })


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    @api.one
    def compute_for_purchase_invoice(self, value, date_ref=False):
        date_ref = date_ref or fields.Date.today()
        amount = value
        result = []
        if self.env.context.get('currency_id'):
            currency = self.env['res.currency'].browse(self.env.context['currency_id'])
        else:
            currency = self.env.user.company_id.currency_id
        prec = currency.decimal_places
        for line in self.line_ids.filtered('default'):
            if line.value == 'fixed':
                amt = round(line.value_amount, prec)
            elif line.value == 'percent':
                amt = round(value * (line.value_amount / 100.0), prec)
            elif line.value == 'balance':
                amt = round(amount, prec)
            if amt:
                next_date = fields.Date.from_string(date_ref)
                if line.option == 'day_after_invoice_date':
                    next_date += relativedelta(days=line.days)
                elif line.option == 'fix_day_following_month':
                    next_first_date = next_date + relativedelta(day=1, months=1)  # Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days - 1)
                elif line.option == 'last_day_following_month':
                    next_date += relativedelta(day=31, months=1)  # Getting last day of next month
                elif line.option == 'last_day_current_month':
                    next_date += relativedelta(day=31, months=0)  # Getting last day of next month
                result.append((fields.Date.to_string(next_date), amt))
                amount -= amt
        amount = reduce(lambda x, y: x + y[1], result, 0.0)
        dist = round(value - amount, prec)
        if dist:
            last_date = result and result[-1][0] or fields.Date.today()
            result.append((last_date, dist))
        return result


class account_payment(models.Model):
    _inherit = "account.payment"

    @api.model
    def default_get(self, fields):
        rec = super(account_payment, self).default_get(fields)
        invoice_defaults = self.resolve_2many_commands('invoice_ids', rec.get('invoice_ids'))
        if invoice_defaults and len(invoice_defaults) == 1:
            invoice = invoice_defaults[0]
            rec['amount'] = self.calculate_amount(self.env['account.invoice'].browse(invoice['id']))
        return rec

    @api.one
    @api.depends('invoice_ids', 'amount', 'payment_date', 'currency_id')
    def _compute_payment_difference(self):
        if len(self.invoice_ids) == 0:
            return
        current_amount = self.calculate_amount(self.invoice_ids)
        if not self.amount:
            self.amount = current_amount
        if self.invoice_ids[0].type in ['in_invoice', 'out_refund']:
            self.payment_difference = self.amount - self._compute_total_invoices_amount()
        else:
            self.payment_difference = self._compute_total_invoices_amount() - self.amount

    def calculate_amount(self,invoice_id):
        # do calculation of amount

        payment_term = invoice_id.payment_term_id
        cal_amount = 0.0
        if payment_term and invoice_id.date_invoice:
            for term in payment_term.line_ids:

                # Calculate due date with current date and payment terms
                due_date = datetime.strptime(invoice_id.date_invoice, '%Y-%m-%d') + relativedelta(
                    days=term.days)

                value_amount = term.value_amount
                if value_amount == 0:
                    value_amount = 1
                cal_amount = value_amount * invoice_id.residual

                if self.payment_date:
                    pay_date = datetime.strptime(self.payment_date, '%Y-%m-%d')
                else:
                    pay_date = datetime.now()

                td = abs(due_date - pay_date)
                if td.days > 0 and due_date >= pay_date:
                    break;
        if not payment_term:
            cal_amount = invoice_id.residual
        return cal_amount
