# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright and licensing details.

from openerp import models


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def inv_line_characteristic_hashcode(self, invoice_line):
        """
        super()
        New hash to combine lines with the same account and not just with the same product.
        """
        return "{0}-{1}-{2}-{3}".format(
            invoice_line.get("account_id", False),
            invoice_line.get("tax_code_id", False),
            invoice_line.get("analytic_account_id", False),
            invoice_line.get("date_maturity", False)
        )

    def group_lines(self, iml, line):
        """
        super()
        Looks up if any two lines are combined and flags the line, so it can later be changed to a useful name.
        """
        result = super(AccountInvoice, self).group_lines(iml, line)

        combined_lines = False
        if self.journal_id.group_invoice_lines:
            line_hash_collection = dict()
            for x, y, line_data in line:
                hash_code = self.inv_line_characteristic_hashcode(line_data)
                if hash_code in line_hash_collection:
                    # Found at least one combined line, so can proceed with the next step.
                    combined_lines = True
                    break
                else:
                    line_hash_collection[hash_code] = line_data

        if combined_lines:
            for line_data in result:
                if line_data[2]["name"] is not '/':
                    line_data[2]["name"] = "is_combined"
        return result
