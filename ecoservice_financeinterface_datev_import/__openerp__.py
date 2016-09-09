# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright and licensing details.
# noinspection PyStatementEffect
{
    "name"       : "ecoservice: DATEV Import",
    "version"    : "9.0.1.0.0",
    "licence"    : "AGPL-3",
    "author"     : "ecoservice",
    "website"    : "https://www.ecoservice.de/",
    "description": """The module ecoservice_financeinterface_datev_import allow you to import accounting entries.

Details of the module:
* Import of accounting entries

Further information under
* https://www.ecoservice.de/page/odoo-datev
""",
    "category"   : "Generic Modules",
    "summary"    : "Import of DATEV Moves.",
    "depends"    : [
        "ecoservice_financeinterface_datev",
    ],
    "data"       : [
        'views/import_datev.xml',
        'views/import_datev_menu.xml',
        'data/import_datev_sequence.xml',
    ],
    "installable": True,
}
