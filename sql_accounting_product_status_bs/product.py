# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import sys
import openerp.netsvc
import logging
from openerp.osv import osv, fields
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class stock_move_line(osv.osv):
    ''' Add extra field for manage BS line
    '''
    _name = 'sql.move.line'
    _inherit = 'sql.move.line'
    
    # ------------------
    # Scheduled actions:
    # ------------------
    def send_bs_info_importation(self, cr, uid, path, filename, context=None):
        ''' Send list of BS imported (as document verifing all single lines)
            Send list from begin of the year
        '''
        f = open(os.path.expanduser(os.path.join(path, filename)), "w")
        
        accounting_proxy = self.pool.get('micronaet.accounting')
        move_proxy = self.pool.get('sql.move.line')

        # Read M*SQL data (only BS):
        cursor = accounting_proxy.get_mm_line(cr, uid, "BS", context=context) 
        if not cursor:
            _logger.error("Unable to connect no importation of movement line!")
            return False

        bs_list = {} # list of BS (header) and lines to export
        for record in cursor:
            header = accounting_proxy.KEY_MM_HEADER_FORMAT % (record)
            if header not in bs_list:
                bs_list[header] = []
            bs_list[header].append(record["NPR_RIGA_ART"])

        # Read PG data:
        line_ids = move_proxy.search(cr, uid, [
            ('header', 'in', bs_list.keys())], context=context)
        for line in move_proxy.browse(cr, uid, line_ids, context=context):
            try:
                bs_list[line.header].remove(long(
                    line.name.split(".")[-1].split("]")[0]))
            except:
                pass # for error do nothing (ex. line in pg not in sql)        

        # Write all key/header that are still present
        for header in bs_list.keys():
            if header in bs_list and not bs_list[header]:
                try:
                    line = header.split(":")[-1]         
                    f.write("20%s-%10s\r\n" % (
                        line.split("-")[0],
                        line.split("-")[1]))
                except:
                    _logger.error("Error exporting BS [%s]" % (header))    
        return True

class product_product(osv.osv):
    ''' Add extra fields.function that calculate stock status for product 
        (used in some view for information)
    '''
    _name = 'product.product'
    _inherit = 'product.product'

    def button_to_update(self, cr, uid, ids, context=None):
        ''' Set inventory_updated
        '''
        return self.write(cr, uid, ids, {
            'inventory_updated': False}, context=context)
    
    # -------------------------------------------------------------------------
    #                               Scheduled actions
    # -------------------------------------------------------------------------
    def update_bs_field(self, cr, uid, context=None):
        ''' Run on all product updating BS value from date inventory according
            to all movement
            (calculate BS value depend on document and inventory syncronized)
        '''
        product_ids = self.search(cr, uid, [], context=context)
        i = 0
        for product in self.browse(cr, uid, product_ids, context=context):
            i += 1
            if i % 100 == 0: # Log operation:
                _logger.info("BS updated quantity, record %s" % i)
                
            # Inventory date present, sum(BS) from that date
            if product.inventory_date and product.inventory_updated: 
                query = """
                    select -sum(quantity) 
                    from sql_move_line 
                    where date > '%s' and product_id = %s and type='BS';""" % (
                        product.inventory_date,
                        product.id)
            else:
                query = """
                    select -sum(quantity) 
                    from sql_move_line 
                    where product_id = %s and type='BS';""" % product.id
            cr.execute(query)
            sql_bs = cr.fetchone()[0] or 0.0
            self.write(cr, uid, product.id, {'sql_bs': sql_bs, }, context=context)
        return True

    def update_inventory_quantity(self, cr, uid, tuple_filename, context=None):
        ''' Write file update for manage new quantity in account program
        '''
        _logger.info(_("Start export file inventory!"))
        product_ids = self.search(cr, uid, [
            ('inventory_date', '!=', False),
            ('inventory_updated', '=', False),
        ], context=context)
        file_path = os.path.expanduser(os.path.join(*tuple_filename))
        f = open(file_path, 'w')
        i = 0
        for product in self.browse(cr, uid, product_ids, context=context):
            i += 1
            if i % 100 == 0:
                _logger.info("Updated inventory quantity, record %s" % (i))
            
            if product.inventory_date:
                try:    
                    f.write("%-20s%10.2f%10s\r\n" % (
                        product.default_code,
                        product.inventory_quantity,
                        product.inventory_date,
                    ))
                except:
                    _logger.error(_("Line %s. Error exporting inventory: %s") % (
                        i, sys.exc_info(), ))
        f.close()
        return True

    def update_inventory_quantity_status(self, cr, uid, tuple_filename, context=None):
        ''' TODO write procedure for read file of confirmation
        '''
        ''' Write file update for manage new quantity in account program
        '''
        try:
            _logger.info(_("Start syncro update product inventory!"))

            file_path = os.path.expanduser(os.path.join(*tuple_filename))
            file_path_out = "%s_err" %  file_path
            f_in = open(file_path, 'r')
            f_out = open(file_path_out, 'w')

            i = 0
        except:
            _logger.error(_("Error starting syncro inventory: [%s]") % (
                sys.exc_info()) )
        error = False
        for line in f_in:
            try:
                i += 1
                if i % 100 == 0:
                    _logger.info("Updated inventory quantity, record %s" % i)
                
                default_code = line[:20].strip()
                inventory_date = line[20:30]
                
                product_ids = self.search(cr, uid, [
                    ('inventory_date', '=', inventory_date),
                    ('default_code', '=', default_code),
                    ('inventory_updated', '=', False),
                ], context=context)
                
                if product_ids:
                    self.write(cr, uid, product_ids, {
                        'inventory_updated': True,
                    }, context=context)                    
                    _logger.info(_("Update! [%s]") % default_code)
                else:
                    _logger.warning(_("Not Updated! [%s]") % (line.strip()) )
                    
            except:
                error = True
                _logger.error(_("Error exporting line: %s [%s]") % (
                    line, sys.exc_info()) )
                try:
                    f_out.write(line)
                except:
                    _logger.error(_("Error writing error file [%s]") % (
                        sys.exc_info()) )

        f_in.close()
        f_out.close()        
        if not error:
            os.remove(file_path)
            os.remove(file_path_out)
            
        _logger.info(_("End syncro update product inventory!"))
        return True

    # ----------------
    # Fields function:
    # ----------------
    # Override function (calculate gross and net availability):
    def _get_sql_store_qty(self, cr, uid, ids, fields, args, context = None):
        ''' Get total amount (multi function)
        '''
        res = {}
        
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = {}
            
            # TODO test value for BS
            net = product.sql_inventary + product.sql_load - product.sql_unload - product.sql_bs
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
        'sql_bs': fields.float('BS', digits=(10,5), 
            help="Depend on database value but according to inventory date and value in product form"),

        # Override fields for new compute method:
        'sql_net': fields.function(
            _get_sql_store_qty, method=True, type='float', string='Net', store=False, multi='availability'),
        'sql_availability_net': fields.function(
            _get_sql_store_qty, method=True, type='float', string='Availability net', store=False, multi='availability'),
        'sql_availability_gross': fields.function(
            _get_sql_store_qty, method=True, type='float', string='Availability gross', store=False, multi='availability'),
        
        # Force inventory:    
        'inventory_quantity': fields.float('Inventory quantity', digits=(16, 5)),
        'inventory_date': fields.date('Inventory Date'),
        'inventory_updated': fields.boolean('Inventory updated', help="Inventory update also in accounting program"),        
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
