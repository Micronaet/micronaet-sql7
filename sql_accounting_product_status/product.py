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
from datetime import datetime, timedelta
from openerp.osv import osv, fields
import logging


_logger = logging.getLogger(__name__)

class res_company(osv.osv):
    ''' Extend res.company with other parameters
    '''
    _name = 'res.company'
    _inherit = 'res.company'
    
    _columns = {
        'sql_exclude_movement': fields.boolean('Exclude movement', help = "There's some movement that is excluded (insert in next field), if so inventory quantity is calculated with this total"),
        'sql_exclude_list': fields.char('Exclue list', help = 'Exclude list, use: ["SL", "CL"] or ("SL", "CL")'),
    }
    
    _defaults = {
        'sql_exclude_movement': lambda *a: False,
    }

class product_product(osv.osv):
    ''' Add extra fields.function that calculate stock status for product 
        (used in some view for information)
    '''
    _name = 'product.product'
    _inherit = 'product.product'
    
    # ------------------
    # Scheduled actions:
    # ------------------
    def import_quantity_existence(self, cr, uid, verbose_quantity=100, context = None):
        ''' Import status of product
        '''
        _logger.info("Start import product existence!")

        # TODO current year always 9 (in company)
        stock = 1

        year = str(datetime.now().year)[3]

        cursor = self.pool.get('micronaet.accounting').get_product_quantity(cr, uid, stock, year, context=context) 
        if not cursor:
            _logger.error("Unable to connect no importation of product existence!")
        
        # Verbose variables:
        i = 0
        try:
            for record in cursor:
                try:
                    i += 1
                    default_code = record['CKY_ART'].strip()

                    item_id = self.search(cr, uid, [('default_code', '=', default_code)], context=context)
                    if item_id:                    
                        accounting_qty = (record['NQT_INV'] or 0.0) + (record['NQT_CAR'] or 0.0) - (record['NQT_SCAR'] or 0.0)                     

                        self.write(cr, uid, item_id, {
                            'sql_inventary': record.get('NQT_INV', 0.0),
                            'sql_load': record.get('NQT_CAR', 0.0),
                            'sql_unload': record.get('NQT_SCAR', 0.0),
                            
                            'sql_order_customer': record.get('NQT_ORD_CLI', 0.0),
                            'sql_order_customer_suspended': record.get('NQT_SOSP_CLI', 0.0),
                            'sql_order_customer_auto': record.get('NQT_CLI_AUT', 0.0),
                            'sql_order_supplier': record.get('NQT_ORD_FOR', 0.0),
                            'sql_order_production': record.get('NQT_INPR', 0.0),
                            'sql_min_level': record.get('NQT_SCORTA_MIN', 0.0),
                            'sql_max_level': record.get('NQT_SCORTA_MAX', 0.0),

                            #'sql_order_cancel': record.get('NQT_INV', 0.0), 
                            #'sql_order_locked': record.get('NQT_INV', 0.0), 
                            #'sql_order': record.get('NQT_INV', 0.0), 
                        }, context=context)

                    if verbose_quantity and (i % verbose_quantity == 0): 
                        _logger.info("%s Record product existing updated!"%(i))
                except:
                    _logger.error("Error update product state! [%s]"%(sys.exc_info()))
        except:
            _logger.error(sys.exc_info())
            return False
        _logger.info("End import product existence!")       
        
        return True
    
    # ----------------
    # Fields function:
    # ----------------
    def _get_sql_store_qty(self, cr, uid, ids, fileds, args, context = None):
        ''' Get total amount (multi function)
        '''
        res = {}
        
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = {}
    
            net = product.sql_inventary + product.sql_load - product.sql_unload 
            res[product.id]['sql_net'] = net
    
            availability = net - (
                product.sql_order_customer + 
                product.sql_order_customer_suspended +
                product.sql_order_customer_auto)
            res[product.id]['sql_availability_net'] = availability  
            
            res[product.id]['sql_availability_gross'] = availability + (
                product.sql_order_supplier +
                product.sql_order_production)
        return res 
        
    _columns = {
        'sql_inventary': fields.float('Inventary', digits=(16, 5)),

        'sql_min_level': fields.float('Min. level', digits=(16, 5)),
        'sql_max_level': fields.float('Max. level', digits=(16, 5)),
        # TODO sottoscorta (bool)?

        'sql_load': fields.float('Load', digits=(16, 5)),
        'sql_unload': fields.float('Unload', digits=(16, 5)),

        'sql_order_customer': fields.float('Customer order', digits=(16, 5)),
        'sql_order_customer_suspended': fields.float('Customer order susp.', digits=(16, 5)),
        'sql_order_customer_auto': fields.float('Customer auto', digits=(16, 5)),
        'sql_order_supplier': fields.float('Supplier order', digits=(16, 5)),
        'sql_order_production': fields.float('Production order', digits=(16, 5)),
        'sql_reorder_lot': fields.float('Reorder lot', digits=(16, 5)),
        
        'sql_net': fields.function(
            _get_sql_store_qty, method = True, type = 'float', string = 'Net', store = False, multi='availability'),
        'sql_availability_net': fields.function(
            _get_sql_store_qty, method = True, type = 'float', string = 'Availability net', store = False, multi='availability'),
        'sql_availability_gross': fields.function(
            _get_sql_store_qty, method = True, type = 'float', string = 'Availability gross', store = False, multi='availability'),
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
