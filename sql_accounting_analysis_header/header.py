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
import netsvc
import logging
from openerp.osv import osv, orm, fields
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class etl_move_line(osv.osv):
    ''' Objetc populated with accounting movement header
    '''    
    _name = 'sql.move.header'
    _order = 'name'
    _description = 'ETL Move header'

    # ----------------------------------------
    # Utility function for fields (to remove):
    # ----------------------------------------
    def force_header_id(self, cr, uid, ids, context=None):
        ''' Search header field in sql.move.header and link header_id 
            fields for link the lines to the header
            (act as a button for speed up operation)
        '''
        line_pool = self.pool.get("sql.move.line")
        move_ids = line_pool.search(cr, uid, [], context=context)
        for item in line_pool.browse(cr, uid, move_ids, context=context):
            header_id = self.search(cr, uid, [
                ('name', '=', item.header)], context=context)
            if header_id:
                line_pool.write(cr, uid, item.id, {
                    'header_id': header_id[0]
                    }, context=context) 
            else:
                _logger.warning("Header not found: %s!" % item.header)
        return True       

    def force_total(self, cr, uid, ids, context=None):
        ''' Force total from lines
        '''
        header_ids = self.search(cr, uid, [], context=context)
        for item in self.browse(cr, uid, header_ids, context=context):
            total = 0.0
            for line in item.line_ids:
                total += line.total
            if total:    
                self.write(cr, uid, item.id, {
                    'total': total,
                    'analysis_total': -total,
                    }, context=context)
        return True       

    def force_number(self, cr, uid, ids, context=None):
        ''' Force total from lines
        '''
        header_ids = self.search(cr, uid, [], context=context)
        for item in self.browse(cr, uid, header_ids, context=context):
            try:
                self.write(cr, uid, item.id, {
                    'number': int(item.name.split("-")[-1]),
                    }, context=context)
            except:
                _logger.error("Cannot see number in %s" % name)        
        return True       

    # -----------------
    # Scheduled action:
    # -----------------
    def schedule_etl_move_header_import(self, cr, uid, context=None):
        ''' Import header movements
        '''
        from openerp.addons.base_mssql.tools import conversion

        _logger.info("Start import movement header!")
        agent_list = []
        try:
            partner_proxy = self.pool.get("res.partner")
            product_proxy = self.pool.get('product.product')
            accounting_proxy = self.pool.get('micronaet.accounting')
            payment_proxy = self.pool.get('account.payment.term')
            reason_proxy = self.pool.get('stock.picking.transportation_reason')

            # ------------------
            # Import move header: 
            # ------------------
            cursor = accounting_proxy.get_mm_header(
                cr, uid, context=context) 
            if not cursor:
                _logger.error(
                    "Unable to connect no importation of movement header!")
                return False

            i = 0
            for record in cursor:        
                try:
                    i += 1                    
                    name = accounting_proxy.KEY_MM_HEADER_FORMAT % (record)
                   
                    if i % 500 == 0:
                        _logger.info('Header %s: record imported/updated!' % i)                             

                    partner_id = partner_proxy.get_partner_from_sql_code(
                        cr, uid, record['CKY_CNT_CLFR'], context = context)
                    agent_id = partner_proxy.get_partner_from_sql_code(
                        cr, uid, record['CKY_CNT_AGENTE'], context=context)
                    reason_id = reason_proxy.get_transportation(
                        cr, uid, record['NKY_CAUM'], context = context)

                    if agent_id and agent_id not in agent_list:
                        agent_list.append(agent_id)
                        
                    data = {
                        # Movement line:
                        'name': name, # line key
                        'date': conversion.get_date(record['DTT_DOC']),
                        'type': record['CSG_DOC'].upper(),
                        'partner_id': partner_id,
                        'agent_id': agent_id,
                        'reason_id': reason_id,
                        'note': record['CDS_NOTE'],
                        #'total': 0.0,
                        #'analysis_total': 0.0,
                    }
                    item_id = self.search(cr, uid, [('name', '=', name)])
                    if item_id:
                        item_id = item_id[0]
                        self.write(cr, uid, item_id, data, context=context)
                    else:    
                        item_id = self.create(cr, uid, data, context=context)
                except:
                    _logger.error(
                        'Header [%s] Error importing, jumped! [%s]' % (
                            name,
                            sys.exc_info(), ))
                    continue

            # -----------------
            # Update foot info: 
            # -----------------
            _logger.info("Start import movement footer!")
            cursor = accounting_proxy.get_mm_footer(cr, uid, context=context) 
            if not cursor:
                _logger.error(
                    "Unable to connect no importation of movement footer!")
                return False

            i = 0
            for record in cursor:        
                try:
                    i += 1                    
                    name = accounting_proxy.KEY_MM_HEADER_FORMAT % (record)
                   
                    if i % 500 == 0:
                        _logger.info('Footer %s: record imported/updated!' % i)                             

                    payment_id = payment_proxy.get_payment(
                        cr, uid, record['NKY_PAG'], context = context)

                    item_id = self.search(cr, uid, [('name', '=', name)])
                    if item_id:
                        self.write(cr, uid, item_id[0], {
                            'payment_id': payment_id,
                            }, context=context)
                    else:    
                        pass # jump
                except:
                    _logger.error(
                        'Header [%s] Error importing, jumped! [%s]' % (
                            name,
                            sys.exc_info(), ))
                    continue

            # Update agent list:
            if agent_list:
                partner_proxy.write(cr, uid, agent_list, {
                    'is_agent': True}, context=context) # TODO reset before?

            _logger.info('End importation. All header is updated!')
        except:
            _logger.error('Error generic import header lines: %s' % (
                sys.exc_info(), ))
            return False
        return True

    # ------------------------
    # Field utility functions:    
    # ------------------------
    def _get_movement_list(self, cr, uid, context=None):
        ''' Get list of movement from move line class
        '''    
        return self.pool.get('sql.move.line').movement_type   
        
    _columns = {
        'name': fields.char('Ref. document', size=24, required=True, readonly=False, help = 'Header document information'),
        'number': fields.integer('Number'),

        'date': fields.date('Date', help="Date when order is created"),
        'deadline': fields.date('Deadline', help="Deadline for statistic evaluation of delivery"),
        #'amount': fields.float('Total amount', digits=(16, 2)),

        'partner_id': fields.many2one('res.partner', 'Partner'),
        'partner_name': fields.related('partner_id', 'name', type='char', 
            string='Partner name', store=True),
        'agent_id': fields.many2one('res.partner', 'Agent',), 
        'payment_id': fields.many2one('account.payment.term', 'Payment term'),
        'reason_id': fields.many2one('stock.picking.transportation_reason', 
            'Transportation reason'),

        'note': fields.text('Note'),

        'total': fields.float('Amount', digits=(16, 5)),
        'analysis_total': fields.float('Amount', digits=(16, 5), 
            help="Used for analysis purpose (usually is equal to -(total)"),
        'type': fields.selection(_get_movement_list, 'State', select=True, readonly=False),
    }

class etl_move_line(osv.osv):
    ''' Extra relation fields:
    '''    
    _name = 'sql.move.line'
    _inherit = 'sql.move.line'
                
    _columns = {
        'header_id': fields.many2one('sql.move.header', 'Header', 
            ondelete='cascade'),
        }

class etl_move_header(osv.osv):
    ''' Extra relation fields:
    '''    
    _name = 'sql.move.header'
    _inherit = 'sql.move.header'
    
    _columns = {
        'line_ids': fields.one2many('sql.move.line', 'header_id', 'Lines'),
        }

class res_partner(osv.osv):
    ''' Add extra field for partner
    '''
    _name = 'res.partner'
    _inherit = 'res.partner'
    
    _columns = {
        'is_agent': fields.boolean('Agent'),
    }
        
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
