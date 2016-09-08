# -*- coding: utf-8 -*-

from openerp.exceptions import Warning


class FinanceinterfaceException(Warning):
    """
    This exception only exists to be caught explicitly in a try statement.
    """
    pass
