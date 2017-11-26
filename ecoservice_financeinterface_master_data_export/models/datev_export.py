# -*- encoding: utf-8 -*- # pylint: disable-msg=C0302
##############################################################################
#    ecoservice_financeinterface_datev_export
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
from odoo import osv, fields, models
import csv
import base64
import cStringIO
from odoo.tools import ustr
from odoo.tools.translate import _
from odoo.modules import module as addons
from decimal import Decimal


class ecofi_datev_formate(models.Model):
    """ Klasse um den Exportformate in Datev festzulegen"""
    _name = 'ecofi.datev.formate'
    _description = 'Configuration for Datev Reference Data Exports'

    def _get_export_type(self):
        """Method that can be used by other Modules to add their interface to the selection of possible export formats"""
        return [('none', 'None')]

    name = fields.Char('Name', size=128, required=True)
    mako_help = fields.Text('Mako Help', readonly=True)
    csv_spalten = fields.One2many('ecofi.datev.spalten', 'import_id', 'Datev-Spalten', default=[])
    datev_domain = fields.Char('Domain', size=128, required=True)
    datev_type = fields.Selection(_get_export_type, 'Exporttype')

    def _get_account_type(self, account_type):
        """Method that can be used by other Modules to add their interface to the selection of possible export formats"""
        return account_type
    
    def convert_value(self, spaltentyp, value, context=None):
        """ Tries to convert given Value into the Datev Format"""
        if context is None:
            context = {}
        checkdict = {
                     'Konto': ("int('%s')" % (value), _('in an Integer')),
                     'Zahl': ("int('%s')" % (value), _('in an Integer')),
                     'Text': ("str('%s')" % (value), _('in a Text')),
                     'Datum': ("time.strftime('%d.%m.%Y', time.strptime('" + ustr(value) + "','%d-%m-%Y'))", _('in a Date')),
                     'Betrag': ("str(Decimal('%s')).replace('.',',')" % (value), _('in an Decimal')),
                     }
        res = {'log': '', 'value': False}
        if spaltentyp in checkdict:
            try:
                if value == '' or value is False:
                    res['value'] = ''
                else:
                    value = eval(checkdict[spaltentyp][0])
                    res['value'] = ustr(value).encode('encoding' in context and context['encoding'] or 'iso-8859-1')
            except:
                res['log'] = _("Value %s could not be convertet %s!" % (value, checkdict[spaltentyp][1]))
        return res

    def generate_export_csv(self, cr, uid, export, ecofi_csv, context={}):
        """ Hook Method to fill the CSV-File with DATA"""
        return {'log': ''}

    def generate_export(self, cr, uid, ids, context={}):
        """ Method that generates the CSV File called by the Wizard"""
        buf = cStringIO.StringIO()
        ecofi_csv = csv.writer(buf, delimiter=',', quotechar='"')
        for export in self.browse(cr, uid, ids, context=context):
            export_info = self.generate_export_csv(cr, uid, export, ecofi_csv, context=context)
        res = {}
        res['file'] = base64.encodestring(buf.getvalue())
        res['log'] = export_info['log']
        return res

    def generate_csv_header_definition(self):
        """CSV-Template Header Definition Dictionary Definition"""
        importattrs = {}
        importattrs['mako'] = {'header': 'Mako',
                                  'fieldnumber': False
        }
        importattrs['datevid'] = {'header': 'Nr.',
                                  'fieldnumber': False
        }
        importattrs['feldname'] = {'header': 'Feldname',
                                   'fieldnumber': False
        }
        importattrs['typ'] = {'header': 'Typ',
                              'fieldnumber': False
        }
        importattrs['nks'] = {'header': 'NKS',
                              'fieldnumber': False
        }
        importattrs['laenge'] = {'header': 'Länge',
                                  'fieldnumber': False
        }
        importattrs['maxlaenge'] = {'header': 'Max. Länge',
                                  'fieldnumber': False
        }
        importattrs['beschreibung'] = {'header': 'Beschreibung',
                                  'fieldnumber': False
        }
        importattrs['mussfeld'] = {'header': 'Muss-Feld',
                                  'fieldnumber': False
        }
        return importattrs

    def getfields_defaults(self, cr, thisimport, context=None):
        """ Hook Method to fill the defaults like template.csv etc"""
        return {}

    def getfields_fromcsv(self, cr, uid, ids, context={}):
        """ Import the CSV Template for the Export Configurations"""
        for thisimport in self.browse(cr, uid, ids, context):
            if thisimport.datev_type:
                thisdefaults = self.getfields_defaults(cr, thisimport, context=context)
                self.write(cr, uid, ids, {'mako_help': thisdefaults['mako_help']}, context=context)
                if thisdefaults['csv_template']:
                    importliste = csv.reader(open(addons.get_module_resource(thisdefaults['module'], thisdefaults['csv_template']), 'r'),
                                              delimiter=',')
                    counter = 0
                    importattrs = self.generate_csv_header_definition()
                    for line in importliste:
                        if counter == 0:
                            fieldcounter = 0
                            for value in line:
                                for attr in importattrs.keys():
                                    if importattrs[attr]['header'] == value:
                                        importattrs[attr]['fieldnumber'] = fieldcounter
                                fieldcounter += 1
                            for attr in importattrs.keys():
                                if importattrs[attr]['fieldnumber'] is False:
                                    raise osv.except_osv(_('Error !'),
                                                         _('Importformat not correct, Headervalue %s not found in the csv!' % (importattrs[attr]['header'])))
                        else:
                            thisspalte = self.pool.get('ecofi.datev.spalten').search(cr, uid, [('import_id', '=', thisimport.id),
                                                                                               ('datevid', '=', int(line[importattrs['datevid']['fieldnumber']]))
                                                                                               ], context=context)
                            if line[importattrs['mussfeld']['fieldnumber']] == 'Ja':
                                line[importattrs['mussfeld']['fieldnumber']] = True
                            else:
                                line[importattrs['mussfeld']['fieldnumber']] = False
                            spaltedict = {
                                          'import_id': thisimport.id,
                                          }
                            for attr in importattrs.keys():
                                spaltedict[attr] = line[importattrs[attr]['fieldnumber']]
                            if len(thisspalte) == 1:
                                self.pool.get('ecofi.datev.spalten').write(cr, uid, thisspalte, spaltedict, context)
                            else:
                                self.pool.get('ecofi.datev.spalten').create(cr, uid, spaltedict, context)
                        counter += 1
        return True
ecofi_datev_formate()


class ecofi_datev_spalten(models.Model):
    _name = 'ecofi.datev.spalten'
    _description = 'Configuration for Datev Reference Data Exports Columns'
    _order = 'datevid asc'
    
    datevid = fields.Integer('DatevID', size=64, readonly=True)
    feldname = fields.Char('Fieldname', size=64, readonly=True)
    typ = fields.Char('Fieldtype', size=64, readonly=True)
    laenge = fields.Integer('Length ', readonly=True)
    nks = fields.Integer('Decimal places', readonly=True)
    maxlaenge = fields.Integer('Maximal length', readonly=True)
    mussfeld = fields.Boolean('Mandatory field', readonly=True)
    beschreibung = fields.Text('Description', readonly=True)
    import_id = fields.Many2one('ecofi.datev.formate', 'Import', required=True, ondelete='cascade', select=True)
    mako = fields.Text('Mako')
    
ecofi_datev_spalten()
