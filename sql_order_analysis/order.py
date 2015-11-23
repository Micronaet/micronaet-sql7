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

class sql_order(osv.osv):
    ''' Object populated with order
    '''    
    _name = 'sql.order'
    _description = 'SQL Order'
    _order = 'name'
    
    # Scheduled action: ########################################################
    def schedule_sql_order_line_import(self, cr, uid, verbose_log_count = 0, context=None):
        ''' Import order line (only active)
        '''
        try:
            from openerp.addons.base_mssql.tools import conversion
            
            _logger.info("Start scheduled import Order!")
            order_line_proxy=self.pool.get("sql.order.line")
            partner_proxy=self.pool.get("res.partner")
            product_proxy=self.pool.get('product.product')
            utility_proxy = self.pool.get('micronaet.accounting') # Query

            # -------------------------
            # Import order header data: 
            # -------------------------
            _logger.info("Start import Order header!")
            
            cursor = utility_proxy.get_oc_header(cr, uid, context=context)    
            if not cursor:
                _logger.error("Unable to connect no importation of order header data!")
                return False

            i = 0
            order_header = {} # conversion tool
            for record in cursor:
                break
                try:
                    i += 1
                    if verbose_log_count and i % verbose_log_count == 0:
                        _logger.info('Order %s: record imported / updated!' % (i, ))                             

                    name = utility_proxy.KEY_OC_FORMAT % (record) # Create key
                    date = record.get('DTT_DOC').strftime("%Y-%m-%d")
                    partner_code = record.get('CKY_CNT_CLFR', False)
                    partner_id = partner_proxy.get_partner_from_sql_code(cr, uid, partner_code, context = context)
                    #if not partner_id:
                    #    _logger.error('Partner not found: %s!' % (partner_code, ))
                    note = record.get('CDS_NOTE', False)
                    # TODO vettore?? CKY_CNT_VETT
                    # TODO agente?? CKY_CNT_AGENTE, 
                    # TODO destinatione?? CKY_CNT_SPED_ALT

                    data = {
                        'name': name,
                        'date': date,
                        'partner_id': partner_id,
                        'note': note,                        
                    }
                    item_id = self.search(cr, uid, [('name', '=', name)])
                    # TODO: remove order not finded
                    if item_id: 
                        self.write(cr, uid, item_id, data)
                        order_header[name] = item_id[0]
                    else:
                        order_header[name] = self.create(cr, uid, data)
                        
                except:
                    _logger.error('[%s] Error importing order, jumped: %s' % (i, order, ))
                    continue                    

            # ------------------
            # Import move lines: 
            # ------------------
            _logger.info("Start import Order line!")
            cursor = utility_proxy.get_oc_line(cr, uid, context=context)    
            if not cursor:
                _logger.error("Unable to connect no importation of order line!")
                return False

            i = 0
            for record in cursor:
                break
                try:
                    i += 1
                    if verbose_log_count and i % verbose_log_count == 0:
                        _logger.info('Order line %s: record imported / updated!' % (i, ))                             

                    name = utility_proxy.KEY_OC_LINE_FORMAT % (record) # Create line key
                    order = utility_proxy.KEY_OC_FORMAT % (record)     # Create order key
                    order_id = order_header[order]
                    if not order_id:
                        _logger.error('Order header not found (line jumped)!: %s' % (order, ))                             
                        continue
                    
                    sequence = record.get('NPR_SORT_RIGA', 0) 
                    deadline = record.get('DTT_SCAD').strftime("%Y-%m-%d") # TODO empty date?  use no_date(data_value)

                    product_id = product_proxy.get_product_from_sql_code(
                        cr, 
                        uid, 
                        record.get('CKY_ART', False), 
                        context = context)                        
                    #if not product_id:
                    #    _logger.error('Product not found: %s!' % (default_code, ))                             

                    #quantity = record.get('NPZ_UNIT', 0.0)
                    #total = record.get('NQT_RIGA_O_PLOR', 0.0)

                    # TODO: remove line non finded
                    data = {
                        'name': name,              # OC-TYPE-REF-LINE
                        'order_id': order_id,      # OC-TYPE-REF
                        'sequence': sequence,
                        'deadline': deadline,
                        'product_id': product_id,
                        #'quantity': quantity,
                        #'unit_price': unit_price,
                        #'total': total,
                    }
                    item_id = order_line_proxy.search(cr, uid, [('name', '=', name)])
                    if item_id: # update:
                        order_line_proxy.write(cr, uid, item_id, data)
                    else:    
                        order_line_proxy.create(cr, uid, data)
                except:
                    _logger.error('[%s] Error importing order line, jumped: %s' % (i, name, ))
                    continue

            # -------------------------
            # Import move lines (funz):
            # -------------------------
            _logger.info("Start import Order function line!")
            cursor = utility_proxy.get_oc_funz_line(cr, uid, context=context)    
            if not cursor:
                _logger.error("Unable to connect no importation of order function line!")
                return False

            i = 0
            for record in cursor:
                try:
                    i += 1
                    if verbose_log_count and i % verbose_log_count == 0:
                        _logger.info('Order line %s: record imported / updated!' % (i, ))                             

                    
                    name = utility_proxy.KEY_OC_LINE_FORMAT % (record) # Create line key
                    quantity = record.get('NQT_MOVM_UM1', 0.0)
                    total = record.get('NMP_VALMOV_UM1', 0.0)
                    unit_price = (total / quantity) if quantity else 0.0

                    data = {
                        'quantity': quantity,
                        'unit_price': unit_price,
                        'total': total,
                        'agent_cost': record.get('NMP_PROVV_VLT', 0.0),
                    }
                    item_id = order_line_proxy.search(cr, uid, [('name', '=', name)])
                    if item_id: # update:
                        order_line_proxy.write(cr, uid, item_id, data)
                except:
                    _logger.error('[%s] Error importing order functional line, jumped: %s' % (i, name, ))
                    continue
                    
        except:
            _logger.error('Generic error importing order')

        _logger.info("End scheduled import Order!")            
        return True

    # Function fields:
    def _get_total_order(self, cr, uid, ids, fields, args, context = None):
        ''' Get total from all lines (sum subtotal and cost agend
        '''
        res = {}
        for order in self.browse(cr, uid, ids, context = context):
            res[order.id] = {'total': 0.0,
                             'agent_total': 0.0,
                             }
            for line in order.line_ids:
                res[order.id]['total'] += line.total
                res[order.id]['agent_total'] += line.agent_cost
        return res        
        
    _columns = {
        'name':fields.char('Order', size=24, required=True, readonly=False, help = 'Order code',),
        'date': fields.date('Date', help="Date when order is created"),
        'partner_id':fields.many2one('res.partner', 'Partner', required=False),
        #'total': fields.float('Total amount', digits=(16, 2)),
        'total': fields.function(_get_total_order, method=True, type='float', string='Order total', store = True, multi = True),        
        'agent_total': fields.function(_get_total_order, method=True, type='float', string='Agent total', store = True, multi = True),        
        'note': fields.text('Note'),
        # agent_id
        # vector
        # destination        
    }

