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

class res_company(osv.osv):
    ''' Add extra info to Company for setup wizard
    '''
    _name = 'res.company'
    _inherit = 'res.company'
    
    # -----------------
    # Utility function:
    # -----------------
    def set_inventory_date(self, cr, uid, inventory_date, 
	company_id=False, context=None):
        ''' Change inventory date to company passed, else the first
        '''
        if not company_id:
            company_id = self.search(cr, uid, [], context=context)[0]
        self.write(cr, uid, company_id, {
            'default_inventory_date': inventory_date, }, context=context)
        return True    

    def get_inventory_date(self, cr, uid, company_id=False, context=None):
        ''' Return inventory date to company passed, else the first
        '''
        if not company_id:
            company_id = self.search(cr, uid, [], context=context)[0]
        company_proxy = self.browse(
            cr, uid, company_id, context=context)
        return company_proxy.default_inventory_date

    _columns = {
        'default_inventory_date': fields.date('Inventory date',
            help="Default inventory date (set up by wizard)"),
        }

class product_product(osv.osv):
    ''' Add extra info to Company for setup wizard
    '''
    _name = 'product.product'
    _inherit = 'product.product'
    
    # -------------------
    # On Change function:
    # -------------------
    def onchange_inventory_date(self, cr, uid, ids, product_qty, context=None):
        ''' Set inventory date to setup date (as default)
        '''
        res = {}
        if not product_qty:
            return res
        inventory_date = self.pool.get('res.company').get_inventory_date(
            cr, uid, context=context)
        if inventory_date:
            res['value'] = {
                'inventory_date': inventory_date, # set default date 
                'inventory_updated': False,       # remove updated if present
                }
        return res
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
