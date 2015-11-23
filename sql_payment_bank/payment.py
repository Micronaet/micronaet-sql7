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

from tools.translate import _


_logger = logging.getLogger(__name__)

class res_partner(osv.osv):
    ''' Append extra info to partner
    '''
    _inherit = 'res.partner'
    
    _columns = {
        'default_payment': fields.many2one('account.payment.term', 
            'Default payment'),

        }
        
class account_payment_term(osv.osv):
    ''' Extend account.payment.term
    '''    
    _inherit = 'account.payment.term'

    # -------------------------------------------------------------------------
    #                          Override function:
    # -------------------------------------------------------------------------
    # Scheduled function:
    def schedule_sql_payment_import(self, cr, uid, context=None):
        ''' Import payment and after link to partner
        '''            
        try:
            # Normal import function launched:
            super(account_payment_term, self).schedule_sql_payment_import(
                cr, uid, context=context)

            _logger.info('Start import SQL: payment for bank')
            
            # Used pool:
            partner_pool = self.pool.get('res.partner')
            bank_pool = self.pool.get('res.bank')
            partner_bank_pool = self.pool.get('res.partner.bank')
            
            cursor = self.pool.get(
                'micronaet.accounting').get_payment_bank(
                    cr, uid, context=context)
                    
            if not cursor:
                _logger.error("Unable to connect, no payment for bank!")
                return True

            # Load dict for convert bank ID in OpenERP ID:
            bank_convert = {} # Correct
            bank_names = {} # With problem!
            bank_ids = bank_pool.search(cr, uid, [], context=context)
            for bank in bank_pool.browse(cr, uid, bank_ids, context=context):
                bank_convert[(bank.abi, bank.cab)] = bank.id
                bank_names[bank.name] = bank.id
                
            i = 0            
            _logger.info('Start import payment for bank')
            for record in cursor:
                i += 1
                try:
                    partner_code = record['CKY_CNT']
                    
                    bank_name = record['CDS_BANCA'].strip()
                    abi = record['NGL_ABI']
                    cab = record['NGL_CAB']
                    prefix = record['CKY_CNT_BAN_PREF']
                    cc = record['CSG_CC'] or _('Not found!')
                    cin = record['CSG_BBAN_CIN']
                    nation_code = record['CSG_IBAN_PAESE']
                    cin_letter = record['NGB_IBAN_CIN'] 
                    bban = record['CSG_IBAN_BBAN'] 
                    bic = record['CSG_BIC']
                  
                    # ---------------------------------------------------------
                    #                    res.bank:
                    # ---------------------------------------------------------
                    if abi and cab:
                        if (abi, cab) in bank_convert:
                            bank_id = bank_convert[(abi, cab)]
                        else:
                            bank_id = False    
                    elif bank_name:
                        bank_id = bank_names.get(bank_name, False)
                    else:
                        _logger.warning(
                            'No ABI, CAB or bank name, partner: %s' % (
                                partner_code))
                        continue    
                                
                    # TODO problem if abi and cab added after (duplicated rec.)            
                    if not bank_id:            
                        bank_id = bank_pool.create(cr, uid, {
                            'abi': abi,
                            'cab': cab,
                            'name': bank_name,
                            'nation_code': nation_code,
                            'cin_code': cin,
                            'cin_letter': cin_letter,                            
                            # TODO enought data!!!!!
                            }, context=context)
                            
                    # ---------------------------------------------------------
                    #                    res.partner.bank:
                    # ---------------------------------------------------------                    
                    # Chech partner    
                    partner_id = partner_pool.get_partner_from_sql_code(
                        cr, uid, partner_code, context=context)
                    if not partner_id:
                        _logger.error('Partner code not found: %s' % (
                            partner_code))
                        continue
                            
                    # Update banck account:
                    account_ids = partner_bank_pool.search(cr, uid, [
                        ('partner_id', '=', partner_id),
                        ('acc_number', '=', cc),
                        ('bank', '=', bank_id),
                        ], context=context)
                    
                    if account_ids: # Update information:
                        partner_bank_pool.write(cr, uid, account_ids[0], {
                            }, context=context)
                    else: # create:        
                        partner_bank_pool.create(cr, uid, {
                            'partner_id': partner_id,
                            'acc_number': cc,
                            'bank': bank_id,
                            'bank_name': bank_name,
                            'bank_abi': abi,
                            'bank_cab': cab,
                            'nation_code': nation_code,
                            'cin_code': cin,
                            'cin_letter': cin_letter,
                            'state': 'bank', #'iban',
                            # TODO enought?
                            }, context=context)
                except:
                    _logger.error('Importing payment for partner [%s]' % (
                        sys.exc_info(), ))
        except:
            _logger.error('Error generic import payment: %s' % (
                sys.exc_info()))
            return False
        _logger.info('All payment is updated!')
        return True

    # -------------------------------------------------------------------------
    #                                 Columns
    # -------------------------------------------------------------------------
    _columns = {
        'import_id': fields.integer('SQL import'),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
