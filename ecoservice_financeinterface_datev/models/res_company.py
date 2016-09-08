# -*- coding: utf-8 -*-

from openerp import fields, models


class ResCompany(models.Model):
    """
    Inherits the res.company class and adds methods and attributes
    """
    _inherit = 'res.company'

    finance_interface = fields.Selection(selection_add=[('datev', 'Datev')], string='Finance Interface')
    exportmethod = fields.Selection(selection=[('netto', 'netto'), ('brutto', 'brutto')], string='Export method')
    enable_datev_checks = fields.Boolean('Perform Datev Checks', default=True)
