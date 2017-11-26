# -*- coding: utf-8 -*-
# pylint: disable-msg=C0111
###############################################################################
#
#    ecoservice_financeinterface_datev
#    Copyright (c) 2015 ecoservice GbR (<http://www.ecoservice.de>).
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
#    This program based on Odoo.
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
###############################################################################

from odoo import api, fields, models, _
from . import exceptions


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    enable_datev_checks = fields.Boolean('Perform Datev Checks', default=True)

    @api.multi
    def is_datev_validation_active(self):
        self.ensure_one()
        return self.enable_datev_checks and self.env['res.users'].browse(self._uid).company_id.enable_datev_checks

    @api.multi
    def perform_datev_validation(self, silent=False):
        is_valid = True
        errors = list()

        for rec in self:
            if rec.is_datev_validation_active():
                if silent:  # Shorter, more performant version w/o string and exception handling
                    for line in rec.invoice_line_ids:
                        if not line.perform_datev_validation(silent=True):
                            return False
                else:
                    for line_no, line in enumerate(rec.invoice_line_ids, start=1):
                        try:
                            line.perform_datev_validation(line_no=line_no)
                        except exceptions.DatevWarning as dw:
                            is_valid = False
                            from odoo.exceptions import except_orm
                            errors.append(dw.name if isinstance(dw, except_orm) else dw.message)

        if not (silent or is_valid):
            raise exceptions.DatevWarning(u'\n'.join(errors))

        return is_valid


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    @api.multi
    def perform_datev_validation(self, silent=False, line_no=None):
        """
        Performs tests on an invoice line for whether the taxes are correctly set or not.

        The major use of this method is in the condition of a workflow transition.

        :param line_no: int Line number to be displayed in an error message.
        :param silent: bool Specifies whether an exception in case of a failed test should be thrown
            or if the checks should be performed silently.
        :return: True if all checks were performed w/o errors or no datev checks are applicable. False otherwise.
        :rtype: bool
        """
        self.ensure_one()
        if not self.is_datev_validation_applicable():
            return True
        is_valid = len(self.invoice_line_tax_ids) == 1 and self.account_id.datev_steuer == self.invoice_line_tax_ids
        if not (silent or is_valid):
            raise exceptions.DatevWarning(
                _(u'Line {line}: The taxes specified in the invoice line ({tax_line}) and the corresponding account ({tax_account}) mismatch!').format(
                    line=line_no,
                    tax_line=self.invoice_line_tax_ids.description,
                    tax_account=self.account_id.datev_steuer.description
                )
            )
        return is_valid

    @api.multi
    def is_datev_validation_applicable(self):
        """
        Tests if an invoice line is applicable to datev checks or not.

        :return: True if it is applicable. Otherwise False.
        :rtype: bool
        """
        self.ensure_one()
        return self.account_id.automatic
