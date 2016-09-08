# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright and licensing details.
# noinspection PyStatementEffect
{
    "name"       : "Financial Interface: DATEV (Import)",
    "version"    : "9.0.1.0.0",
    "licence"    : "AGPL-3",
    "author"     : "ecoservice GbR",
    "website"    : "https://www.ecoservice.de/",
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
