# -*- encoding: utf-8 -*-
""" The ecofi module provides the basic objects to export account moves as csv data
"""
##############################################################################
#    ecoservice_financeinterface
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
#    This program based on OpenERP.
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
##############################################################################
from openerp.osv import fields, osv
from openerp.tools.translate import _
import base64
import cStringIO
import csv
from decimal import Decimal
from openerp.tools import ustr
from datetime import datetime
import re


class ecofi(osv.osv):
    """
    The class ecofi is the central object to generate a csv file for the selected moves that
    can be used to be imported in the different financial programms
    """
    _name = 'ecofi'
    _description = 'Ecoservice Financial Interface'
    _zahlungsbedingungen = []
    _columns = {
                'name': fields.char('Exportname', size=64, required=True, readonly=True),
                'journale': fields.char('Journals', size=128, required=True, readonly=True),
                'zeitraum': fields.char('Zeitraum', size=128, required=True, readonly=True),
                'csv_file': fields.binary('Export CSV', readonly=True),
                'csv_file_fname': fields.char('Stored Filename', size=256),
                'account_moves': fields.one2many('account.move', 'vorlauf_id', 'Account Moves', readonly=True),
                'partner_error_ids': fields.many2many('res.partner', 'ecofi_res_partner_error_rel',
                    'ecofi_id', 'res_partner_id', 'Partner Errors'),
                'move_error_ids': fields.many2many('account.move', 'ecofi_eccount_move_error_rel',
                    'ecofi_id', 'account_move_id', 'Move Errors'),
                'note': fields.text('Comment'),
    }

    def replace_non_ascii_characters(self, text, replacement='?'):
        return re.sub(r'[^\x00-\x7F]+', replacement, text)

    def copy(self, cr, uid, id, default=None, context=None):
        """ Prevent the copy of the object

        :param cr: the current row, from the database cursor
        :param uid: the current user’s ID for security checks
        :param id: Id of the ecofi object
        :param context: context arguments, like lang, time zone
        :param default: default values
        """
        raise osv.except_osv(_('Warning!'), _('Exports cannot be duplicated.'))

    def is_taxline(self, cr, account_id):
        """Method to check if the selected account is a tax account

        :param cr: the current row, from the database cursor
        :param account_id: Id of the account to analyse
        """
        cr.execute("Select id from account_tax where account_id = %s or refund_account_id = %s" % (account_id, account_id))
        taxids = map(lambda x: x[0], cr.fetchall())
        if len(taxids) > 0:
            return True
        else:
            return False

    def get_tax_account(self, cr, uid, line, context=None):
        """ Calculates and returns the account of tax that has to be considered for an account_move_line.
        :param cr: the current row, from the database cursor
        :param uid: the current user’s ID for security checks
        :param line: account_move_line
        :param context: context arguments, like lang, time zone
        """
        if context is None:
            context = {}
        linetax = self.get_line_tax(cr, uid, line)
        tax_account = False
        if linetax:
            total = line.credit - line.debit
            if total <= 0.00:
                tax_account = linetax.refund_account_id
            else:
                tax_account = linetax.account_id
        return tax_account
    
    def get_tax(self, cr, account_id):
        """Method to get the tax for the selected account

        :param cr: the current row, from the database cursor
        :param account_id: Id of the account to analyse
        """
        cr.execute("Select id from account_tax where account_id = %s or refund_account_id = %s" % (account_id, account_id))
        taxids = map(lambda x: x[0], cr.fetchall())
        return taxids

    def get_line_tax(self, cr, uid, line):
        """returns the tax used in the line

        :param cr: the current row, from the database cursor
        :param account_id: Id of the account to analyse
        """
        linetax = False
        if line.tax_line_id:
            linetax = line.tax_line_id
        if line.ecofi_taxid:
            linetax = line.ecofi_taxid
        return linetax

    def calculate_tax(self, cr, uid, line, context=None):
        """ Calculates and returns the amount of tax that has to be considered for an account_move_line. The calculation
        always uses the _compute method of the account.tax object wich returns the tax as if it was excluded.

        :param cr: the current row, from the database cursor
        :param uid: the current user’s ID for security checks
        :param line: account_move_line
        :param context: context arguments, like lang, time zone
        """
        if context is None:
            context = {}
        linetax = self.get_line_tax(cr, uid, line)
        texamount = 0
        if linetax:
            if 'waehrung' in context and context['waehrung']:
                amount = line.amount_currency
            else:
                amount = line.debit - line.credit
            return self.calc_tax(cr, uid, linetax, amount, context=context)
        else:
            if 'return_calc' in context and context['return_calc'] is True:
                return []
        return texamount
    
    def calc_tax(self, cr, uid,tax_object, amount, context=None):
        if context is None:
            context = {}
        texamount = 0
        if tax_object:
            taxes = tax_object.compute_all(amount)['taxes']
            if 'return_calc' in context and context['return_calc'] is True:
                return taxes
            for tex in taxes:
                texamount += tex['amount']
        else:
            if 'return_calc' in context and context['return_calc'] is True:
                return []
        return texamount

    def set_main_account(self, cr, uid, move, context=None):
        """ This methods sets the main account of the corresponding account_move

        :param cr: the current row, from the database cursor
        :param uid: the current user’s ID for security checks
        :param move: account_move
        :param context: context arguments, like lang, time zone

        How the Mainaccount is calculated (tax lines are ignored):

        1. Analyse the number of debit and credit lines.
        a. 1 debit, n credit lines: Mainaccount is the debitline account
        b. m debit, 1 credit lines: Mainaccount is the creditline account
        c. 1 debit, 1 credit lines: Mainaccount is the firstline account

        If there are m debit and n debitlines:
        a. Test if there is an invoice connected to the move_id and test if the invoice
            account_id is in the move than this is the mainaccount
        """
        context = context or dict()
        ecofikonto = False
        sollkonto = list()
        habenkonto = list()
        nullkonto = list()
        error = False
        ecofikonto_no_invoice = move.line_ids[0].account_id

        for line in move.line_ids:
            Umsatz = Decimal(str(line.debit)) - Decimal(str(line.credit))
            if Umsatz < 0:
                habenkonto.append(line.account_id)
            elif Umsatz > 0:
                sollkonto.append(line.account_id)
            else:
                nullkonto.append(line.account_id)
        if len(sollkonto) == 1 and len(habenkonto) == 1:
            ecofikonto = move.line_ids[0].account_id
        elif len(sollkonto) == 1 and len(habenkonto) > 1:
            ecofikonto = sollkonto[0]
        elif len(sollkonto) > 1 and len(habenkonto) == 1:
            ecofikonto = habenkonto[0]
        elif len(sollkonto) > 1 and len(habenkonto) > 1:
            if len(sollkonto) > len(habenkonto):
                habennotax = list()
                for haben in habenkonto:
                    if not self.is_taxline(cr, haben.id):
                        habennotax.append(haben)
                if len(habennotax) == 1:
                    ecofikonto = habennotax[0]
            elif len(sollkonto) < len(habenkonto):
                sollnotax = list()
                for soll in sollkonto:
                    if not self.is_taxline(cr, soll.id):
                        sollnotax.append(soll)
                if len(sollnotax) == 1:
                    ecofikonto = sollnotax[0]
        if not ecofikonto:
            if 'invoice' in context:
                invoice = context['invoice']
            else:
                invoice = self.pool.get('account.invoice').search(cr, uid, [('move_id', '=', move.id)])
            in_booking = False
            invoice_mainaccount = False
            if len(invoice) == 1:
                invoice_mainaccount = invoice.account_id
                for sk in sollkonto:
                    if sk == invoice_mainaccount:
                        in_booking = True
                        break
                for hk in habenkonto:
                    if hk == invoice_mainaccount:
                        in_booking = True
                        break
            if not in_booking and invoice:
                error = _(u"The main account of the booking could not be resolved, the move has %s credit- and %s debitlines!") % (len(sollkonto), len(habenkonto))
                error += "\n"
                ecofikonto = ecofikonto_no_invoice
            else:
                ecofikonto = invoice_mainaccount
        if ecofikonto:
            self.pool.get('account.move.line').write(cr, uid, [l.id for l in move.line_ids],
                                                     {'ecofi_account_counterpart': ecofikonto.id},
                                                     context=context)
        return error

    def generate_csv_move_lines(self, cr, uid, move, buchungserror, errorcount, thislog, thismovename, exportmethod,
                          partnererror, buchungszeilencount, bookingdict, context=None):
        """Method to be implemented for each Interface, generates the corresponding csv entries for each move

        :param cr: the current row, from the database cursor
        :param uid: the current user’s ID for security checks
        :param move: account_move
        :param buchungserror: list of the account_moves with errors
        :param errorcount: number of errors
        :param thislog: logstring wich contains error descriptions or infos
        :param thismovename: Internal name of the move (for error descriptions)
        :param exportmethod: brutto / netto
        :param partnererror: List of the partners with errors (eg. missing ustid)
        :param buchungszeilencount: total number of lines written
        :param bookingdict: Dictionary that contains generated Bookinglines and Headers
        :param context: context arguments, like lang, time zone
        """
        if context is None:
            context = {}
        return buchungserror, errorcount, thislog, partnererror, buchungszeilencount, bookingdict

    def generate_csv(self, cr, uid, ecofi_csv, bookingdict, log, context={}):
        """ Method to be implemented for each Interface, generates the corresponding csv entries for each move
        
        :param cr: the current row, from the database cursor
        :param uid: the current user’s ID for security checks
        :param ecofi_csv: object for the csv file
        :param bookingdict: Dictionary that contains generated Bookinglines and Headers
        :param log: logstring wich contains error descriptions or infos
        :param context: context arguments, like lang, time zone
        """
        return ecofi_csv, log
    
    def pre_export(self, cr, uid, account_move_ids, context={}):
        """ Method to call before the Import starts and the moves to export are going to be browsed
        
        :param cr: the current row, from the database cursor
        :param uid: the current user’s ID for security checks
        :param ecofi_csv: object for the csv file
        :param bookingdict: Dictionary that contains generated Bookinglines and Headers
        :param log: logstring wich contains error descriptions or infos
        :param context: context arguments, like lang, time zone
        """
        return True
                   
    def ecofi_buchungen(self, cr, uid, journal_ids=[], vorlauf_id=False, context={}, date_from=False, date_to=False):
        """ Method that generates the csv export by the given parameters
        
        :param cr: the current row, from the database cursor
        :param uid: the current user’s ID for security checks
        :param journal_ids: list of journalsIDS wich should be exported if the value is False all exportable journals will be exported
        :param vorlauf_id: id of the vorlauf if an existing export should be generated again
        :param context: context (export_interface is important: eg. datev, addison)
        :param date_from: date in wich moves should be exported
        :param date_to: date in wich moves should be exported
        .. seealso:: 
            :class:`ecoservice_financeinterface.wizard.export_ecofi_buchungsaetze.export_ecofi`
        """
        buf = cStringIO.StringIO()
        ecofi_csv = csv.writer(buf, delimiter=';', quotechar='"', quoting=csv.QUOTE_ALL)
        partnererror = []
        buchungserror = []
        exportmethod = ''
        user = self.pool.get('res.users').browse(cr, uid, [uid], context)[0]
        if user.company_id.finance_interface:
            context['export_interface'] = user.company_id.finance_interface
            try:
                exportmethod = user.company_id.exportmethod
            except:
                exportmethod = 'netto'
        else:
            context['export_interface'] = 'datev'
            exportmethod = 'netto'
        if len(journal_ids) == 0:
            if user.company_id.journal_ids:
                if len(user.company_id.journal_ids) == 0:
                    return (_("There is no journal for the ecofi_export configured!"), False, 'none', buchungserror, partnererror)
                journalname = ''
                for journal in user.company_id.journal_ids:
                    journalname += ustr(journal.name) + ','
                    journal_ids.append(journal.id)
                journalname = journalname[:-1]                   
            else:
                return (_("There is no journal for the ecofi_export configured!"), False, 'none', buchungserror, partnererror)
        else:
            journalname = ''
            for journal in self.pool.get('account.journal').browse(cr, uid, journal_ids, context=context):
                journalname += ustr(journal.name) + ','
            journalname = journalname[:-1]                   
        if vorlauf_id is not False:
            account_move_searchdomain = [('vorlauf_id', '=', vorlauf_id)]
        else:
            account_move_searchdomain = [('journal_id', 'in', journal_ids),
                                         ('state', '=', 'posted'),
                                         ('vorlauf_id', '=', False)
            ]
            if date_from and date_to:
                account_move_searchdomain.append(('date', '>=', date_from))
                account_move_searchdomain.append(('date', '<=', date_to))
        account_move_ids = self.pool.get('account.move').search(cr, uid, account_move_searchdomain)
        if len(account_move_ids) != 0:
            thislog = ""
            if vorlauf_id is False:
                vorlaufname = self.pool.get('ir.sequence').get(cr, uid, 'ecofi.vorlauf')
                zeitraum = ""
                if date_from and date_to:
                    try:
                        date_from = datetime.strptime(date_from, '%Y-%m-%d').strftime('%d.%m.%Y')
                        date_to = datetime.strptime(date_to, '%Y-%m-%d').strftime('%d.%m.%Y')
                    except:
                        pass
                    zeitraum = str(date_from) + " - " + str(date_to)
                vorlauf_id = self.pool.get('ecofi').create(cr, uid, {'name': str(vorlaufname),
                                                               'zeitraum': zeitraum,
                                                               'journale': ustr(journalname)
                                                               })
            else:
                vorlaufname = self.pool.get('ecofi').browse(cr, uid, [vorlauf_id], context=context)[0]['name']
            thislog += _("This export is conducted under the Vorlaufname: %s") % (vorlaufname)
            thislog += "\n"
            thislog += "-----------------------------------------------------------------------------------\n"
            thislog += _("Start export")
            thislog += "\n"
            bookingdictcount = 0
            buchungszeilencount = 0
            errorcount = 0
            warncount = 0
            bookingdict = {}
            self.pre_export(cr, uid, account_move_ids, context)
            for move in self.pool.get('account.move').browse(cr, uid, account_move_ids):
                self.pool.get('account.move').write(cr, uid, [move.id], {'vorlauf_id': vorlauf_id})  
                thismovename = ustr(move.name) + ", " + ustr(move.ref) + ": "
                bookingdictcount += 1
                buchungserror, errorcount, thislog, partnererror, buchungszeilencount, bookingdict = self.generate_csv_move_lines(cr, uid, move, buchungserror, errorcount, thislog, thismovename, exportmethod, # pylint: disable-msg=C0301
                          partnererror, buchungszeilencount, bookingdict, context=context)
            ecofi_csv, thislog = self.generate_csv(cr, uid, ecofi_csv, bookingdict, thislog, context=context)
            if errorcount == 0:
                out = base64.encodestring(buf.getvalue())
            else:
                out = base64.encodestring(buf.getvalue())
            thislog += _("Export finished")
            thislog += "\n"
            thislog += "-----------------------------------------------------------------------------------\n\n"
            thislog += _("Edited posting record : %s") % (bookingdictcount)
            thislog += "\n"
            thislog += _("Edited posting lines: %s") % (buchungszeilencount)
            thislog += "\n"
            thislog += _("Warnings: %s") % (warncount)
            thislog += "\n"
            thislog += _("Error: %s") % (errorcount)
            thislog += "\n"
            self.pool.get('ecofi').write(cr, uid, vorlauf_id, {'csv_file': out,
                                                               'csv_file_fname': '%s.csv' % (vorlaufname),
                                                               'note': thislog,
                                                               'partner_error_ids': [(6, 0, list(set(partnererror)))],
                                                               'move_error_ids': [(6, 0, list(set(buchungserror)))],
                                                               }) 
        else:
            thislog = _("No posting records found")
            out = False
            vorlauf_id = False
        return vorlauf_id
ecofi()
