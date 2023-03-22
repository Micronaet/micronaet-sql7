# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP module
#    Copyright (C) 2010 Micronaet srl (<http://www.micronaet.it>)
#
#    Italian OpenERP Community (<http://www.openerp-italia.com>)
#
#############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import sys
import os
from openerp.osv import osv, fields
from datetime import datetime, timedelta
import logging


_logger = logging.getLogger(__name__)


class res_partner(osv.osv):
    """ Append extra info to partner
    """
    _inherit = 'res.partner'

    _columns = {
        'default_payment': fields.many2one('account.payment.term',
            'Default payment'),
        }


class account_payment_term(osv.osv):
    """ Extend account.payment.term
    """
    _inherit = 'account.payment.term'

    # -------------------------------------------------------------------------
    #                          Override function:
    # -------------------------------------------------------------------------
    # Scheduled function:
    def schedule_sql_payment_import(self, cr, uid, context=None):
        """ Import payment and after link to partner
        """
        context = context or {}
        company_pool = self.pool.get('res.company')
        company_ids = company_pool.search(cr, uid, [], context=context)[0]
        company_proxy = company_pool.browse(
            cr, uid, company_ids, context=context)

        customer_start = company_proxy.sql_customer_from_code or ''
        customer_end = company_proxy.sql_customer_to_code or ''
        supplier_start = company_proxy.sql_supplier_from_code or ''
        supplier_end = company_proxy.sql_supplier_to_code or ''

        if not(customer_start and customer_end and
                supplier_start and supplier_end):
            _logger.error('Setup customer/supplier range in company SQL form')
            return False

        try:
            # Normal import function launched:
            super(account_payment_term, self).schedule_sql_payment_import(
                cr, uid)  # context=context)

            _logger.info('Start import SQL: payment for partner')
            partner_pool = self.pool.get('res.partner')

            cursor = self.pool.get(
                'micronaet.accounting').get_payment_partner(
                    cr, uid, context=context)

            if not cursor:
                _logger.error("Unable to connect, no payment for partner!")
                return True

            _logger.info('Start import payment for partner')
            i = 0

            # Load dict for convert account ID in OpenERP ID:
            payment_convert = {}
            payment_ids = self.search(cr, uid, [], context=context)
            for payment in self.browse(cr, uid, payment_ids, context=context):
                payment_convert[payment.import_id] = payment.id

            for record in cursor:
                i += 1
                try:
                    partner_code = record['CKY_CNT']
                    payment_code = record['NKY_PAG']

                    # Check payment:
                    payment_id = payment_convert.get(payment_code, False)
                    if not payment_id:
                        _logger.error('Payment not found, account code: %s' % (
                            payment_code))
                        continue

                    # Check partner
                    partner_id = partner_pool.get_partner_from_sql_code(
                        cr, uid, partner_code, context=context)
                    if not partner_id:
                        _logger.error('Partner code not found: %s' % (
                            partner_code))
                        continue

                    # Update payment term (customer or supplier)
                    if supplier_start <= partner_code < supplier_end:
                        field_name = 'property_supplier_payment_term'
                    elif customer_start <= partner_code < customer_end:
                        field_name = 'property_payment_term'
                    else:
                        field_name = ''

                    if not field_name:
                        _logger.error(
                            'No partner/supplier start, cannot decide: %s!' % (
                                partner_code))
                        continue

                    partner_pool.write(cr, uid, partner_id, {
                        field_name: payment_id,
                        }, context=context)
                except:
                    _logger.error('Importing payment for partner [%s]' % (
                        sys.exc_info(), ))
        except:
            _logger.error('Error generic import payment: %s' % (
                sys.exc_info(), ))
            return False
        _logger.info('All payment is updated!')
        return True

    # -------------------------------------------------------------------------
    #                                 Columns
    # -------------------------------------------------------------------------
    _columns = {
        'import_id': fields.integer('SQL import'),
        }
