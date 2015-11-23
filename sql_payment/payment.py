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

class account_payment_term(osv.osv):
    ''' Extend account.payment.term
    '''    
    _name = 'account.payment.term'
    _inherit = 'account.payment.term'
    
    # -------------------------------------------------------------------------
    # Utility function
    # -------------------------------------------------------------------------
    def get_payment(self, cr, uid, account_id, context=None):
        ''' Return OpenERP ID from  account ID        
        '''
        payment_ids = self.search(cr, uid, [
            ('import_id', '=', account_id)], context=context)
        if payment_ids:
            return payment_ids[0]
        else:    
            return False
            
    # -------------------------------------------------------------------------
    #                             Scheduled action
    # -------------------------------------------------------------------------
    def schedule_sql_payment_import(self, cr, uid, context=None):
        ''' Import payment
        '''            
        try:
            _logger.info('Start import SQL: payment')
            
            cursor = self.pool.get('micronaet.accounting').get_payment(
                cr, uid, context=context)
            if not cursor:
                _logger.error("Unable to connect, no payment!")
                return True

            _logger.info('Start import payment')                          
            i = 0
            for record in cursor:
                i += 1
                try:
                    import_id = record['NKY_PAG']
                    data = {
                        'import_id': import_id,
                        'name': record['CDS_PAG'],
                        }                    
                    payment_ids = self.search(cr, uid, [
                        ('import_id', '=', import_id)], context=context)

                    # Update / Create
                    if payment_ids:
                        payment_id = payment_ids[0]
                        self.write(cr, uid, payment_id, data, 
                            context=context)
                    else:
                        payment_id = self.create(
                            cr, uid, data, context=context)
                except:
                    _logger.error('Error importing payment [%s]' % (
                        sys.exc_info(), ))
                                            
        except:
            _logger.error('Error generic import payment: %s' % (sys.exc_info(), ))
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
