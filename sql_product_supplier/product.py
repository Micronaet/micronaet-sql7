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
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, \
    DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class product_product(osv.osv):
    ''' Extend accounting query
    '''    
    _inherit = 'micronaet.accounting'
    
    def get_product_supplier(self, cr, uid, context=None):
        ''' Return query for first supplier
        '''
        table = 'ar_anagrafiche' 
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = table.upper()    

        cursor = self.connect(cr, uid, context=context)
        try: 
            cursor.execute('''
                SELECT CKY_ART, CKY_CNT_FOR_AB FROM %s 
                WHERE CKY_CNT_FOR_AB is not null;''' % table)
            return cursor
        except: 
            return False

class product_product(osv.osv):
    ''' Extend product.product
    '''    
    _inherit = 'product.product'
    
    _columns = {
        'first_supplier_id': fields.many2one('res.partner', 'First supplier'),
        }

    # -------------------------------------------------------------------------
    #                                  Override
    # -------------------------------------------------------------------------
    def schedule_sql_product_import(self, cr, uid, **args):
        ''' Launch import supplier after product
            verbose_log_count=100, write_date_from=False, write_date_to=False, 
            create_date_from=False, create_date_to=False, context=None):
        '''
        import pdb; pdb.set_trace()
        res = super(product_product, self).schedule_sql_product_import(
            cr, uid, **args)

        _logger.info('Start update product supplier!')
        
        # Pool used:
        accounting_pool = self.pool.get('micronaet.accounting')
        product_proxy = self.pool.get('product.product')
        partner_pool = self.pool.get('res.partner')

        cursor = accounting_pool.get_product_supplier(cr, uid, context=context)
        if not cursor:
            _logger.error(
                'Unable to connect no importation product supplier!')
            return False

        i = 0
        for record in cursor:
            try:
                i += 1
                if verbose_log_count and i % verbose_log_count == 0:
                    _logger.info('Import %s: record import/update!' % i)                             

                # Read fields:
                default_code = record['CKY_ART']
                supplier_code = record['CKY_CNT_FOR_AB']
                
                # Search product (all product imported before):
                product_ids = product_pool.search(cr, uid, [
                    ('default_code', '=', default_code),
                    ], context=context)
                if not product_ids:
                    _logger.error('Product not found: %s' % default_code)
                    
                # Search supplier:
                partner_ids = partner_pool.search(cr, uid, [
                    ('sql_supplier_code', '=', supplier_code),
                    ], context=context)
                if not partner_ids:
                    _logger.error('Supplier not found: %s' % supplier_code)
                
                product_pool.write(cr, uid, product_ids, {
                    'first_supplier_id': partner_ids[0],
                    ), context=context)

            except:
                _logger.error('Error update product supplier: %s [%s]' % (
                    record, sys.exc_info(), ))
                    
        _logger.info('All product supplier updated!')
        return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
