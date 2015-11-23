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

class sql_move_line(osv.osv):
    ''' Add a back door for return if problems (
    '''
    _inherit = 'sql.move.line'
    
    def force_unification_partner(self, cr, uid, context=None):
        ''' Force unification for partner double
            Re assign all movement line
        '''
        partner_pool = self.pool.get('res.partner')
        
        # -----------------------------------------
        # Read customer for get convert dictionary:
        # -----------------------------------------
        customer_ids = partner_pool.search(cr, uid, [
            ('sql_customer_code', '!=', False),
            ('sql_import', '=', True),
            ('type', '=', 'default'),            
            ], context=context)
        customer_db = {}
        _logger.info('Customer total: %s' % len(customer_ids))
        for customer in partner_pool.browse(cr, uid, customer_ids, 
                context=context):
            customer_db[customer.sql_customer_code] = customer.id
            
        # -----------------------------------------
        # Read supplier for get convert dictionary:
        # -----------------------------------------
        supplier_ids = partner_pool.search(cr, uid, [
            ('sql_supplier_code', '!=', False),
            ('sql_import', '=', True),
            ('type', '=', 'default'),            
            ], context=context)
        supplier_db = {}
        _logger.info('Supplier total: %s' % len(supplier_ids))
        for supplier in partner_pool.browse(cr, uid, supplier_ids, 
                context=context):
            supplier_db[supplier.sql_supplier_code] = supplier.id
            
        # ---------------------------------------
        # Read destination for correct operation:
        # ---------------------------------------
        destination_ids = partner_pool.search(cr, uid, [
            ('sql_destination_code', '!=', False),
            ('sql_import', '=', True),
            ('type', '=', 'contact'),
            ], context=context)
            
        i = 0
        remove_destination = [] # to remove and correct move line
        _logger.info('Destination total: %s' % len(destination_ids))
        for destination in partner_pool.browse(cr, uid, destination_ids, 
                context=context):
            i += 1
            code = destination.sql_destination_code
            data = {}
            if not code:
                _logger.error('%s. Destination without code, ID: %s' % (
                    i, code))
                continue # remove this code?

            if code in customer_db:
                if not destination.remove:
                    data.update({
                        'name': '[RIMUOVERE] %s' % destination.name,
                        'bugfix_id': customer_db[code], # real customer
                        'remove': True,
                        })
                    remove_destination.append(destination.id)    
                    _logger.info('%s. CUSTOMER: Code: %s ID: %s' % (
                        i, code, customer_db[code]))
            else:
                if code in supplier_db:
                    if not destination.remove:
                        data.update({
                            'name': '[RIMUOVERE] %s' % destination.name,
                            'bugfix_id': supplier_db[code], # real supplier
                            'remove': True,
                            })
                        remove_destination.append(destination.id)    
                        _logger.info('%s. SUPPLIER: Code: %s ID: %s' % (
                            i, code, supplier_db[code]))
                else:
                    # General Account:
                    if not destination.remove: # Tengo i movimenti, no rimoz.
                        data.update({
                            'name': '[??RIMUOVERE??] %s' % destination.name,
                            'remove': True,
                            })
                        remove_destination.append(destination.id)    
                        _logger.warning('%s. NOT FOUND: Code %s [%s]' % (
                            i, code, destination.name))
            if data:            
                partner_pool.write(
                    cr, uid, destination.id, data, context=context)

        # Update all lines from destination to client or supplier:        
        _logger.info('Destination total: %s' % len(remove_destination))
        move_ids = self.search(cr, uid, [
            ('partner_id', 'in', remove_destination)], context=context)
            
        i = 0
        _logger.info('Destination movement total: %s' % len(move_ids))
        for move in self.browse(cr, uid, move_ids, context=context):
            i += 1
            if not move.bugfix_old_id: # update only once
                data = {'bugfix_old_id': move.partner_id.id}
                mode = 'UPDATE BUG ID'
            else: 
                data = {}      
                move = 'ONLY PARTNER'  
            if move.partner_id.bugfix_id.agent_code: # speed up?
                data.update({
                    'agent_code': move.partner_id.bugfix_id.agent_code,
                    })                
            data.update({
                'partner_id': move.partner_id.bugfix_id.id,
                })    
                
            self.write(cr, uid, move.id, data, context=context)
            _logger.info("%s. Update move: %s data: %s" % (i, mode, data))
            
        _logger.info('Update destination movement: %s' % i)
            
        # TODO delete all destination:
        #_logger.info('Remove destination: %s' % len(remove_destination))
        #partner_pool.unlink(cr, uid, remove_destination, context=context)        
        _logger.info('End bugfix')
        return True                
        
    _columns = {
        'bugfix_old_id': fields.many2one('res.partner', 'Bugfix old ID'),
        }

class res_partner(osv.osv):
    ''' Add partner ref 
        Bugfix = record to delete (ref to original partner)
    '''
    _inherit = 'res.partner'
    
    _columns = {
        'bugfix_id': fields.many2one('res.partner', 'Bugfix ID'),        
        'remove': fields.boolean('To remove'),
        }    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
