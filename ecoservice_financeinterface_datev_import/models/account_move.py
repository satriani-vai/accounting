# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright and licensing details.

from openerp import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    import_datev = fields.Many2one('import.datev', 'DATEV Import', readonly=True)
