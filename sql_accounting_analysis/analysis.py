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
from openerp.osv import osv, orm, fields
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class etl_move_line(osv.osv):
    ''' Objetc populated with accounting movement
    '''    
    _name = 'sql.move.line'
    _order = 'name'
    _description = 'ETL Move line'
    
    movement_type = [
        ('BC', _('DDT customer (BC)')),       # - (sale analysis)
        ('FT', _('Customer invoice (FT)')),   # - (sale analysis
        ('NC', _('Credit note (NC)')),        # + (sale analysis
        ('RC', _('Refund (RC)')),             # + (sale analysis
        ('BF', _('DDT supplier (BF)')),       # +
        ('CL', _('Lavoration load (CL)')),    # +
        ('SL', _('Lavoration unload (SL)')),  # - 
        ('BS', _('Unload document (BS)')),    # -
        ('FF', _('Supplier invoice (FF)')),   # +
        ('BD', _('Deposit document (BD)')),   # - stock origin e + stock destination (use -)
        ('DL', _('Working deposit (DL)')),    # -
        ('RF', _('Refund supplier (RF)')), ]  # -
     
    # movement for sell analysis
    movement_sell = ['BC', 'FT', 'NC', 'RC', ]
    
    sign = {
        'BC': -1, 'FT': -1, 'NC': +1, 'RC': +1, 'BF': +1, 'CL': +1, 'SL': -1,
        'BS': -1, 'FF': +1, 'BD': -1, 'DL': -1, 'RF': -1, }

    # Function fileds:
    def _get_unit_price(self, cr, uid, ids, fields, args, context=None):
        ''' Calculate unit price
        '''
        res = {}
        for item in self.browse(cr, uid, ids, context=context):
            if item.quantity:
                res[item.id] = abs(item.total / item.quantity)
            else:
                res[item.id] = 0.0            
        return res    
        
    _columns = {
        'name': fields.char('Ref. document', size=24, required=True, 
            readonly=False, help = 'Line references, is like a key'),
        'header': fields.char('Ref. document', size=24, required=True, 
            readonly=False, help = 'Header document information'),

        'date': fields.date('Date', help="Date when order is created"),
        'deadline': fields.date('Deadline', 
            help="Deadline for statistic evaluation of delivery"),
        #'amount': fields.float('Total amount', digits=(16, 2)),

        'partner_id': fields.many2one('res.partner', 'Partner', required=False),
        'partner_name': fields.related('partner_id', 'name', type='char',
             string='Partner name', store=True),

        'product_id': fields.many2one('product.product', 'Product', required=False),
        'parent_product_id': fields.many2one('product.product', 'Product parent', required=False),
        'product_description': fields.char('Product description', size=72, 
            required=False, readonly=False, help='Product description'),
        'lot': fields.char('Lot', size=8),
        'product_name': fields.related('product_id', 'name', type='char',
            string='Product name', store=True),

        'note': fields.text('Note'),

        # TODO remove after debug
        #'import_note': fields.text('Import note'),
        'unit_price': fields.function(_get_unit_price, method=True, 
            type='float', digits=(16, 5), string='Unit price', store=False),
        'quantity': fields.float('Quantity', digits=(16, 5)),  
        'analysis_quantity': fields.float('Analysis quantity', digits=(16, 5)),  

        'total': fields.float('Amount', digits=(16, 5)),
        'analysis_total': fields.float('Analysis amount', digits=(16, 5),
            help='Same as total but inverted sign (usd for manager analysis, FT in account is -, for manager is +)'),
        #'delivered': fields.float('Total delivered', digits=(16, 2)),
        #'expected': fields.float('Total expected', digits=(16, 2)),
        #'left': fields.float('Total left', digits=(16, 2)),
        'type': fields.selection(movement_type, 'State', select=True, readonly=False),
    }

    # Scheduled action: #######################################################
    def schedule_etl_move_line_import(self, cr, uid, parent_product=0,
        verbose_log_count=500, only_analysis=True, debug_limit=0,
        lot_range=(0, 0), only_movement_list=False, context=None):
        ''' Import movement from external DB:
            parent_product: number of char of product code to identify the parent code 
                            (program search also parent product ID
            lot_range: if present is the range of char where lot is localized: (from, to)
            verbose_log_count: number or record for verbose log importation
            only_analysis: import only movement for sold analysis (else all)
            debug_limit: tot record of MM imported (for debug purposes)
            movement_list: list of document to import movement 
        '''
        from openerp.addons.base_mssql.tools import conversion

        _logger.info("Start import movement!")
        try:
            order_line_proxy = self.pool.get("sql.move.line")
            partner_proxy = self.pool.get("res.partner")
            product_proxy = self.pool.get('product.product')
            accounting_proxy = self.pool.get('micronaet.accounting')

            lot_exist = any(lot_range)
            movement_list = [item[0] for item in self.movement_type] # general list for check correct code doc.
            if only_movement_list: # import only some document: (in this case there's not test for only:_analyisis)
                if type(only_movement_list) not in (tuple, list): # string (single value)
                    only_movement_list = [only_movement_list, ]
            else:                    
                if only_analysis: # search only document for analysis
                    only_movement_list = [item[0] for item in self.movement_sell]
                else: # All known docs
                    only_movement_list = movement_list 

            # ------------------
            # Import move lines: 
            # ------------------
            _logger.info("Start import movement line!")
            cursor = accounting_proxy.get_mm_line(
                cr, uid, where_document=only_movement_list, context=context) 
            if not cursor:
                _logger.error("Unable to connect no importation of movement line!")
                return False

            i = 0
            for record in cursor:        
                try:
                    i += 1                    
                    name = str(accounting_proxy.KEY_MM_LINE_FORMAT % (record))
                    header = accounting_proxy.KEY_MM_HEADER_FORMAT % (record)
                    type_value = record['CSG_DOC'].upper()

                    # For debug purposes:
                    if debug_limit and i > debug_limit:
                        break
                        
                    if verbose_log_count and i % verbose_log_count == 0:
                        _logger.info('Line %s: record imported / updated!' % (i, ))                             

                    default_code = record['CKY_ART']
                    product_id = product_proxy.get_product_from_sql_code(
                        cr, uid, default_code, context=context)                    

                    # TODO log and comunicate what lines are not included!                    
                    if not product_id:
                        # Create a minimal product for go ahead
                        product_id = product_proxy.fast_product_create(
                            cr, uid, default_code, context=context)
                        _logger.warning('Line %s Product create [%s]!' % (
                            name, default_code))                             
                     
                    lot = False
                    if parent_product and len(default_code) > parent_product:
                        # Parent:
                        parent_product_id = product_proxy.get_product_from_sql_code(
                            cr, uid, default_code[:parent_product], 
                            context=context)                    

                        # TODO parametrize force creation of parent product!!!
                        if not parent_product_id:
                            parent_product_id = product_proxy.fast_product_create(
                                cr, uid, default_code[:parent_product], context=context)
                            _logger.warning('Line %s Parent product create [%s]!' % (
                                name, default_code[:parent_product]))                             

                        # Lot:
                        try:
                            if lot_exist:
                                lot = default_code[lot_range[0]:lot_range[1]]
                        except:
                            lot = False                            
                    else:
                        parent_product_id = False    
                                              
                    data = {
                        # Movement line:
                        'name': name,        # line key
                        'header': header,    # header key
                        'deadline': conversion.get_date(record['DTT_SCAD']),
                        'product_id': product_id,
                        'product_description': record['CDS_VARIAB_ART'],
                        'parent_product_id': parent_product_id,
                        'lot': lot,
                        'type': type_value,
                    }
                    item_id = self.search(cr, uid, [('name', '=', name)])
                    if item_id:
                        item_id = item_id[0]
                        self.write(cr, uid, item_id, data)                            
                    else:    
                        item_id = self.create(cr, uid, data)

                except:
                    _logger.error('Line [%s] Error jumped! [%s]' % (
                        name,
                        sys.exc_info()))
                    continue

            # --------------------
            # Update funz element: 
            # --------------------
            _logger.info("Start import functional movement line!")
            cursor = accounting_proxy.get_mm_funz_line(cr, uid, where_document = only_movement_list, context=context) 
            if not cursor:
                _logger.error("Unable to connect no importation of funz line!")
                return False

            i = 0
            for record in cursor:
                try:
                    i += 1
                    if verbose_log_count and i % verbose_log_count == 0:
                        _logger.info('Funz. line %s: record imported / updated!' % (i, ))                             

                    name = str(accounting_proxy.KEY_MM_LINE_FORMAT % (record))
                    type_value = record['CSG_DOC'].upper()

                    # For debug purposes:
                    if debug_limit and i > debug_limit: break

                    total = self.sign.get(type_value, 1) * record['NMP_VALMOV_UM1']
                    quantity = self.sign.get(type_value, 1) * record['NQT_MOVM_UM1']
                    data = {
                        'quantity': quantity,
                        'analysis_quantity': -(quantity),
                        'total': total, 
                        'analysis_total': -(total),
                    }
                    try: 
                        item_id = self.search(cr, uid, [('name','=',name)])
                        if item_id:
                            self.write(cr, uid, item_id, data)                            
                    except:
                        continue # not found (jump line) # TODO log!

                except:
                    _logger.error('Line [%s] Error importing record, jumped!' % (i, ))
                    continue

            # -------------------
            # Update with header: 
            # -------------------
            _logger.info("Start import header!")
            cursor = accounting_proxy.get_mm_header(cr, uid, where_document = only_movement_list, context=context) 
            if not cursor:
                _logger.error("Unable to connect no importation of header list!")
                return False
                                
            i = 0
            for record in cursor:
                try:
                    i += 1
                    # For debug purposes:
                    if debug_limit and i > debug_limit:
                        break
                        
                    header = accounting_proxy.KEY_MM_HEADER_FORMAT % (record)
                    partner_id = partner_proxy.get_partner_from_sql_code(cr, uid, record['CKY_CNT_CLFR'], context = context)
                    if not partner_id:
                        _logger.error('Header %s - Partner not found: [%s]!' % (header, record['CKY_CNT_CLFR'], ))
                    
                    data = {
                        'date': conversion.get_date(record['DTT_DOC']),
                        'partner_id': partner_id,
                        'note': record['CDS_NOTE'],
                    }
                    # only update lines with headers falue (line must exist)
                    item_ids = self.search(cr, uid, [('header', '=', header)]) # N lines with this header
                    if item_ids:
                        updated = self.write(cr, uid, item_ids, data)
                    
                    if verbose_log_count and i % verbose_log_count == 0:
                        _logger.info('Header %s: records imported / updated!' % (i, ))                             
                except:
                    _logger.error('[%s] Error importing records, jumped: %s' % (i, record, ))
                    continue
            _logger.info('End importation. All record is updated!')
        except:
            _logger.error('Error generic import movement lines: %s' % (sys.exc_info(), ))
            return False
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
