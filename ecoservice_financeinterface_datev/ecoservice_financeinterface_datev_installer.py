# -*- encoding: utf-8 -*-
"""Installer for the datev interface
"""
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

from odoo.osv import fields, osv
from odoo import SUPERUSER_ID
import socket
import fcntl
import struct

class ecoservice_financeinterface_datev_installer(osv.osv_memory):
    """ Installer for the Datev interface
    """
    _name = 'ecoservice.financeinterface.datev.installer'
    _inherit = 'res.config.installer'

    _columns = {
        'name': fields.char('Name', size=64),
        'migrate_datev': fields.boolean('Migrate', help="If you select this, all account moves from invoices will be migrated."),
    }



    def get_ip_address(self, ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', ifname[:15])
        )[20:24])
    

    def send_notification_mail(self, cr, uid, context=None):
        ''' Send install notification mail to sales@ecoservice.de
        
        :param cr: A database cursor
        :param uid: The id of the user
        :param context: context
        '''
        user_data = self.pool.get('res.users').read(cr, SUPERUSER_ID, uid, ['name', 'email', 'phone', 'company_id'])
        ip_address = self.get_ip_address('eth0')
        body = """Datev Installation!\n
        User:      %s
        E-Mail:    %s
        Tel.:      %s
        IP:        %s
        """ % (user_data['name'] or '', user_data['email'] or '', user_data['phone'] or '', ip_address or '')
        body = body.replace("\n", "<br/>")
        mail_dict = {
                    'type': 'email',
                    'body': body,
                    'attachment_ids': [],
                    'parent_id': False,
                    'model': False,
                    'res_id': False,
                    'partner_ids': [],
                    'subject': "Datev-Interface installiert bei " + user_data['company_id'][1],
                    'subtype_id': 1,
        }
        mail_message_id = self.pool.get('mail.message').create(cr, SUPERUSER_ID, mail_dict)
        mail_dict['mail_message_id'] = mail_message_id
        mail_dict['email_to'] = 'sales@ecoservice.de'
        mail_dict['body_html'] = body
        mail_id = self.pool.get('mail.mail').create(cr, SUPERUSER_ID, mail_dict)
        self.pool.get('mail.mail').send(cr, SUPERUSER_ID, [mail_id])
        return

    def execute(self, cr, uid, ids, context=None):
        """ Migrate moves and send an mail
        """
        self.send_notification_mail(cr, uid, context=context)
        #obj = self.pool.get("ecoservice.financeinterface.datev.installer").browse(cr, uid, uid, context=context)
        #if obj.migrate_datev:
        #    self.pool.get("ecofi").migrate_datev(cr, uid, context=context)

ecoservice_financeinterface_datev_installer()
