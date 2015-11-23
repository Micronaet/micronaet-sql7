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

class product_product(osv.osv):
    ''' Add extra fields.function that calculate stock status for product 
        (used in some view for information)
    '''
    _name = 'product.product'
    _inherit = 'product.product'

    # --------
    # Utility:
    # --------
    def get_supplier_id(self, cr, uid, ref, context=None):
        ''' Search supplier from code
        '''
        if not ref:
            return False

        partner_pool = self.pool.get('res.partner')
        partner_ids = partner_pool.search(cr, uid, [('sql_supplier_code', '=', ref)], context=context)
        if partner_ids:
            return partner_ids[0]
        return False    
    
    # ------------------
    # Scheduled actions:
    # ------------------
    def export_store_qty_csv(self, cr, uid, path, csv_file, context=None):
        ''' Export status material
        '''
        _logger.info("Start export product existence via CSV!")
        f = open(os.path.join(os.path.expanduser(path), csv_file), "w")       
        i = 0
        separator = ";"
        
        try:
            product_ids = self.search(cr, uid, [], context=context)
            for product in self.browse(cr, uid, product_ids, context=context):
                i += 1
                if i % 100 == 0:
                    _logger.info("Export product situation, record %s" % (i))
                f.write("%-15s%10.3f%10.3f%10.3f\r\n" % (
                    product.default_code,
                    product.sql_net,
                    product.sql_availability_net,
                    product.sql_availability_gross,
                ))
                
        except:
            _logger.error("[Row: %s] Error exporting: %s" % (i, sys.exc_info()))
            return False
        return True

    def import_quantity_existence_csv(self, cr, uid, path, csv_file, context = None):    
        ''' Import status of product
        '''
        def format_float(value):
            ''' Format float value
            '''     
            value = format_string(value)
            try:
                return float(value.replace(",", "."))
            except:
                return 0.0 # in case of error # TODO log
               
        def format_string(value):
            ''' Format float value
            '''        
            return value.strip()
            
        _logger.info("Start import product existence via CSV!")

        f = open(os.path.join(os.path.expanduser(path), csv_file), "r")       
        i = 0
        separator = ";"
        try:
            for line in f:
                try:
                    i += 1
                    if i % 100 == 0:
                        _logger.info("AQ Quantity line read: %s" % (i))
                      
                    csv_line = line.strip().split(separator)
                    
                    default_code = format_string(csv_line[0])
                    sql_inventary = format_float(csv_line[1])
                    sql_load = format_float(csv_line[2])
                    sql_unload = format_float(csv_line[3])
                    sql_order_customer = format_float(csv_line[4])
                    sql_order_customer_suspended = format_float(csv_line[5])
                    sql_order_customer_auto = format_float(csv_line[6])
                    sql_order_supplier = format_float(csv_line[7])
                    #sql_order_production = csv_line[8]
                    sql_min_level = format_float(csv_line[8])
                    #sql_max_level = csv_line[10]
                    sql_reorder_lot = format_float(csv_line[9])
                    supplier_ref = format_string(csv_line[10])
                    supplier_id = self.get_supplier_id(
                        cr, uid, supplier_ref, context=context)

                    item_id = self.search(cr, uid, [
                        ('default_code', '=', default_code)], context=context)
                    if item_id:                    
                        #accounting_qty = (record['NQT_INV'] or 0.0) + (record['NQT_CAR'] or 0.0) - (record['NQT_SCAR'] or 0.0)
                        self.write(cr, uid, item_id, {
                            'sql_inventary': sql_inventary,
                            'sql_load': sql_load,
                            'sql_unload': sql_unload,                            
                            'sql_order_customer': sql_order_customer,
                            'sql_order_customer_suspended': sql_order_customer_suspended,
                            'sql_order_customer_auto': sql_order_customer_auto,
                            'sql_order_supplier': sql_order_supplier,
                            'sql_order_production': 0.0,
                            'sql_min_level': sql_min_level,
                            'sql_max_level': 0.0,
                            'sql_reorder_lot': sql_reorder_lot, 
                            #'sql_order_cancel': sql_order_cancel,
                            #'sql_order_locked': sql_order_locked,
                            #'sql_order': sql_order,
                            'default_supplier_id': supplier_id,
                        }, context=context)
                except:
                    _logger.error("Error update product state! [%s]" % (
                        sys.exc_info()))
        except:
            _logger.error(sys.exc_info())
            return False
        _logger.info("End import product existence!")        
        return True
        
    _columns = {
        'default_supplier_id':fields.many2one('res.partner', 'Default supplier', required=False),
    }

class etl_move_line(osv.osv):
    ''' Extra field 
    '''    
    _name = 'sql.move.line'    
    _inherit = 'sql.move.line'    
    
    _columns = {
        'default_supplier_id': fields.related('product_id', 'default_supplier_id', type='many2one', relation='res.partner', string='Default partner', store=True),
    }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
