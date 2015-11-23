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
import sys
import os
from openerp.osv import osv, fields
import logging


_logger = logging.getLogger(__name__)

class product_product(osv.osv):
    ''' Extend product.product
    '''    
    _name = 'product.product'
    _inherit = 'product.product'
    
    # Scheduled action: ########################################################
    def schedule_sql_product_price_import(self, cr, uid, pricelist=1, verbose_count=100, context=None):
        ''' Update product price from external DB
        '''
        _logger.info('Start updating product price')
        product_proxy = self.pool.get('product.product')
        try:
            cursor = self.pool.get('micronaet.accounting').get_product_price(cr, uid, context=context) 
            if not cursor:
                _logger.error("Unable to connect no importation of price for product!")
                return False

            i = 0
            for record in cursor:
                try:
                    i += 1
                    if i % verbose_count == 0:
                        _logger.info('%s price imported!' % (i, ))
                    product_id = product_proxy.search(cr, uid, [('default_code', '=', record['CKY_ART'])])
                    if product_id: # update
                        product_proxy.write(cr, uid, product_id, {
                           'list_price': record['NPZ_LIS_%s' % (pricelist)], 
                        }, context = context)
                        product_id = product_id[0]
                except:
                    _logger.error('Error update product price [%s], jumped: %s' % (record['CKY_ART'], sys.exc_info(), ))
                        
            _logger.info('All product price is updated!')
        except:
            _logger.error('Error generic import product price: %s' % (sys.exc_info(), ))
            return False
        return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
