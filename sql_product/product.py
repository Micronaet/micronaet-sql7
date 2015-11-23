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

class product_product(osv.osv):
    ''' Extend product.product
    '''    
    _name = 'product.product'
    _inherit = 'product.product'
    
    _columns = {
        'sql_import': fields.boolean('SQL import', required=False),
        'statistic_category': fields.char('Statistic category', size=10, required=False, readonly=False),
    }
    
    _defaults = {
        'sql_import': lambda *a: False,
        'statistic_category': lambda *x: False,
    }

    def fast_product_create(self, cr, uid, code, context=None):
        ''' Create a minimal product only from code
        '''
        return self.create(cr, uid, {
            'name': _("Prod. %s*") % code,
            'default_code': code,
            'sql_import': True,
            'active': True,
            }, context=context)

    def get_product_from_sql_code(self, cr, uid, code, context = None):
        ''' Return product_id read from the import code passed
            (all product also pre-deleted
        '''
        product_ids = self.search(cr, uid, [('default_code', '=', code),])

        if product_ids:
            return product_ids[0]
        return False

    def get_is_to_import_product(self, cr, uid, item_id, context = None):
        ''' Return if the product is to import (MM) from ID
        '''
        product_id = self.search(cr, uid, [('id', '=', item_id),])
        if product_id:
            product_browse = self.search(cr, uid, product_id, context = context)
            return not product_browse[0].not_analysis

        return True #False # Jump line with product not found

    # -------------------------------------------------------------------------
    #                                  Scheduled action
    # -------------------------------------------------------------------------
    def schedule_sql_product_import(self, cr, uid, verbose_log_count=100, write_date_from=False, write_date_to=False, create_date_from=False, create_date_to=False, context=None):
        ''' Import product from external DB
        '''
        product_proxy = self.pool.get('product.product')
        accounting_pool = self.pool.get('micronaet.accounting')
        try:
            cursor = accounting_pool.get_product( 
                cr, uid, active = False, write_date_from=write_date_from,
                write_date_to=write_date_to, create_date_from=create_date_from,
                create_date_to=create_date_to, context=context) 
            if not cursor:
                _logger.error("Unable to connect no importation of package list for product!")
                return False

            i = 0
            for record in cursor:
                try:
                    i += 1
                    if verbose_log_count and i % verbose_log_count == 0:
                        _logger.info('Import %s: record import/update!' % i)                             

                    data = {
                        # TODO IFL_ART_DBP o DBV for supply_method='produce'
                        'name': record['CDS_ART'],
                        'default_code': record['CKY_ART'],
                        'sql_import': True,
                        'active': True,
                        'statistic_category': "%s%s" % (
                            record['CKY_CAT_STAT_ART'] or '', 
                            "%02d" % int(
                                record['NKY_CAT_STAT_ART'] or '0') if record['CKY_CAT_STAT_ART'] else '',
                        ),
                    }
                    if accounting_pool.is_active(record):
                        data['state'] = 'sellable'
                    else:
                        data['state'] = 'obsolete'
                        
                    product_ids = product_proxy.search(cr, uid, [
                        ('default_code', '=', record['CKY_ART'])])
                    if product_ids:
                        product_id = product_ids[0]
                        product_proxy.write(cr, uid, product_id, data, 
                            context=context)
                    else:
                        product_id = product_proxy.create(cr, uid, data, 
                            context=context)

                except:
                    _logger.error('Error import product [%s], jumped: %s' % (
                        record['CDS_ART'], sys.exc_info(), ))
                        
            _logger.info('All product is updated!')
        except:
            _logger.error('Error generic import product: %s' % (sys.exc_info(), ))
            return False
        return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
