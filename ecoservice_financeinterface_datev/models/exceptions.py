# -*- coding: utf-8 -*-

from openerp.addons.ecoservice_financeinterface.models.exceptions import FinanceinterfaceException


class DatevWarning(FinanceinterfaceException):
    """
    This exception only exists to be caught explicitly in a try statement.
    """
    pass
