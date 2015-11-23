# -*- encoding: utf-8 -*-
###############################################################################
#
#    OpenERP module
#    Copyright (C) 2010 Micronaet srl (<http://www.micronaet.it>) 
#    
#    Italian OpenERP Community (<http://www.openerp-italia.com>)
#
##############################################################################
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
###############################################################################
import sys
import os
from openerp.osv import osv, fields
from datetime import datetime, timedelta
import logging


_logger = logging.getLogger(__name__)

class sql_move_line(osv.osv):
    ''' Extend sql.move.line
    '''    
    _inherit = 'sql.move.line'
    
    def _force_agent_code_update(self, cr, uid, ids, context=None):
        ''' Update line when change partner
        '''
        return self.pool.get('sql.move.line').search(cr, uid, [
            ('partner_id', 'in', ids)], context=context)
        
    _columns = {
        # Agent info:
        'agent_code': fields.related('partner_id', 'agent_code', 
            type='char', size=15, string='Agent code', 
            store={'res.partner': 
                [_force_agent_code_update, ['agent_code'], 10]}),
        }

class res_partner(osv.osv):
    ''' Extend res.partner
    '''    
    _inherit = 'res.partner'
    
    _columns = {
        # Agent info:
        'has_agent': fields.boolean('Has agent', required=False),
        'agent_code': fields.char('Agent code', size=15),
        'agent_id':fields.many2one('res.partner', 'Agent', required=False),
    }
    
    # -------------------------------------------------------------------------
    #                              Scheduled action
    # -------------------------------------------------------------------------
    def schedule_sql_partner_commercial_import(self, cr, uid, 
            only_precence=True, verbose_log_count=100, context=None):
        ''' Import partner commercial info
        '''            

        try:
            partner_proxy = self.pool.get('res.partner')
            company_pool = self.pool.get('res.company')
            company_proxy = company_pool.get_from_to_dict(
                cr, uid, context=context)
            if not company_proxy:
                _logger.error('Company parameters not setted up!')

            # Customer range
            from_code = company_proxy.sql_customer_from_code
            to_code =  company_proxy.sql_customer_to_code
            
            cursor = self.pool.get(
                'micronaet.accounting').get_partner_commercial(
                    cr, uid, from_code, to_code, context=context) 
            if not cursor:
                _logger.error(
                    "Unable to connect, no importation partner commercial list!")
                return False

            _logger.info('Start import from: %s to: %s' % (
                from_code, to_code))
            i = 0
            for record in cursor:
                i += 1
                if verbose_log_count and i % verbose_log_count == 0:
                    _logger.info('Import: %s record imported / updated!' % i)
                    
                try:                        
                    data = {
                        'has_agent': record['CKY_CNT_AGENTE'],
                        'agent_code': record['CKY_CNT_AGENTE'],
                        'agent_id': False, 
                        # TODO search correctly with: partner_proxy.search
                        #    (cr, uid, [(key_field, '=', record['CKY_CNT'])])
                        # usabile: get_partner_from_sql_code (
                        #    self, cr, uid, code, context = None)
                        }
                    # Search code to update:
                    partner_ids = partner_proxy.search(cr, uid, [
                        ('sql_customer_code', '=', record['CKY_CNT'])])
                    if partner_ids: # update
                        partner_proxy.write(
                            cr, uid, partner_ids, data, context=context)

                except:
                    _logger.error(
                        'Error importing partner commercial [%s], jumped: %s' % (
                            record['CKY_CNT'], 
                            sys.exc_info())
                    )
                            
            _logger.info('All partner commercial is updated!')
        except:
            _logger.error('Error generic import partner commercial: %s' % (
                sys.exc_info(), ))
            return False
        return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
