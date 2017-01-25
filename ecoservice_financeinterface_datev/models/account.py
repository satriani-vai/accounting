# -*- coding: utf-8 -*-
"""
The account module extends the original OpenERP account objects with different attributes and methods
"""

from openerp import models, fields, _
from decimal import Decimal
from . import exceptions


class account_account(models.Model):
    """Inherits the account.account class and adds attributes
    """
    _inherit = 'account.account'

    ustuebergabe = fields.Boolean('Datev VAT-ID', help=_(u'Is required when transferring a sales tax identification number from the account partner (e.g. EU-Invoice)'))
    automatic = fields.Boolean('Datev Automatic Account')
    datev_steuer = fields.Many2one('account.tax', 'Datev Tax Account', domain=[('buchungsschluessel', '!=', -1)])
    datev_steuer_erforderlich = fields.Boolean('Tax posting required?')

    def cron_update_line_autoaccounts_tax(self, cr, uid, context=None):
        """Method for Cronjop that Updates all account.move.lines
        without ecofi_taxid of Accounts where automatic is True and a datev_steuer
        """
        context = context or dict()
        ids = self.search(cr, uid, [('automatic', '=', True), ('datev_steuer', '!=', False)])
        for account in self.read(cr, uid, ids, load='_classic_write'):
            move_line_ids = self.pool.get('account.move.line').search(cr, uid, [('account_id', '=', account['id']), ('ecofi_taxid', '=', False)], context=context)
            if move_line_ids:
                self.pool.get('account.move.line').write(cr, uid, move_line_ids, {'ecofi_taxid': account['datev_steuer']}, context=context)


class AccountTax(models.Model):
    """Inherits the account.tax class and adds attributes
    """
    _inherit = 'account.tax'
    datev_skonto = fields.Many2one('account.account', 'Datev Cashback Account')


class AccountPaymentTerm(models.Model):
    """Inherits the account.payment.term class and adds attributes
    """
    _inherit = 'account.payment.term'
    zahlsl = fields.Integer('Payment key')


