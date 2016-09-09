# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright notices and license terms.
# noinspection PyStatementEffect
{
    "name"       : "Compacted Account Move Lines",
    "version"    : "8.0.1.0.0",
    "licence"    : "AGPL-3",
    "author"     : "ecoservice",
    "website"    : "https://www.ecoservice.de/",
    "category"   : "Accounting & Finance",
    "summary"    : "Summarize multiple invoice lines in one account move line.",
    "description": """

    Summarize multiple invoice lines in one account move line if the account are equal.

Further information under
* https://www.ecoservice.de/

ecoservice
Karl-Kellner-Str. 105J
30853 Langenhagen
Germany

Phone: +49.511.700376-20

""",
    "depends"    : [
        "account",
    ],
    'installable': True,
}

