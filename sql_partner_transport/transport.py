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
import os
import sys
import logging
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class res_partner(osv.osv):
    ''' Append extra info to partner
    '''
    _inherit = 'res.partner'
    
    # -------------------------------------------------------------------------
    #                          Override function:
    # -------------------------------------------------------------------------
    # Scheduled function:
    def schedule_sql_partner_import(self, cr, uid, verbose_log_count=100, 
        capital=True, write_date_from=False, write_date_to=False, 
        create_date_from=False, create_date_to=False, sync_vat=False,
        address_link=False, only_block=False, dest_merged=False, 
            set_lang=False, context=None):
        ''' Import partner from external DB
            verbose_log_count: number of record for verbose log (0 = nothing)
            capital: if table has capital letters (usually with mysql in win)
            write_date_from: for smart update (search from date update record)
            write_date_to: for smart update (search to date update record)
            create_date_from: for smart update (search from date create record)
            create_date_to: for smart update (search to date create record)
            sync_vat: Supplier update partner customer with same VAT
            address_link: Link to parent partner as an address the destination
            only_block: update only passed block name:
                (supplier, customer destination... TODO agent, employee)
            v. 8:
            dest_merged 
            set_lang
            context: context of procedure
        '''
        # ---------------------------------------------------------------------
        #                           Utility: 
        # ---------------------------------------------------------------------
        def get_transport_product(self, cr, uid, context=None):
            ''' Create of get default transport product
            '''    
            product_pool = self.pool.get('product.product')
            name = _('Cost of transport')
            product_ids = product_pool.search(cr, uid, [
                ('name', '=', name)], context=context)
            if product_ids:
                return product_ids[0]        

            return product_pool.create(cr, uid, {
                'name': name, 
                'type': 'service',
                }, context=context)
        # ---------------------------------------------------------------------

        try:
            # Normal import function launched:
            super(res_partner, self).schedule_sql_partner_import(cr, uid, 
                verbose_log_count=verbose_log_count, 
                capital=capital, write_date_from=write_date_from, 
                write_date_to=write_date_from, 
                create_date_from=create_date_from, 
                create_date_to=create_date_to, sync_vat=sync_vat,
                address_link=address_link, only_block=only_block, 
                context=context)
            
            _logger.info('Start import SQL: Import transport ref.')
            carrier_pool = self.pool.get('delivery.carrier')

            cursor = self.pool.get(
                'micronaet.accounting').get_partner_transport(
                    cr, uid, context=context)
                    
            if not cursor:
                _logger.error("Unable to connect, no transport for partner!")
                return True

            # Get product for default transport cost:
            transport_id = get_transport_product(
                self, cr, uid, context=context)
            
            _logger.info('Start import transport for partner')
            i = 0            
            for record in cursor:            
                i += 1
                try:
                    partner_code = record['CKY_CNT'] 
                    vector_code = record['CKY_CNT_VETT']
                    # TODO Extra parameters!
                    
                    # --------------
                    # Check partner:
                    # --------------
                    partner_id = self.get_partner_from_sql_code(
                        cr, uid, partner_code, context=context)
                    if not partner_id:
                        _logger.error('Partner code not found: %s' % (
                            partner_code))
                        continue

                    # -------------
                    # Check vector:
                    # -------------
                    vector_id = self.get_partner_from_sql_code(
                        cr, uid, vector_code, context=context)
                    if not vector_id:
                        _logger.error('Vector code not found: %s' % (
                            vector_code))
                        continue
                    name = self.browse(
                        cr, uid, vector_id, context=context).name    

                    # Mark as vector:
                    self.write(cr, uid, vector_id, {
                        'is_vector': True}, context=context)
                        
                    # Create carrier block:
                    carrier_ids = carrier_pool.search(cr, uid, [
                        ('partner_id', '=', vector_id),
                        ], context=context)
                    if carrier_ids:
                        carrier_id = carrier_ids[0]
                    else:
                        carrier_id = carrier_pool.create(cr, uid, {
                            'name': name,
                            'partner_id': vector_id,
                            'product_id': transport_id,
                            }, context=context)    

                    # Update payment term        
                    self.write(cr, uid, partner_id, {
                        'default_transport_id': vector_id,
                        'default_carrier_id': carrier_id,
                        }, context=context)
                except:
                    _logger.error('Importing transport for partner [%s]' % (
                        sys.exc_info(), ))
        except:
            _logger.error('Error generic import vector: %s' % (
                sys.exc_info(), ))
            return False
        _logger.info('All vector is updated!')
        return True

    _columns = {
        'is_vector': fields.boolean('Is Vector'),
        # TODO remove:?
        'default_transport_id': fields.many2one('res.partner', 
            'Default vector'),
        'default_carrier_id': fields.many2one('delivery.carrier', 
            'Default carrier'),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
