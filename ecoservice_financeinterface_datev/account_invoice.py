# -*- coding: utf-8 -*-
# pylint: disable-msg=C0111
###############################################################################
#
#    ecoservice_financeinterface_datev
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
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
###############################################################################

from openerp.osv import fields, orm
from openerp.tools.translate import _


class AccountInvoice(orm.Model):
    _inherit = 'account.invoice'

    _columns = {
        'enable_datev_checks': fields.boolean('Perform Datev Checks'),
    }

    _defaults = {
        'enable_datev_checks': True}

    def is_datev_validation_active(self, cr, uid, ids, context=None):
        res = False
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        for invoice in self.browse(cr, uid, ids, context=context):
            if invoice.enable_datev_checks and user and user.company_id and user.company_id.enable_datev_checks:
                res = True
        return res

    def perform_datev_validation(self, cr, uid, ids, context=None, silent=False):
        context = context or dict()
        is_valid = True
        errors = list()

        for rec in self.browse(cr, uid, ids, context=context):
            if self.is_datev_validation_active(cr, uid, [rec.id], context=context):
                if silent:  # Shorter, more performant version w/o string and exception handling
                    for line in rec.invoice_line:
                        if not self.pool.get('account.invoice.line').perform_datev_validation(
                                cr, uid, [line.id],
                                context=None,
                                silent=True,
                                line_no=None):
                            return False
                else:
                    for line_no, line in enumerate(rec.invoice_line, start=1):
                        try:
                            self.pool.get('account.invoice.line').perform_datev_validation(
                                cr, uid, [line.id],
                                context=None,
                                silent=silent,
                                line_no=line_no)
                        except Exception as E:
                            raise
                            is_valid = False
                            errors.append(E.message)

        if not (silent or is_valid):
            raise orm.except_orm(_(u'Datev Error'), u'\n'.join(errors))

        return is_valid


class AccountInvoiceLine(orm.Model):
    _inherit = 'account.invoice.line'

    def perform_datev_validation(self, cr, uid, ids, context=None, silent=False, line_no=None):
        """
        Performs tests on an invoice line for whether the taxes are correctly set or not.

        The major use of this method is in the condition of a workflow transition.

        :param line_no: int Line number to be displayed in an error message.
        :param silent: bool Specifies whether an exception in case of a failed test should be thrown
            or if the checks should be performed silently.
        :return: True if all checks were performed w/o errors or no datev checks are applicable. False otherwise.
        :rtype: bool
        """
        for line in self.browse(cr, uid, ids, context=context):
            if not self.is_datev_validation_applicable(cr, uid, [line.id], context=context, line=line):
                return True
            is_valid = len(line.invoice_line_tax_id) == 1 and line.account_id.datev_steuer == line.invoice_line_tax_id[
                0]
            if not (silent or is_valid):
                raise orm.except_orm(
                    _(u'Datev Error'),
                    _(
                        u'Line {line}: The taxes specified in the invoice line ({tax_line}) and the corresponding account ({tax_account}) mismatch!').format(
                        line=line_no,
                        tax_line=line.invoice_line_tax_id[0].description,
                        tax_account=line.account_id.datev_steuer.description
                    )
                )
            return is_valid

    def is_datev_validation_applicable(self, cr, uid, ids, context=None, line=False):
        """
        Tests if an invoice line is applicable to datev checks or not.

        :return: True if it is applicable. Otherwise False.
        :rtype: bool
        """
        return line.account_id.automatic if line and line.account_id else False
