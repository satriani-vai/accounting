# -*- coding: utf-8 -*-
# This file is part of Odoo. The COPYRIGHT file at the top level of
# this module contains the full copyright and licensing details.

import base64
import cStringIO
import csv
import sys
import time
import traceback
from datetime import datetime
from decimal import Decimal

from openerp import fields, osv, models
from openerp.tools import ustr
from openerp.tools.translate import _


class ImportDatev(models.Model):
    """
    The class import.datev manages the reimport of datev buchungsstapel (account.moves)
    """
    _name = 'import.datev'

    name = fields.Char('Name', readonly=True, default=lambda self: self.env['ir.sequence'].get('datev.import.sequence') or '-')
    description = fields.Char('Description', required=True)
    company_id = fields.Many2one('res.company', "Company", required=True)
    datev_ascii_file = fields.Binary('DATEV ASCII File')
    journal_id = fields.Many2one('account.journal', 'Journal', required=True)
    one_move = fields.Boolean('In one move?')
    start_date = fields.Date('Start Date', required=True, default=fields.Date.today())
    end_date = fields.Date('End Date', required=True, default=fields.Date.today())
    log_line = fields.One2many('import.datev.log', 'parent_id', 'Log')
    account_moves = fields.One2many('account.move', 'import_datev', 'Account Moves')
    state = fields.Selection([('draft', 'Draft'),
                              ('error', 'Error'),
                              ('imported', 'Imported'),
                              ('booking_error', 'Booking Error'),
                              ('booked', 'Booked')], 'Status', select=True, readonly=True, default='draft')

    def _lookup_erpvalue(self, cr, uid, field_config, value, context=None):
        """ Method to get the ERP ID for the Object and the given Value
        
        :param field_config: Dictionary of the field containing the erpobject and the erpfield
        :param value: Domain Search Value
        """
        try:
            if field_config['erpfield'] == 'buchungsschluessel':
                if value in ['SD', '40']:
                    return value
                else:
                    try:
                        value = int(value)
                    except:
                        return False
            args = 'domain' in field_config and field_config['domain'] or []
            args.append((field_config['erpfield'], '=', value))
            value = self.pool.get(field_config['erpobject']).search(cr, uid, args, context=context)
            if len(value) == 1:
                return value[0]
            else:
                return False
        except:
            return False

    def _convert_to_unicode_dict(self, cr, uid, importcsv, import_config, import_struct, errorlist, start_date, end_date, context={}):
        """ Method that imports the CSV File using the import_config and import struct rules. The CSV File is than converted
        to a unicode encoded Dictionary that can be used from the following functions
        
        :param importcsv: CSV File to be imported
        :param import_config: Import Config Dictionary
        :param import_struct: Import Structure Dictionary
        :param errorlist: Listobject that handles errors through the whole function
        """
        delimiter = import_config['delimiter']
        encoding = import_config['encoding']
        headerrow = import_config['headerrow']
        quotechar = import_config['quotechar']
        delimiter = delimiter.encode(encoding)
        importliste = csv.reader(cStringIO.StringIO(importcsv), delimiter=delimiter, quotechar=quotechar)
        # linecounter = 0        
        date_year = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y')
        vorlauf = {'header': [],
                   'lines': []
                   }
        for linecounter, line in enumerate(importliste, start=1):
            print '### line', linecounter, headerrow, line
            if linecounter == headerrow:
                for spalte in line:
                    try:
                        vorlauf['header'].append(spalte.decode(encoding).encode('UTF-8'))
                    except:
                        errorlist.append({'line': linecounter,
                                          'name': _('Decoding ERROR'),
                                          'beschreibung': _("Headerline %s could not be converted from format %s!") % (spalte, encoding)})  # pylint: disable-msg=C0301
            if linecounter > headerrow:
                thisline = []
                for spalte in line:
                    try:
                        thisline.append(spalte.decode(encoding).encode('UTF-8'))
                    except:
                        errorlist.append({'line': linecounter,
                                          'name': _("Decoding ERROR"),
                                          'beschreibung': _("Dataline %s could not be converted from format %s!") % (linecounter, encoding)})  # pylint: disable-msg=C0301
                        break
                vorlauf['lines'].append(thisline)
            linecounter += 1

        if len(vorlauf['header']) != len(list(set(vorlauf['header']))):
            errorlist.append({'line': 2,
                              'name': _("Attributename twice in Header"),
                              'beschreibung': _("The Attributename must be unique in the header")})
        print '### errorlist 1', len(errorlist)

        for key in import_struct.keys():
            headercount = 0
            # print "### vorlauf['header']", vorlauf['header']
            for header in vorlauf['header']:
                if header == import_struct[key]['csv_name']:
                    import_struct[key]['csv_row'] = headercount
                headercount += 1
        for key in import_struct.keys():
            if import_struct[key]['csv_row'] is False:
                errorlist.append({'line': headerrow,
                                  'name': _("Attribute not found"),
                                  'beschreibung': _("Attribute %s could not be found") % (import_struct[key]['csv_name'])})

        print '### errorlist 2', len(errorlist)

        linecounter = headerrow
        data_list = []
        for line in vorlauf['lines']:
            skip = False
            for key in import_struct.keys():
                if 'skipon' in import_struct[key]:
                    if line[import_struct[key]['csv_row']] in import_struct[key]['skipon']:
                        skip = True
            if skip:
                thisvalue = {}
                thisvalue['skip'] = True
                data_list.append(thisvalue)
                continue
            linecounter += 1
            spaltenvalues = {}
            print '-------------------------------------------------------------------'

            for key in import_struct.keys():
                thisvalue = False
                if line[import_struct[key]['csv_row']] == '':
                    if 'default' in import_struct[key]:
                        line[import_struct[key]['csv_row']] = import_struct[key]['default']
                if line[import_struct[key]['csv_row']] == '' and import_struct[key]['required'] is False:
                    spaltenvalues[key] = thisvalue
                    continue

                print '### ', import_struct[key]['csv_name'], '|', import_struct[key]['required'], '|', import_struct[key]['csv_row'], '|', line[import_struct[key]['csv_row']]
                if line[import_struct[key]['csv_row']] == '' and import_struct[key]['required'] is True:
                    print '### error: no column and required'
                    errorlist.append({'line': linecounter,
                                      'name': _("Attribute is required"),
                                      'beschreibung': _("Attribute %s in line %s is required but not filled") % (import_struct[key]['csv_name'], linecounter)})  # pylint: disable-msg=C0301
                    spaltenvalues[key] = thisvalue
                    continue
                try:
                    if import_struct[key]['type'] == 'string':
                        thisvalue = str(line[import_struct[key]['csv_row']])
                        if 'zfill' in import_struct[key]:
                            thisvalue = thisvalue.zfill(import_struct[key]['zfill'])
                    elif import_struct[key]['type'] == 'integer':
                        thisvalue = int(line[import_struct[key]['csv_row']])
                    elif import_struct[key]['type'] == 'decimal':
                        decimalvalue = line[import_struct[key]['csv_row']]
                        if import_struct[key]['decimalformat'][0]:
                            decimalvalue = decimalvalue.replace(import_struct[key]['decimalformat'][0], '')
                        thisvalue = Decimal(decimalvalue.replace(import_struct[key]['decimalformat'][1], '.'))
                    elif import_struct[key]['type'] == 'date':
                        if import_struct[key]['dateformat'] == '%d%m':
                            dateformat = '%Y%d%m'
                            line[import_struct[key]['csv_row']] = date_year + line[import_struct[key]['csv_row']].zfill(4)
                        else:
                            dateformat = import_struct[key]['dateformat']
                        # print ""
                        # print "11111111"
                        # print dateformat
                        # print line[import_struct[key]['csv_row']]
                        thisvalue = datetime.strptime(line[import_struct[key]['csv_row']], dateformat)
                        # print "THISVALUE", thisvalue
                        # print start_date
                        # print type(start_date)
                        # print end_date
                        # print type(end_date)
                        # print datetime.strptime(start_date + " 00:00", "%Y-%m-%d %H:%M")
                        # print datetime.strptime(end_date + " 23:59", "%Y-%m-%d %H:%M")
                        # print datetime.strptime(start_date + " 00:00", "%Y-%m-%d %H:%M") > thisvalue
                        # print datetime.strptime(end_date + " 23:59", "%Y-%m-%d %H:%M") < thisvalue
                        # print "1.1"
                        # print datetime.min.time()
                        # print datetime.combine(start_date, datetime.min.time())
                        # datetime.datetime.combine(dateobject, datetime.time.min)
                        # if datetime.combine(start_date, datetime.min.time()) > thisvalue or datetime.combine(end_date, datetime.max.time()) < thisvalue:
                        # datetime.strptime("20.04.14" + " 00:00", "%d.%m.%y %H:%M")
                        if datetime.strptime(start_date + " 00:00", "%Y-%m-%d %H:%M") > thisvalue or datetime.strptime(end_date + " 23:59", "%Y-%m-%d %H:%M") < thisvalue:
                            print "2"
                            errorlist.append({'line': linecounter,
                                              'name': _("Date is not in the selected date range!"),
                                              'beschreibung': _("Date %s in line %s is not in the selected date range!") % (thisvalue.strftime('%d.%m.%Y'), import_struct[key]['csv_name'])})  # pylint: disable-msg=E1103,C0301
                        print "3"
                    else:
                        errorlist.append({'line': linecounter,
                                          'name': _("Attributetype could not be resolved"),
                                          'beschreibung': _("Attributetype %s could not be resolved!") % (import_struct[key]['type'])})
                    if import_struct[key].has_key('convert_method'):
                        thisvalue = import_struct[key]['convert_method'](cr, uid, thisvalue)

                except:
                    errorlist.append({'line': linecounter,
                                      'name': _("Attribute could not be converted!"),
                                      'beschreibung': _("Attribute %s in line %s could not be converted to type: %s!") % (import_struct[key]['csv_name'], linecounter, import_struct[key]['type'])})  # pylint: disable-msg=C0301
                if thisvalue is not False:
                    if import_struct[key].has_key('erplookup'):
                        if import_struct[key]['erplookup'] is True:
                            newvalue = self._lookup_erpvalue(cr, uid, import_struct[key], thisvalue, context=context)
                            if newvalue is False:
                                errorlist.append({'line': linecounter,
                                                  'name': _("ERP object not found"),
                                                  'beschreibung': _("The ERP object for Value %s (%s) in line %s could not be resolved!") % (thisvalue, import_struct[key]['csv_name'], linecounter)})  # pylint: disable-msg=C0301
                                thisvalue = newvalue
                            else:
                                thisvalue = newvalue
                spaltenvalues[key] = thisvalue
            data_list.append(spaltenvalues)

        print '### errorlist 3', len(errorlist)
        return data_list, errorlist

    def unlink(self, cr, uid, ids, context=None):
        """ Import can only be unlinked if State is draft
        """
        for thisimport in self.browse(cr, uid, ids, context):
            if thisimport.state != 'draft':
                raise osv.except_osv(_('Warning!'), _('Import can only be deleted in state draft!'))
        return super(import_datev, self).unlink(cr, uid, ids, context)

    def reset_import(self, cr, uid, ids, context={}):
        """ Method to reset the import
        #. Unreconcile all reconciled imported Moves
        #. Cancel all imported moves not in state draft
        #. Delete all imported moves
        #. Delete all Importloglines
        #. Set Import state to draft 
        """
        for datev_import in self.browse(cr, uid, ids, context=context):
            try:
                context['delete_none'] = True
                for move in datev_import.account_moves:
                    for line in move.line_ids:
                        if line.reconciled:
                            self.pool.get('account.move.line')._remove_move_reconcile(cr, uid, move_ids=[line.id], context=context)
                    if move.state != 'draft':
                        self.pool.get('account.move').button_cancel(cr, uid, [move.id], context=context)
                    self.pool.get('account.move').unlink(cr, uid, [move.id], context=context)
                for log in datev_import.log_line:
                    self.pool.get('import.datev.log').unlink(cr, uid, [log.id], context=context)
                self.write(cr, uid, [datev_import.id], {'state': 'draft'}, context=context)
            except:
                tb_s = reduce(lambda x, y: x + y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))  # @UndefinedVariable # pylint: disable-msg=C0301
                self.pool.get('import.datev.log').create(cr, uid, {'parent_id': datev_import.id,
                                                                   'name': _("%s could not be booked, ERP ERROR: %s") % (ustr(move.name), tb_s),  # pylint: disable-msg=C0301
                                                                   'state': 'error',})
            error = True
        return True

    def search_partner(self, cr, uid, konto, context={}):
        """ Get the partner for the specified account
        
        :param konto: ID of the account
        """
        thissql = """select res_id from ir_property where name like 'property_account%' 
                        and res_id like 'res.partner%' and value_reference = 'account.account,""" + str(konto) + "';"
        cr.execute(thissql)
        partner_ids = []
        for thisres in cr.fetchall():
            partner_ids.append(int(thisres[0].split(',')[1]))
        if len(partner_ids) == 1:
            return partner_ids[0]
        else:
            return False

    def get_partner(self, cr, uid, line, context={}):
        """ Search Partner for the line

        :param line: Move Line
        """
        partner_id = False
        if line['konto_object'].user_type_id.type in ('receivable', 'payable'):
            partner_id = self.search_partner(cr, uid, line['konto_object'].id, context=context)
        if partner_id is False:
            if line['gegenkonto_object'].user_type_id.type in ('receivable', 'payable'):
                partner_id = self.search_partner(cr, uid, line['gegenkonto_object'].id, context=context)
        return partner_id

    def get_import_defaults(self, datev_import):
        """ Default import_config and import_struct
        """
        import_config = {}
        import_config['delimiter'] = ";"
        import_config['encoding'] = 'iso-8859-1'
        import_config['quotechar'] = '"'
        import_config['headerrow'] = 2
        import_config['journal_id'] = datev_import.journal_id.id
        import_config['company_id'] = datev_import.company_id.id
        import_config['company_currency_id'] = datev_import.company_id.currency_id.id
        import_config['skonto_account'] = 499
        import_config['date'] = datev_import.start_date
        import_struct = {
            'gegenkonto': {'csv_name': 'Gegenkonto',
                           'csv_row': False,
                           'type': 'string',
                           'required': True,
                           'erplookup': True,
                           'erpobject': 'account.account',
                           'erpfield': 'code',
                           'domain': [],
                           'zfill': 4,
                           },
            'konto': {'csv_name': 'Konto',
                      'csv_row': False,
                      'type': 'string',
                      'required': True,
                      'erplookup': True,
                      'erpobject': 'account.account',
                      'erpfield': 'code',
                      'domain': [],
                      'zfill': 4,
                      },
            'wkz': {'csv_name': 'WKZ',
                    'csv_row': False,
                    'type': 'string',
                    'required': False,
                    'erplookup': True,
                    'erpobject': 'res.currency',
                    'erpfield': 'name',
                    },
            'buschluessel': {'csv_name': 'BU',
                             'csv_row': False,
                             'type': 'string',
                             'required': False,
                             'erplookup': True,
                             'erpobject': 'account.tax',
                             'erpfield': 'buchungsschluessel'
                             },
            'belegdatum': {'csv_name': 'Datum',
                           'csv_row': False,
                           'type': 'date',
                           'required': True,
                           'dateformat': '%d.%m.%Y',
                           },
            'beleg1': {'csv_name': 'Belegfeld 1',
                       'csv_row': False,
                       'type': 'string',
                       'required': False,
                       },
            'beleg2': {'csv_name': 'Belegfeld 2',
                       'csv_row': False,
                       'type': 'string',
                       'required': False,
                       },
            'umsatz': {'csv_name': 'Umsatz',
                       'csv_row': False,
                       'type': 'decimal',
                       'required': True,
                       'decimalformat': ('.', ',')
                       },
            'skonto': {'csv_name': 'Skonto',
                       'csv_row': False,
                       'type': 'decimal',
                       'required': False,
                       'decimalformat': (False, ',')
                       },
            'buchungstext': {'csv_name': 'Buchungstext',
                             'csv_row': False,
                             'type': 'string',
                             'required': False,
                             'skipon': ['Gruppensumme', 'Abstimmsumme'],
                             },
            'sollhaben': {'csv_name': 'S/H',
                          'csv_row': False,
                          'type': 'string',
                          'required': True,
                          'default': 'S'
                          },
        }
        return import_config, import_struct

    def create_account_move(self, cr, uid, datev_import, import_config, line, linecounter, move_id=False, manual=False, context={}):
        """ Create the move for the import line
        
        :param datev_import: Datev Import
        :param import_config: Import Config
        :param line: Move Line
        :param linecounter: Counter of the move line
        """
        partner_id = self.get_partner(cr, uid, line, context=context)
        if move_id is False:
            if line['beleg1'] and line['beleg2']:
                ref = ", ".join([line['beleg1'], line['beleg2']])
            elif line['beleg1'] and not line['beleg2']:
                ref = line['beleg1']
            elif not line['beleg1'] and line['beleg2']:
                ref = line['beleg2']
            else:
                ref = ''
            move = {
                'import_datev': datev_import.id,
                'name': line['name'],
                'ref': ref,
                'journal_id': datev_import.journal_id.id,
                'company_id': import_config['company_id'],
                'date': line['belegdatum'].strftime('%Y-%m-%d'),
                'ecofi_buchungstext': line['buchungstext'],
                'ecofi_manual': manual,
                'partner_id': partner_id,
            }
            move_id = self.pool.get('account.move').create(cr, uid, move, context=context)

        return move_id, partner_id

    def create_move_line_dict(self, cr, uid, move, import_config, context=None):
        move_line_dict = {
            'company_id': import_config['company_id'],
            'partner_id': move['partner_id'],
            'credit': str(move['credit']),
            'debit': str(move['debit']),
            'journal_id': import_config['journal_id'] and import_config['journal_id'] or False,
            # 'state': 'valid',
            'account_id': move['account_id'],
            'date': move['date'],
            'name': move['name'],
            'move_id': move['move_id'],
            'ecofi_account_counterpart': move['ecofi_account_counterpart'],
            'ecofi_taxid': 'ecofi_taxid' in move and move['ecofi_taxid'] or False,
            'amount_currency': 'amount_currency' in move and move['amount_currency'] or False,
            'currency_id': 'currency_id' in move and move['currency_id'] or False,
            'date_maturity': 'date_maturity' in move and move['date_maturity'] or False,
            # 'tax_code_id': 'tax_code_id' in move and move['tax_code_id'] or False,
            # 'tax_amount': 'tax_amount' in move and move['tax_amount'] or False,
            'analytic_account_id': False,
            'quantity': 1.0,
            'ecofi_bu': 'ecofi_bu' in move and move['ecofi_bu'] or '',
            'product_id': False,
        }
        return move_line_dict

    def compute_currency(self, cr, uid, move_line, line, import_config, context=None):
        if context is None:
            context = {}
        cur_obj = self.pool.get('res.currency')
        if line['wkz'] != import_config['company_currency_id']:
            context.update({'date': line['belegdatum'].strftime('%Y-%m-%d') or time.strftime('%Y-%m-%d')})
            move_line['currency_id'] = line['wkz']
            move_line['amount_currency'] = move_line['debit'] - move_line['credit']
            move_line['debit'] = Decimal(str(cur_obj.compute(cr, uid, line['wkz'], import_config['company_currency_id'], float(move_line['debit']), context=context)))
            move_line['credit'] = Decimal(str(cur_obj.compute(cr, uid, line['wkz'], import_config['company_currency_id'], float(move_line['credit']), context=context)))
        #             if 'tax_amount' in move_line:
        #                 move_line['tax_amount'] = Decimal(str(cur_obj.compute(cr, uid, line['wkz'], import_config['company_currency_id'], float(move_line['tax_amount']), context=context)))
        return move_line

    def create_main_lines(self, cr, uid, line, thismove, partner_id, import_config, move_lines=None, context=None):
        """ Create the Main booking Lines
         
        :param line: Import Line
        :param thismove: MoveID
        :param move_lines: MoveLines
        """
        if move_lines is None:
            move_lines = []
        if context is None:
            context = {}
        if line['sollhaben'].upper() == 'S':
            debit = line['umsatz']
            credit = Decimal('0.0')
        else:
            debit = Decimal('0.0')
            credit = line['umsatz']
        gegenmove = {'credit': debit,
                     'debit': credit,
                     'account_id': line['gegenkonto'],
                     'date': line['belegdatum'].strftime('%Y-%m-%d'),
                     'move_id': thismove,
                     'name': 'Gegenbuchung',
                     'partner_id': partner_id,
                     'ecofi_account_counterpart': line['gegenkonto'],
                     }
        mainmove = {'credit': credit,
                    'debit': debit,
                    'account_id': line['konto'],
                    'date': line['belegdatum'].strftime('%Y-%m-%d'),
                    'move_id': thismove,
                    'name': 'Buchung',
                    'partner_id': partner_id,
                    'ecofi_account_counterpart': line['gegenkonto'],
                    }
        if line['buschluessel'] is False and line['konto_object'].automatic:
            line['buschluessel'] = line['konto_object'].datev_steuer and line['konto_object'].datev_steuer.id or False
        if line['buschluessel']:
            mainmove, taxmoves = self.create_tax_line(cr, uid, mainmove, import_config, line, context=context)
            for taxmove in taxmoves:
                move_lines.append(self.compute_currency(cr, uid, taxmove, line, import_config, context=context))
        gegenmove = self.compute_currency(cr, uid, gegenmove, line, import_config, context=context)
        mainmove = self.compute_currency(cr, uid, mainmove, line, import_config, context=context)
        move_lines.append(self.create_move_line_dict(cr, uid, gegenmove, import_config, context=context))
        move_lines.append(self.create_move_line_dict(cr, uid, mainmove, import_config, context=context))
        return move_lines

    def create_tax_line(self, cr, uid, mainmove, import_config, line, context=None):
        tax_obj = self.pool.get('account.tax')
        taxmoves = []
        if line['buschluessel'] in ['40', 'SD']:
            mainmove['ecofi_bu'] = line['buschluessel']
            mainmove['ecofi_taxid'] = line['konto_object'].datev_steuer and line['konto_object'].datev_steuer.id or False
            return mainmove, taxmoves
        tax_id = tax_obj.browse(cr, uid, line['buschluessel'], context=context)
        total = float(mainmove['debit'] + mainmove['credit'])
        if mainmove['credit'] == Decimal('0.00'):  # Es liegt eine
            # base_code = 'ref_base_code_id'
            # tax_code = 'ref_tax_code_id'
            account_id = 'account_id'
            # base_sign = 'ref_base_sign'
            # tax_sign = 'ref_tax_sign'
        else:
            # base_code = 'base_code_id'
            # tax_code = 'tax_code_id'
            account_id = 'account_id'
            # base_sign = 'base_sign'
            # tax_sign = 'tax_sign'
        # for tax in tax_obj.compute_all_inv(cr, uid, [tax_id], total, 1.00, force_excluded=True).get('taxes'):
        #     if mainmove['credit'] == Decimal('0.00'):
        #         tax_credit = 0.00
        #         tax_debit = tax['amount']
        #     else:
        #         tax_credit = tax['amount']
        #         tax_debit = 0.00
        #     data = {
        #         'move_id': mainmove['move_id'],
        #         'name': ustr(mainmove['name'] or '') + ' ' + ustr(tax['name'] or ''),
        #         'date': mainmove['date'],
        #         'partner_id': mainmove['partner_id'] and mainmove['partner_id'] or False,
        #         'ref': 'ref' or False,
        #         'account_tax_id': False,
        #         #'tax_code_id': tax[tax_code],
        #         #'tax_amount': tax[tax_sign] * tax['amount'],
        #         'account_id': tax[account_id],
        #         'credit': tax_credit,
        #         'debit': tax_debit,
        #         'ecofi_account_counterpart': line['gegenkonto'],
        #     }
        #     mainmove['credit'] -= Decimal(str(data['credit']))
        #     mainmove['debit'] -= Decimal(str(data['debit']))
        #     #mainmove['tax_code_id'] = tax[base_code]
        #     #mainmove['tax_amount'] = Decimal(str(tax[base_sign] * float(mainmove['credit'] + mainmove['debit'])))
        #     mainmove['ecofi_taxid'] = line['buschluessel']
        #     taxmoves.append(data)
        return mainmove, taxmoves

    def do_import(self, cr, uid, ids, context={}, import_config={}, import_struct={}):
        """Method to Start the Import of the Datev ASCII File Containing the Datev Moves
        :param import_config: Dictionary Containing the Config parameterws
        :param import_struct: Dictionary Containing the Structure of the ASCII FIle
        """
        errorlist = []
        for datev_import in self.browse(cr, uid, ids, context=context):
            import_config, import_struct = self.get_import_defaults(datev_import)
            self.reset_import(cr, uid, ids, context)
            self.pool.get('import.datev.log').create(cr, uid, {'parent_id': datev_import.id,
                                                               'name': _("Import started!"),
                                                               'state': 'info',
                                                               })
            if datev_import.datev_ascii_file:
                importcsv = base64.decodestring(datev_import.datev_ascii_file)
                vorlauf, errorlist = self._convert_to_unicode_dict(cr, uid, importcsv,
                                                                   import_config,
                                                                   import_struct,
                                                                   errorlist,
                                                                   datev_import.start_date,
                                                                   datev_import.end_date,
                                                                   context=context)

                if len(errorlist) == 0:
                    linecounter = 0
                    thismove = False
                    for line in vorlauf:
                        linecounter += 1
                        if 'skip' in line:
                            self.pool.get('import.datev.log').create(cr, uid, {'parent_id': datev_import.id,
                                                                               'name': _("Line: %s has been skipped") % (ustr(linecounter + import_config['headerrow'])),  # pylint: disable-msg=C0301
                                                                               'state': 'standard',
                                                                               })
                            continue
                        line['gegenkonto_object'] = self.pool.get('account.account').browse(cr, uid, line['gegenkonto'], context=context)
                        line['konto_object'] = self.pool.get('account.account').browse(cr, uid, line['konto'], context=context)
                        if datev_import.one_move is False:
                            thismove = False
                            manual = False
                        else:
                            manual = True

                        next_seq = datev_import.journal_id.sequence_id.next_by_id()
                        line['name'] = next_seq
                        if not line.get('wkz', False):
                            currency_id = datev_import.journal_id.currency_id or datev_import.company_id.currency_id
                            line['wkz'] = currency_id.id

                        thismove, partner_id = self.create_account_move(cr, uid, datev_import,
                                                                        import_config, line, linecounter, move_id=thismove, manual=manual, context=context)
                        move_lines = self.create_main_lines(cr, uid, line, thismove, partner_id, import_config, context=context)
                        move_line_ids = []
                        for move in move_lines:
                            context['check_move_validity'] = False
                            move['credit'] = Decimal(move['credit'])
                            move['debit'] = Decimal(move['debit'])
                            move_line_ids.append(self.pool.get('account.move.line').create(cr, uid, move, context=context))
                            context['check_move_validity'] = True
                        #                         thismove, partner_id = self.create_account_move(cr, uid, datev_import,
                        #                                                                         import_config, line, linecounter, move_id=thismove, manual=manual, context=context)
                        #                         print "13"
                        #                         self.pool.get('account.move.line').write(cr, uid, move_line_ids, {'partner_id': partner_id, 'move_id': thismove})
                        #                         print "14"
                        #
                        #                         self.pool.get('account.move').validate(cr, uid, [thismove], context)
                        self.pool.get('import.datev.log').create(cr, uid, {'parent_id': datev_import.id,
                                                                           'name': _("Line: %s has been imported") % (ustr(linecounter + import_config['headerrow'])),  # pylint: disable-msg=C0301
                                                                           'state': 'standard',
                                                                           })
                    if len(errorlist) != 0:
                        for line in errorlist:
                            self.pool.get('import.datev.log').create(cr, uid, {'parent_id': datev_import.id,
                                                                               'name': _("%s line: %s") % (ustr(line['beschreibung']), ustr(line['line'])),  # pylint: disable-msg=C0301
                                                                               'state': 'error',
                                                                               })
                        self.write(cr, uid, [datev_import.id], {'state': 'error'})
                    else:
                        self.write(cr, uid, [datev_import.id], {'state': 'imported'})

                else:
                    for line in errorlist:
                        self.pool.get('import.datev.log').create(cr, uid, {'parent_id': datev_import.id,
                                                                           'name': _("%s Line: %s") % (ustr(line['beschreibung']), ustr(line['line'])),  # pylint: disable-msg=C0301
                                                                           'state': 'error',})
                    self.write(cr, uid, [datev_import.id], {'state': 'error'})
        return True

    def confirm_booking(self, cr, uid, ids, context=None):
        """ Confirm the booking after all moves have been imported
         
        :param ids: List of Datev Imports
        """
        for thisimport in self.browse(cr, uid, ids, context=context):
            error = False
            for move in thisimport.account_moves:
                if move.state == 'draft':
                    try:
                        self.pool.get('account.move').post(cr, uid, [move.id], context=context)
                        self.pool.get('import.datev.log').create(cr, uid, {'parent_id': thisimport.id,
                                                                           'name': _("%s booked successful.") % (ustr(move.name)),  # pylint: disable-msg=C0301
                                                                           'state': 'standard',
                                                                           })
                    except:
                        tb_s = reduce(lambda x, y: x + y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))  # @UndefinedVariable # pylint: disable-msg=C0301
                        self.pool.get('import.datev.log').create(cr, uid, {'parent_id': thisimport.id,
                                                                           'name': _("%s could not be booked, ERP ERROR: %s") % (ustr(move.name), tb_s),  # pylint: disable-msg=C0301
                                                                           'state': 'error',
                                                                           })
                        error = True
            if error is False:
                self.write(cr, uid, [thisimport.id], {'state': 'booked'})
            else:
                self.write(cr, uid, [thisimport.id], {'state': 'booking_error'})
        return True


class ImportDatevLog(models.Model):
    """
    Logzeilenobject des Imports
    """
    _name = 'import.datev.log'
    _order = 'id desc'

    name = fields.Text('Name')
    parent_id = fields.Many2one('import.datev', 'Import', ondelete='cascade')
    date = fields.Datetime('Time', readonly=True, default=lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'))
    state = fields.Selection([('info', 'Info'), ('error', 'Error'), ('standard', 'Ok')],
                             'State', select=True, readonly=True, default='info')
