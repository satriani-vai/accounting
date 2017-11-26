# -*- coding: utf-8 -*-
##############################################################################
#    ecoservice_financeinterface_datev
#    Copyright (c) 2013 ecoservice GbR (<http://www.ecoservice.de>).
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
##############################################################################
import datetime

from odoo import tools
from odoo.tests.common import TransactionCase

from odoo import netsvc

import base64
import cStringIO
import csv

class TestEcoserviceFinanceinterface(TransactionCase):
    def setUp(self):
        """ setUp ***"""
        super(TestEcoserviceFinanceinterface, self).setUp()
        cr, uid = self._cr, self._uid
        
        self.partner = self.registry('res.partner')
        self.company = self.registry('res.company')
        self.invoice = self.registry('account.invoice')
        self.journal = self.registry('account.journal')
        self.account = self.registry('account.account')
        self.tax = self.registry('account.tax')
        self.account_move = self.registry('account.move')
        self.account_move_line = self.registry('account.move.line')
        self.ecofi = self.registry('ecofi')
        self.export_ecofi = self.registry('export.ecofi')

        self.company_id = self.registry("ir.model.data").get_object_reference(cr, uid, "base", "main_company")[1]
        self.account_id_recievable = self.registry("ir.model.data").get_object_reference(cr, uid, "account", "a_recv")[1]
        self.account_id_payable = self.registry("ir.model.data").get_object_reference(cr, uid, "account", "a_pay")[1]
        self.account_id_vat = self.registry("ir.model.data").get_object_reference(cr, uid, "account", "iva")[1]
        self.account_id_sales = self.registry("ir.model.data").get_object_reference(cr, uid, "account", "a_sale")[1]
        self.account_id_purchase = self.registry("ir.model.data").get_object_reference(cr, uid, "account", "a_expense")[1]
        self.product_id = self.registry("ir.model.data").get_object_reference(cr, uid, "product", "product_product_6")[1]

        self.partner_id = self.partner.create(cr, uid, {'name':'Test Company', 
                                                    'email':'test@localhost',
                                                    'is_company': True,
                                                    }, 
                                                context=None)        
        
        self.journal_sale_id = self.journal.create(cr, uid, {'name': 'ecofi sale test',
                                                        'code': 'ESAL',
                                                        'type': 'sale',
                                                        'company_id': self.company_id,
                                                        })
        self.journal_purchase_id = self.journal.create(cr, uid, {'name': 'ecofi purchase test',
                                                        'code': 'EPUR',
                                                        'type': 'purchase',
                                                        'company_id': self.company_id,
                                                        })
        
        self.tax_id = self.tax.create(cr, uid, {
                                                'name': '19% UST',
                                                'type': 'percent',
                                                'amount': '0.19',
                                                'buchungsschluessel': '9',
                                                'refund_account_id': self.account_id_vat,
                                                'account_id': self.account_id_vat,
                                            })
        self.company.write(cr, uid, [self.company_id], {'finance_interface': 'datev', 'exportmethod': 'brutto'} )
        
    def export_wizard_csv_check(self, cr, uid, check_list, context=None):
        self.export_ecofi_id = self.export_ecofi.create(cr, uid, {'journal_id':[(6,0,[self.journal_sale_id, self.journal_purchase_id])]})
        ecofi_id = self.export_ecofi.startexport(cr, uid, [self.export_ecofi_id], context={})['res_id']
        ecofi_instance = self.ecofi.browse(cr, uid, ecofi_id)
        exportcsv = base64.decodestring(ecofi_instance.csv_file)
        exportlines = csv.DictReader(cStringIO.StringIO(exportcsv), delimiter=';')
        errortext = ''
        errorfound = False
        for line in exportlines:
            for check in check_list:
                linedetectet = True
                for ident in check['ident']:
                    if line[ident[0]] != ident[1]:
                        linedetectet = False
                if linedetectet:
                    check['tested'] = True
                    for key in check['check']:
                        if line[key] != check['check'][key]:
                            errorfound = True
                            errortext += '%s: %s != %s,' % (key, line[key], check['check'][key]) 
        for check in check_list:
            if 'tested' not in check:
                 self.assertEqual(True, False, "Check %s has not been tested no line was found" % (check))
        self.assertEqual(errorfound, False, "Error validation csv export: '%s'" % (errortext[:-1]))
            
    def test_00_check_invoice_out(self):
        """ Testing if invoice out parameters are passed correctly to the account moves"""
        cr, uid = self._cr, self._uid      
        invoice_id_out = self.invoice.create(cr, uid, {'partner_id': self.partner_id, 
                                                        'account_id': self.account_id_recievable, 
                                                        'journal_id': self.journal_sale_id, 
                                                        'type': 'out_invoice',
                                                        'origin': 'origin_check',
                                                        'ecofi_buchungstext': 'CHECK BUCHUNGSTEXT',
                                                        'invoice_line': [(0, 0, {
                                                                            'name': "LCD Screen", 
                                                                            'product_id': self.product_id, 
                                                                            'account_id': self.account_id_sales,
                                                                            'quantity': 5, 
                                                                            'price_unit':200,
                                                                            'invoice_line_tax_id': [(6,0,[self.tax_id])]
                                                                                 })]})
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'account.invoice', invoice_id_out, 'invoice_open', cr)
        thisinvoice = self.invoice.browse(cr, uid, invoice_id_out) 
        self.assertEqual(thisinvoice.move_id.ecofi_buchungstext, thisinvoice.ecofi_buchungstext, 
                                            "Invoice Out Vouchernumber 2 was not updated correctly") 
        for move_line in thisinvoice.move_id.line_id:
            if move_line.account_id.id == self.account_id_sales: 
                self.assertEqual(move_line.ecofi_taxid.id, self.tax_id, 
                                                    "Tax was not passed correctly to account move!")
        self.account_move.write(cr, uid, [thisinvoice.move_id.id], {'name': 'TIN01'})
        checklist = []
        checklist.append({'ident': [('Belegfeld 1', 'TIN01')],
                          'check': {'BU-Schl\xfcssel ': '9', 
                                    'Konto': 'X11002', 
                                    'Gegenkonto (ohne BU-Schl\xfcssel)': 'X2001', 
                                    'W\xe4hrungskennung': 'EUR', 
                                    'Buchungstext': 'CHECK BUCHUNGSTEXT', 
                                    'Belegfeld 1': 'TIN01', 
                                    'Umsatz (ohne Soll-/Haben-Kennzeichen)': '1190,0', 
                                    'Soll-/Haben-Kennzeichen': 's', 
                                    'EU-Land und UStID': ''
                                    },
                         })
        self.export_wizard_csv_check(cr, uid, checklist) 
        

    def test_01_check_invoice_in(self):
        """ Testing if invoice in parameters are passed correctly to the account moves)"""
        cr, uid = self._cr, self._uid
        invoice_id_in = self.invoice.create(cr, uid, {'partner_id': self.partner_id, 
                                                           'name': 'check_invoice_name',
                                                        'account_id': self.account_id_payable, 
                                                        'journal_id': self.journal_purchase_id, 
                                                        'type': 'in_invoice',
                                                        'origin': 'origin_check',
                                                        'check_total': 1000,
                                                        'ecofi_buchungstext': 'CHECK BUCHUNGSTEXT',
                                                        'invoice_line': [(0, 0, {
                                                                            'name': "LCD Screen", 
                                                                            'product_id': self.product_id, 
                                                                            'account_id': self.account_id_purchase,
                                                                            'quantity': 5, 
                                                                            'price_unit':200
                                                                                 })]})
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'account.invoice', invoice_id_in, 'invoice_open', cr)
        thisinvoice = self.invoice.browse(cr, uid, invoice_id_in)    
        self.assertEqual(thisinvoice.move_id.ecofi_buchungstext, thisinvoice.ecofi_buchungstext, 
                                            "Invoice Out Vouchernumber 2 was not updated correctly")
        

    
    def test_02_sale_move_no_autoaccount(self):
        """ Testing a sales move on an non autoaccount"""
        cr, uid = self._cr, self._uid
        move = {'name': 'TESTMOVE01',
                'journal_id': self.journal_sale_id,
                'state': 'draft',
                'ecofi_buchungstext': 'CHECK BUCHUNGSTEXT'
                }
        move_id = self.account_move.create(cr, uid, move)
        line = {'name': 'TAX',
                'debit': 0.00,
                'credit': 190.00,
                'account_id': self.account_id_vat,
                'move_id': move_id,
                }   
        self.account_move_line.create(cr, uid, line)
        line = {'name': 'SALES',
                'debit': 0.00,
                'credit': 1000.00,
                'account_id': self.account_id_sales,
                'ecofi_taxid': self.tax_id,
                'move_id': move_id,
                }   
        self.account_move_line.create(cr, uid, line)
        line = {'name': 'DEBIT',
                'debit': 1190.00,
                'credit': 0.00,
                'account_id': self.account_id_recievable,
                'move_id': move_id,
                }      
        self.account_move_line.create(cr, uid, line)
        self.account_move.button_validate(cr, uid, [move_id])
        checklist = []
        checklist.append({'ident': [('Belegfeld 1', 'TESTMOVE01')],
                          'check': {'BU-Schl\xfcssel ': '9', 
                                    'Konto': 'X11002', 
                                    'Gegenkonto (ohne BU-Schl\xfcssel)': 'X2001', 
                                    'W\xe4hrungskennung': 'EUR', 
                                    'Buchungstext': 'CHECK BUCHUNGSTEXT', 
                                    'Belegfeld 1': 'TESTMOVE01', 
                                    'Umsatz (ohne Soll-/Haben-Kennzeichen)': '1190,0', 
                                    'Soll-/Haben-Kennzeichen': 's', 
                                    'EU-Land und UStID': ''
                                    },
                         })
        self.export_wizard_csv_check(cr, uid, checklist) 

    def test_03_purchase_move_no_autoaccount(self):
        """ Testing a purchase move on an non autoaccount"""
        cr, uid = self._cr, self._uid
        move = {'name': 'TESTMOVE01',
                'journal_id': self.journal_purchase_id,
                'state': 'draft',
                'ecofi_buchungstext': 'CHECK BUCHUNGSTEXT'
                }
        move_id = self.account_move.create(cr, uid, move)
        line = {'name': 'TAX',
                'debit': 190.00,
                'credit': 0.00,
                'account_id': self.account_id_vat,
                'move_id': move_id,
                }   
        self.account_move_line.create(cr, uid, line)
        line = {'name': 'PURCHASE',
                'debit': 1000.00,
                'credit': 0.00,
                'account_id': self.account_id_purchase,
                'ecofi_taxid': self.tax_id,
                'move_id': move_id,
                }   
        self.account_move_line.create(cr, uid, line)
        line = {'name': 'CREDIT',
                'debit': 0.00,
                'credit': 1190.00,
                'account_id': self.account_id_payable,
                'move_id': move_id,
                }      
        self.account_move_line.create(cr, uid, line)
        self.account_move.button_validate(cr, uid, [move_id])
        checklist = []
        checklist.append({'ident': [('Belegfeld 1', 'TESTMOVE01')],
                          'check': {'BU-Schl\xfcssel ': '9', 
                                    'Konto': 'X1111', 
                                    'Gegenkonto (ohne BU-Schl\xfcssel)': 'X2110', 
                                    'W\xe4hrungskennung': 'EUR', 
                                    'Buchungstext': 'CHECK BUCHUNGSTEXT', 
                                    'Belegfeld 1': 'TESTMOVE01', 
                                    'Belegfeld 2': '', 
                                    'Umsatz (ohne Soll-/Haben-Kennzeichen)': '1190,0', 
                                    'Soll-/Haben-Kennzeichen': 'h', 
                                    'EU-Land und UStID': ''
                                    },
                         })
        self.export_wizard_csv_check(cr, uid, checklist) 

    def test_04_sale_move_autoaccount(self):
        """ Testing a sales move on an autoaccount"""
        cr, uid = self._cr, self._uid
        move = {'name': 'TESTMOVE01',
                'journal_id': self.journal_sale_id,
                'state': 'draft',
                'ecofi_buchungstext': 'CHECK BUCHUNGSTEXT'
                }
        move_id = self.account_move.create(cr, uid, move)
        line = {'name': 'TAX',
                'debit': 0.00,
                'credit': 190.00,
                'account_id': self.account_id_vat,
                'move_id': move_id,
                }   
        self.account_move_line.create(cr, uid, line)
        self.account.write(cr, uid, [self.account_id_sales], {'automatic': True,
                                                              'datev_steuer': self.tax_id,
                                                              })
        line = {'name': 'SALES',
                'debit': 0.00,
                'credit': 1000.00,
                'account_id': self.account_id_sales,
                'ecofi_taxid': self.tax_id,
                'move_id': move_id,
                }   
        self.account_move_line.create(cr, uid, line)
        line = {'name': 'DEBIT',
                'debit': 1190.00,
                'credit': 0.00,
                'account_id': self.account_id_recievable,
                'move_id': move_id,
                }      
        self.account_move_line.create(cr, uid, line)
        self.account_move.button_validate(cr, uid, [move_id])
        checklist = []
        checklist.append({'ident': [('Belegfeld 1', 'TESTMOVE01')],
                          'check': {'BU-Schl\xfcssel ': '', 
                                    'Konto': 'X11002', 
                                    'Gegenkonto (ohne BU-Schl\xfcssel)': 'X2001', 
                                    'W\xe4hrungskennung': 'EUR', 
                                    'Buchungstext': 'CHECK BUCHUNGSTEXT', 
                                    'Belegfeld 1': 'TESTMOVE01', 
                                    'Belegfeld 2': '', 
                                    'Umsatz (ohne Soll-/Haben-Kennzeichen)': '1190,0', 
                                    'Soll-/Haben-Kennzeichen': 's', 
                                    'EU-Land und UStID': ''
                                    },
                         })
        self.export_wizard_csv_check(cr, uid, checklist) 

    def test_05_testing_taxrequired_constraint(self):
        """ Testing if the Tax Required Constraint is working"""
        cr, uid = self._cr, self._uid
        move = {'name': 'TESTMOVE01',
                'journal_id': self.journal_sale_id,
                'state': 'draft',
                'ecofi_buchungstext': 'CHECK BUCHUNGSTEXT'
                }
        move_id = self.account_move.create(cr, uid, move)
        line = {'name': 'TAX',
                'debit': 0.00,
                'credit': 190.00,
                'account_id': self.account_id_vat,
                'move_id': move_id,
                }   
        self.account_move_line.create(cr, uid, line)
        self.account.write(cr, uid, [self.account_id_sales], {'automatic': False,
                                                              'datev_steuer_erforderlich': True,
                                                              })
        line = {'name': 'SALES',
                'debit': 0.00,
                'credit': 1000.00,
                'account_id': self.account_id_sales,
                'move_id': move_id,
                }   
        self.account_move_line.create(cr, uid, line)
        line = {'name': 'DEBIT',
                'debit': 1190.00,
                'credit': 0.00,
                'account_id': self.account_id_recievable,
                'move_id': move_id,
                }      
        self.account_move_line.create(cr, uid, line)
        try:
            self.account_move.button_validate(cr, uid, [move_id])
            self.assertEqual(True, False,"The move should not have been validatet!")
        except:
            pass
        
    def test_05_testing_manual_correct(self):
        """ Testing if a manual configured booking is working"""
        cr, uid = self._cr, self._uid
        move = {'name': 'TESTMOVE01',
                'journal_id': self.journal_sale_id,
                'state': 'draft',
                'ecofi_buchungstext': 'CHECK BUCHUNGSTEXT',
                'ecofi_manual': True
                }
        move_id = self.account_move.create(cr, uid, move)
        line = {'name': 'TAX',
                'debit': 0.00,
                'credit': 190.00,
                'account_id': self.account_id_vat,
                'move_id': move_id,
                'ecofi_account_counterpart': self.account_id_recievable,
                }
        self.account_move_line.create(cr, uid, line)
        self.account.write(cr, uid, [self.account_id_sales], {'automatic': False,
                                                              'datev_steuer_erforderlich': True,
                                                              })
        line = {'name': 'SALES',
                'debit': 0.00,
                'credit': 1000.00,
                'account_id': self.account_id_sales,
                'ecofi_taxid': self.tax_id,
                'move_id': move_id,
                'ecofi_account_counterpart': self.account_id_recievable,
                }   
        self.account_move_line.create(cr, uid, line)
        line = {'name': 'DEBIT',
                'debit': 1190.00,
                'credit': 0.00,
                'account_id': self.account_id_recievable,
                'move_id': move_id,
                'ecofi_account_counterpart': self.account_id_recievable,
                }
        self.account_move_line.create(cr, uid, line)
        self.account_move.button_validate(cr, uid, [move_id])
        
    def test_05_testing_manual_correct_error(self):
        """ Testing if a not right configured manual booking is working"""
        cr, uid = self._cr, self._uid
        move = {'name': 'TESTMOVE01',
                'journal_id': self.journal_sale_id,
                'state': 'draft',
                'ecofi_buchungstext': 'CHECK BUCHUNGSTEXT',
                'ecofi_manual': True
                }
        move_id = self.account_move.create(cr, uid, move)
        line = {'name': 'TAX',
                'debit': 0.00,
                'credit': 190.00,
                'account_id': self.account_id_vat,
                'move_id': move_id,
                'ecofi_account_counterpart': self.account_id_recievable,
                }
        self.account_move_line.create(cr, uid, line)
        self.account.write(cr, uid, [self.account_id_sales], {'automatic': False,
                                                              'datev_steuer_erforderlich': True,
                                                              })
        line = {'name': 'SALES',
                'debit': 0.00,
                'credit': 1000.00,
                'account_id': self.account_id_sales,
                'ecofi_taxid': self.tax_id,
                'move_id': move_id,
                }   
        self.account_move_line.create(cr, uid, line)
        line = {'name': 'DEBIT',
                'debit': 1190.00,
                'credit': 0.00,
                'account_id': self.account_id_recievable,
                'move_id': move_id,
                'ecofi_account_counterpart': self.account_id_recievable,
                }
        self.account_move_line.create(cr, uid, line)
        try:
            self.account_move.button_validate(cr, uid, [move_id])
            self.assertEqual(True, False,"The move should not have been validatet!")
        except:
            pass

    def test_05_testing_manual_correct_error2(self):
        """ Testing if a not right configured manual booking is working"""
        cr, uid = self._cr, self._uid
        move = {'name': 'TESTMOVE01',
                'journal_id': self.journal_sale_id,
                'state': 'draft',
                'ecofi_buchungstext': 'CHECK BUCHUNGSTEXT',
                'ecofi_manual': True
                }
        move_id = self.account_move.create(cr, uid, move)
        line = {'name': 'TAX',
                'debit': 0.00,
                'credit': 190.00,
                'account_id': self.account_id_vat,
                'move_id': move_id,
                'ecofi_account_counterpart': self.account_id_recievable,
                }
        self.account_move_line.create(cr, uid, line)
        self.account.write(cr, uid, [self.account_id_sales], {'automatic': False,
                                                              'datev_steuer_erforderlich': True,
                                                              })
        line = {'name': 'SALES',
                'debit': 0.00,
                'credit': 1000.00,
                'account_id': self.account_id_sales,
                'ecofi_taxid': self.tax_id,
                'move_id': move_id,
                'ecofi_account_counterpart': self.account_id_sales,
                }   
        self.account_move_line.create(cr, uid, line)
        line = {'name': 'DEBIT',
                'debit': 1190.00,
                'credit': 0.00,
                'account_id': self.account_id_recievable,
                'move_id': move_id,
                'ecofi_account_counterpart': self.account_id_recievable,
                }
        self.account_move_line.create(cr, uid, line)
        try:
            self.account_move.button_validate(cr, uid, [move_id])
            self.assertEqual(True, False,"The move should not have been validatet!")
        except:
            pass
