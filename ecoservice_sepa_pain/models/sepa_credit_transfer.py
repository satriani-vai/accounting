# -*- coding: utf-8 -*-

import re
import time
import random
import base64

from lxml import etree

from openerp import models, api, _
from openerp.tools import float_round
from openerp.exceptions import UserError, ValidationError

from openerp.addons.account_sepa.sepa_credit_transfer import prepare_SEPA_string


class AccountSepaCreditTransfer(models.TransientModel):
    _inherit = 'account.sepa.credit.transfer'

    def _create_pain_001_003_03_document(self, doc_payments):
        """ :param doc_payments: recordset of account.payment to be exported in the XML document returned
            """
        xsi = "http://www.w3.org/2001/XMLSchema-instance"
        Document = etree.Element("Document", nsmap={
            None: "urn:iso:std:iso:20022:tech:xsd:pain.001.003.03",
            'xsi': xsi
        }, attrib={'{' + xsi + '}schemaLocation': "urn:iso:std:iso:20022:tech:xsd:pain.001.003.03 pain.001.003.03.xsd"})
        # 'schemaLocation': "urn:iso:std:iso:20022:tech:xsd:pain.001.003.03 pain.001.003.03.xsd"})
        CstmrCdtTrfInitn = etree.SubElement(Document, "CstmrCdtTrfInitn")

        # Create the GrpHdr XML block
        GrpHdr = etree.SubElement(CstmrCdtTrfInitn, "GrpHdr")
        MsgId = etree.SubElement(GrpHdr, "MsgId")
        val_MsgId = str(int(time.time() * 100))[-10:]
        val_MsgId = str(random.random()) + val_MsgId
        val_MsgId = val_MsgId[-30:]
        MsgId.text = val_MsgId
        CreDtTm = etree.SubElement(GrpHdr, "CreDtTm")
        CreDtTm.text = time.strftime("%Y-%m-%dT%H:%M:%S")
        NbOfTxs = etree.SubElement(GrpHdr, "NbOfTxs")
        val_NbOfTxs = str(len(doc_payments))
        if len(val_NbOfTxs) > 15:
            raise ValidationError(_(u"Too many transactions for a single file."))
        NbOfTxs.text = val_NbOfTxs
        CtrlSum = etree.SubElement(GrpHdr, "CtrlSum")
        CtrlSum.text = self._get_CtrlSum(doc_payments)
        GrpHdr.append(self._get_InitgPty())

        # Create the PmtInf XML block
        PmtInf = etree.SubElement(CstmrCdtTrfInitn, "PmtInf")
        PmtInfId = etree.SubElement(PmtInf, "PmtInfId")
        PmtInfId.text = (val_MsgId + str(self.journal_id.id))[-30:]
        PmtMtd = etree.SubElement(PmtInf, "PmtMtd")
        PmtMtd.text = 'TRF'
        BtchBookg = etree.SubElement(PmtInf, "BtchBookg")
        BtchBookg.text = 'false'
        NbOfTxs = etree.SubElement(PmtInf, "NbOfTxs")
        NbOfTxs.text = str(len(doc_payments))
        CtrlSum = etree.SubElement(PmtInf, "CtrlSum")
        CtrlSum.text = self._get_CtrlSum(doc_payments)
        PmtInf.append(self._get_PmtTpInf())
        ReqdExctnDt = etree.SubElement(PmtInf, "ReqdExctnDt")
        ReqdExctnDt.text = time.strftime("%Y-%m-%d")
        PmtInf.append(self._get_Dbtr())
        PmtInf.append(self._get_DbtrAcct())
        DbtrAgt = etree.SubElement(PmtInf, "DbtrAgt")
        FinInstnId = etree.SubElement(DbtrAgt, "FinInstnId")
        if not self.bank_account_id.bank_bic:
            raise UserError(_(u"There is no Bank Identifier Code recorded for bank account '%s' of journal '%s'") % (self.bank_account_id.acc_number, self.journal_id.name))
        BIC = etree.SubElement(FinInstnId, "BIC")
        BIC.text = self.bank_account_id.bank_bic

        # One CdtTrfTxInf per transaction
        for payment in doc_payments:
            PmtInf.append(self._get_CdtTrfTxInf(PmtInfId, payment))

        return etree.tostring(Document, pretty_print=True, xml_declaration=True, encoding='utf-8')

    @api.v7
    def create_sepa_credit_transfer(self, cr, uid, payment_ids, context=None):
        payments = self.pool['account.payment'].browse(cr, uid, payment_ids, context=context)
        return self.pool['account.sepa.credit.transfer'].browse(cr, uid, [], context=context).create_sepa_credit_transfer(payments)

    @api.v8
    @api.model
    def create_sepa_credit_transfer(self, payments):
        """ Create a new instance of this model then open a wizard allowing to download the file
        """
        # Since this method is called via a client_action_multi, we need to make sure the received records are what we expect
        payments = payments.filtered(self._payments_filter).sorted(key=lambda r: r.id)

        if len(payments) == 0:
            raise UserError(_(u"Payments to export as SEPA Credit Transfer must have 'SEPA Credit Transfer' selected as payment method and be posted"))
        if any(payment.journal_id != payments[0].journal_id for payment in payments):
            raise UserError(_(u"In order to export a SEPA Credit Transfer file, please only select payments belonging to the same bank journal."))

        journal = payments[0].journal_id
        bank_account = journal.bank_account_id
        if not bank_account.acc_type == 'iban':
            raise UserError(_(u"The account %s, of journal '%s', is not of type IBAN.\nA valid IBAN account is required to use SEPA features.") % (bank_account.acc_number, journal.name))
        for payment in payments:
            if not payment.partner_bank_account_id:
                raise UserError(_(u"There is no bank account selected for payment '%s'") % payment.name)

        res = self.create({
            'journal_id': journal.id,
            'bank_account_id': bank_account.id,
            'filename': "SCT" + bank_account.sanitized_acc_number + time.strftime("%Y%m%d") + ".xml",
            'is_generic': self._require_generic_message(journal, payments),
        })

        xml_doc = res._create_pain_001_003_03_document(payments)
        for no, line in enumerate(xml_doc.split('\n')):
            print '{:3d}: {}'.format(no, line)
        res.file = base64.encodestring(xml_doc)

        # self._check_created_xml(res.file)
        self._check_created_xml(xml_doc)

        payments.write({'state': 'sent', 'payment_reference': res.filename})

        # Alternatively, return the id of the transient and use a controller to download the file
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.sepa.credit.transfer',
            'target': 'new',
            'res_id': res.id,
        }

    @api.model
    def _require_generic_message(self, journal, payments):
        """ Find out if generating a credit transfer initiation message for payments requires to use the generic rules, as opposed to the standard ones.
            The generic rules are used for payments which are not considered to be standard european credit transfers.
        """
        # A message is generic if :
        debtor_currency = journal.currency_id and journal.currency_id.name or journal.company_id.currency_id.name
        if debtor_currency != 'EUR':
            return True  # The debtor account is not labelled in EUR
        for payment in payments:
            bank_account = payment.partner_bank_account_id
            if payment.currency_id.name != 'EUR':
                return True  # Any transaction in instructed in another currency than EUR
            if not bank_account.bank_bic:
                return True  # Any creditor agent is not identified by a BIC
            if not bank_account.acc_type == 'iban':
                return True  # Any creditor account is not identified by an IBAN
        return False

    def _get_CdtTrfTxInf(self, PmtInfId, payment):
        CdtTrfTxInf = etree.Element("CdtTrfTxInf")
        PmtId = etree.SubElement(CdtTrfTxInf, "PmtId")
        InstrId = etree.SubElement(PmtId, "InstrId")
        InstrId.text = prepare_SEPA_string(payment.name)
        EndToEndId = etree.SubElement(PmtId, "EndToEndId")
        EndToEndId.text = (PmtInfId.text + str(payment.id))[-30:]
        Amt = etree.SubElement(CdtTrfTxInf, "Amt")
        val_Ccy = payment.currency_id and payment.currency_id.name or payment.journal_id.company_id.currency_id.name
        val_InstdAmt = str(float_round(payment.amount, 2))
        max_digits = val_Ccy == 'EUR' and 11 or 15
        if len(re.sub('\.', '', val_InstdAmt)) > max_digits:
            raise ValidationError(_(u"The amount of the payment '%s' is too high. The maximum permitted is %s.") % (payment.name, str(9) * (max_digits - 3) + ".99"))
        InstdAmt = etree.SubElement(Amt, "InstdAmt", Ccy=val_Ccy)
        InstdAmt.text = val_InstdAmt
        CdtTrfTxInf.append(self._get_ChrgBr())
        CdtTrfTxInf.append(self._get_CdtrAgt(payment.partner_bank_account_id))
        Cdtr = etree.SubElement(CdtTrfTxInf, "Cdtr")
        Nm = etree.SubElement(Cdtr, "Nm")
        Nm.text = prepare_SEPA_string(payment.partner_id.name[:70])
        CdtTrfTxInf.append(self._get_CdtrAcct(payment.partner_bank_account_id))
        Purp = etree.SubElement(CdtTrfTxInf, 'Purp')
        Cd = etree.SubElement(Purp, 'Cd')
        Cd.text = 'NOWS'
        val_RmtInf = self._get_RmtInf(payment)
        if val_RmtInf != False:
            CdtTrfTxInf.append(val_RmtInf)
        return CdtTrfTxInf

    def _get_CdtrAgt(self, bank_account):
        CdtrAgt = etree.Element("CdtrAgt")
        FinInstnId = etree.SubElement(CdtrAgt, "FinInstnId")
        val_BIC = bank_account.bank_bic
        if val_BIC:
            BIC = etree.SubElement(FinInstnId, "BIC")
            BIC.text = val_BIC
        elif not self.is_generic:
            raise UserError(_(u"There is no Bank Identifier Code recorded for bank account '%s'") % bank_account.acc_number)
        return CdtrAgt

    @staticmethod
    def _check_created_xml(data):
        from io import StringIO
        import os

        file_path = u"{absolute}/../schemas/{document}.{sepa}.{variant}.{version}.xsd".format(
            absolute=os.path.dirname(os.path.realpath(__file__)),
            document='pain',
            sepa='001',
            variant='003',
            version='03'
        )
        data = '\n'.join(data.split('\n')[1:])
        xsd = etree.XMLSchema(etree.parse(file_path))
        if not xsd.validate(etree.parse(StringIO(unicode(data)))):
            raise ValidationError(u'\n'.join([unicode(m) for m in xsd.error_log.filter_from_errors()]))
        return True

    def _payments_filter(self, r):
        return r.payment_method_id.code == 'sepa_ct' and r.state in ('posted', 'sent')
