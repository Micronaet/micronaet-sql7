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

class move_prefilter_wizard(osv.osv_memory):
    ''' Prefilter wizard
    '''
    _name = "sql.move.prefilter.wizard"

    # ------------------------------
    # Button function of the wizard:
    # ------------------------------
    def calculate_range(self, cr, uid, ids, context=None): 
        ''' Generate range elements
        '''        
        if context is None:
            context = {}
        
        _logger.info("Start filter process")
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]
        totals = {}

        move_pool = self.pool.get('sql.move.line')
        move_ids = move_pool.search(cr, uid, [], context=context)
        move_proxy = move_pool.browse(cr, uid, move_ids, context=context)

        # Group by totals:
        for item in move_proxy:
            if wiz_proxy.group == 'partner':
                if item.partner_id.id not in totals:
                    totals[item.partner_id.id] = [0.0, []]
                element = totals[item.partner_id.id]
            elif wiz_proxy.group == 'product':
                if item.product_id.id not in totals:
                    totals[item.product_id.id] = [0.0, []]
                element = totals[item.product_id.id]                    
            elif wiz_proxy.group == 'code3':
                if item.code3 not in totals:
                    totals[item.code3] = [0.0, []]
                element = totals[item.code3]
            elif wiz_proxy.group == 'code5':
                if item.code5 not in totals:
                    totals[item.code5] = [0.0, []]
                element = totals[item.code5]
            #elif wiz_proxy.qroup == 'nation':
                                
            element[0] += item.__getattr__(wiz_proxy.total) #  * move_pool.sign[item.type] 
            element[1].append(item.id)                   
            
        _logger.info("Filter totalizing")
        ranges = {0: [], 1: [], 2: [], 3: [], 4: [], }    
        for key in totals:
            item = totals[key]
            if item[0] <= 0.0:
                ranges[0].extend(item[1])
            elif item[0] < wiz_proxy.range1:
                ranges[1].extend(item[1])
            elif item[0] < wiz_proxy.range2:
                ranges[2].extend(item[1])
            elif item[0] < wiz_proxy.range3:
                ranges[3].extend(item[1])
            else:
                ranges[4].extend(item[1])
                
        # Write on DB
        _logger.info("Filter update range:")
        for key in ranges:
            _logger.info("  > Update range %s:" % key)            
            move_pool.write(cr, uid, ranges[key], {'range': key}, context=context)                
                
        return True
        
    _columns = {
        'group': fields.selection([
            ('partner', 'Partner'),
            ('product', 'Product'),
            ('code3', 'Product code 3'),
            ('code5', 'Product code 5'),
            ('nation', 'Nation'),            
        ], 'Groub by', required=True),

        'total': fields.selection([
            ('analysis_quantity', 'Quantity'),
            ('analysis_total', 'Value'),
        ], 'Field total', required=True),

        'range1': fields.float('Range 1', digits=(16, 2), required=True
            , help=">=0 <Range 1"),
        'range2': fields.float('Range 2', digits=(16, 2), required=True
            , help=">=Range 1 <Range 2"),
        'range3': fields.float('Range 3', digits=(16, 2), required=True
            , help=">=Range 2 <Range 3"),
        }

    _defaults = {
        'group': lambda *x: 'partner',
        'total': lambda *x: 'analysis_total',
        'range1': lambda *x: 10000.0,
        'range2': lambda *x: 20000.0,
        'range3': lambda *x: 30000.0,
        }        

class etl_move_line_range(osv.osv):
    ''' Add range to movement
    '''    
    _name = 'sql.move.line'
    _inherit = 'sql.move.line'

    _columns = {
        'range': fields.selection([
            (0, 'No move or negative'),
            (1, '< R1'),
            (2, '< R2'),
            (3, '< R3'),
            (4, 'Oversize'),
        ], 'Range'),
        }

    _defaults = {
        'range': lambda *x: 1,
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
