# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright notices and license terms.
# noinspection PyStatementEffect
{
    "name"       : "Compacted Account Move Lines",
    "version"    : "7.0.1.0.0",
    "licence"    : "AGPL-3",
    "author"     : "ecoservice",
    "website"    : "https://www.ecoservice.de/",
    "category"   : "Accounting & Finance",
    "summary"    : "Summarize multiple invoice lines to one account move line.",
    'description': """
Description
===========

This module overrides the default behavior and summarize multiple invoice lines to one account move line by its account instead the product.

Usage
=====

Just like before. Validate your invoices and the new behavior is automatically used.
""",
    "depends"    : [
        "account",
    ],
    'installable': True,
}