class sql_order_line(osv.osv):
    ''' Object populated with order line
    '''
    _name = 'sql.order.line'
    _order = 'name,sequence'
    _description = 'SQL Order line'
    
    _columns = {
        'name':fields.char('Number', size=24, required=True, readonly=False, help = 'Order line code',),
        # TODO remove after create order:
        #'order':fields.char('Order code', size=16, required=True, readonly=False, help = 'Order header code'),
        'order_id':fields.many2one('sql.order', 'Order', required=False, ondelete = 'cascade'),
        'sequence': fields.integer('Sequence'),
        
        #'date': fields.date('Date', help="Date when order is created"),
        'date': fields.related('order_id','date', type='date', string='Date', store = True),
        #'partner_id':fields.many2one('res.partner', 'Partner', required=False),
        'partner_id': fields.related('order_id','partner_id', type='many2one', relation='res.partner', string='Partner', store=True),
        
        'deadline': fields.date('Deadline', help="Deadline for statistic evaluation of delivery"),
        'product_id':fields.many2one('product.product', 'Product', required=False, ondelete = 'set null'),
        'quantity': fields.float('Quantity', digits=(16, 5)),  
        'unit_price': fields.float('Unit price', digits=(16, 5)),
        'agent_cost': fields.float('Agent cost', digits=(16, 5)),  
        'total': fields.float('Total amount', digits=(16, 5)),
        
        #'delivered': fields.float('Total delivered', digits=(16, 2)),
        #'expected': fields.float('Total expected', digits=(16, 2)),
        #'left': fields.float('Total left', digits=(16, 2)),
    }
    
class sql_order(osv.osv):
    ''' Add 2many fields
    '''    
    _name = 'sql.order'
    _inherit = 'sql.order'
    
    _columns = {
        'line_ids':fields.one2many('sql.order.line', 'order_id', 'Line', required=False),
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
