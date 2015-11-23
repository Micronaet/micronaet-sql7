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

class product_categ(osv.osv):
    ''' Extend product.category
    '''    
    _name = 'product.category'
    _inherit = 'product.category'
    
    # Scheduled action: ########################################################
    def schedule_update_product_category(self, cr, uid, context=None):
        ''' Update product category from external DB
        '''
        _logger.info('Start updating product category')

        # Read category range:
        category_ids = self.search(cr, uid, [
            ('from_code', '!=', False),
            ('to_code', '!=', False),
        ], context = context)
        category_proxy = self.browse(cr, uid, category_ids, context=context)

        # Update category product in range:
        product_pool = self.pool.get('product.product')
        for category in category_proxy:
            try:
                field_name = category.auto_category_type
                product_ids = product_pool.search(cr, uid, [
                    (field_name, '>=', category.from_code),
                    (field_name, '<', category.to_code),
                ], context=context)
                if product_ids:
                    product_proxy = product_pool.write(cr, uid, product_ids, {
                        'categ_id': category.id
                    }, context=context)
                    _logger.info('Update category: %s [Tot.: %s]' % (
                        category.name, 
                        len(product_ids),
                    ))

            except:
                _logger.error('Error update product category (%s) products! [%s]' % (
                    category.name, 
                    sys.exc_info(),
                ))
        _logger.info('All product category is updated!')
        return True

    _columns = {
        'from_code':fields.char('From code (>=)', size=30, required=False, readonly=False),
        'to_code':fields.char('To code (<)', size=30, required=False, readonly=False),
        'auto_category_type': fields.selection([
            ('default_code', 'Default code'),
            ('statistic_category', 'Statistic category'),
        ], 'Auto category type', required=False),
    }        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