class account_move(models.Model):
    """ Inherits the account.move class to add checking methods to the original post method
    """
    _inherit = 'account.move'

    enable_datev_checks = fields.Boolean('Perform Datev Checks', default=True)

    def datev_account_checks(self, cr, uid, move, context=None):
        context = context or dict()
        errors = list()
        self.update_line_autoaccounts_tax(cr, uid, move, context=context)
        for linecount, line in enumerate(move.line_id, start=1):
            if line.account_id.id != line.ecofi_account_counterpart.id:
                if not self.pool.get('ecofi').is_taxline(cr, line.account_id.id) or line.ecofi_bu == 'SD':
                    linetax = self.pool.get('ecofi').get_line_tax(cr, uid, line)
                    if line.account_id.automatic and not line.account_id.datev_steuer:
                        errors.append(_(u'The account {account} is an Auto-Account but the automatic taxes are not configured!').format(
                            account=line.account_id.code))
                    if line.account_id.datev_steuer_erforderlich and not linetax:
                        errors.append(_(u'The Account requires a tax but the move line {line} has no tax!').format(line=linecount))
                    if line.account_id.automatic and linetax:
                        if not line.account_id.datev_steuer or linetax.id != line.account_id.datev_steuer.id:
                            errors.append(_(
                                u'The account is an Auto-Account but the tax account ({line}) in the move line {tax_line} differs from the configured {tax_datev}!').format(
                                    line=linecount, tax_line=linetax.name, tax_datev=line.account_id.datev_steuer.name))
                    if line.account_id.automatic and not linetax:
                        errors.append(_(u'The account is an Auto-Account but the tax account in the move line {line} is not set!').format(line=linecount))
                    if not line.account_id.automatic and linetax and linetax.buchungsschluessel < 0:
                        errors.append(_(u'The booking key for the tax {tax} is not configured!').format(tax=linetax.name))
        return '\n'.join(errors)

    def update_line_autoaccounts_tax(self, cr, uid, move, context=None):
        context = context or dict()
        errors = list()
        for linecount, line in enumerate(move.line_id, start=1):
            if line.account_id.id != line.ecofi_account_counterpart.id:
                if not self.pool.get('ecofi').is_taxline(cr, line.account_id.id):
                    linetax = self.pool.get('ecofi').get_line_tax(cr, uid, line)
                    if line.account_id.automatic and not linetax:
                        if line.account_id.datev_steuer:
                            self.pool.get('account.move.line').write(cr, uid, [line.id], {'ecofi_taxid': line.account_id.datev_steuer.id}, context=context)
                        else:
                            errors.append(_(u'The Account is an Auto-Account but the move line {line} has no tax!').format(line=linecount))
        return '\n'.join(errors)

    def datev_tax_check(self, cr, uid, move, context=None):
        context = context or dict()
        errors = list()
        linecount = 0
        tax_values = dict()
        linecounter = 0
        for line in move.line_id:
            linecount += 1
            if line.account_id.id != line.ecofi_account_counterpart.id:
                if self.pool.get('ecofi').is_taxline(cr, line.account_id.id) and not line.ecofi_bu == 'SD':
                    if line.account_id.code not in tax_values:
                        tax_values[line.account_id.code] = {
                            'real': 0.0,
                            'datev': 0.0
                        }
                    tax_values[line.account_id.code]['real'] += line.debit - line.credit
                else:
                    linecounter += 1
                    new_context = context.copy()
                    new_context['return_calc'] = True
                    taxcalc_ids = self.pool.get('ecofi').calculate_tax(cr, uid, line, new_context)
                    for taxcalc_id in taxcalc_ids:
                        taxaccount = taxcalc_id['account_paid_id'] and taxcalc_id['account_paid_id'] or taxcalc_id['account_collected_id']
                        if taxaccount:
                            datev_account_code = self.pool.get('account.account').read(cr, uid, taxaccount, context=new_context)['code']
                            if datev_account_code not in tax_values:
                                tax_values[datev_account_code] = {
                                    'real': 0.0,
                                    'datev': 0.0,
                                }
                            if line.ecofi_bu and line.ecofi_bu == '40':
                                continue
                            tax_values[datev_account_code]['datev'] += taxcalc_id['amount']

        sum_real = 0.0
        sum_datev = 0.0
        for value in tax_values.itervalues():
            sum_real += value['real']
            sum_datev += value['datev']
        if Decimal(str(abs(sum_real - sum_datev))) > Decimal(str(10 ** -2 * linecounter)):
            errors.append(_(u'The sums for booked ({real}) and calculated ({datev}) are different!').format(
                real=sum_real, datev=sum_datev))

        return '\n'.join(errors)

    def datev_checks(self, cr, uid, move, context=None):
        """Constraint check if export method is 'gross'
        :param cr: the current row, from the database cursor
        :param uid: the current user’s ID for security checks
        :param move: account_move
        :param context: context arguments, like lang, time zone
        """
        context = context or dict()
        errors = list()
        errors.append(self.update_line_autoaccounts_tax(cr, uid, move, context=context))
        errors.append(self.datev_account_checks(cr, uid, move, context=context))
        if not errors:
            errors.append(self.datev_tax_check(cr, uid, move, context=context))
        return '\n'.join(filter(lambda e: bool(e), errors)) or False

    def finance_interface_checks(self, cr, uid, ids, context=None):
        context = context or dict()
        res = True
        if 'invoice' not in context or context['invoice'] and context['invoice'].enable_datev_checks:
            for move in self.browse(cr, uid, ids, context=context):
                if move.enable_datev_checks and self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.enable_datev_checks:
                    res &= super(account_move, self).finance_interface_checks(cr, uid, ids, context=context)
                    error = self.datev_checks(cr, uid, move, context=context)
                    if error:
                        raise exceptions.DatevWarning(error)
        return res


class AccountMoveLine(models.Model):
    """Inherits the account.move.line class and adds attributes
    """
    _inherit = 'account.move.line'

    ecofi_bu = fields.Selection([
        ('40', '40'),
        ('SD', 'Steuer Direkt')
    ], 'Datev BU', select=True)
