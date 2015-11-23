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

class res_company_inventory_date_wizard(osv.osv_memory):
    ''' Object that manage the request of demo on the web
    '''
    _name = 'res.company.inventory.date.wizard'
    
    # Button event:
    def set_date(self, cr, uid, ids, context=None):
        ''' Change date in company parameters '''
        wizard_proxy = self.browse(cr, uid, ids, context=context)[0]
        if wizard_proxy.inventory_date:        
            self.pool.get("res.company").set_inventory_date(
                cr, uid, wizard_proxy.inventory_date, 
                context=context)
        return True

    def set_today_date(self, cr, uid, ids, context=None):
        ''' Change date in company parameters '''
        self.pool.get("res.company").set_inventory_date(
            cr, uid, datetime.now().strftime(
                DEFAULT_SERVER_DATE_FORMAT), 
            context=context)
        return True


    # Fields function:
    def _get_inventory_date(self, cr, uid, context=None):
        ''' Read company date else today:
        '''
        return self.pool.get("res.company").get_inventory_date(
                cr, uid, context=context) or datetime.now().strftime(
                DEFAULT_SERVER_DATE_FORMAT)         
        return
    _columns = {
        'inventory_date': fields.date('Date'),
        }

    _defaults = {
        'inventory_date': lambda s, cr, uid, ctx: s._get_inventory_date(
            cr, uid, ctx),
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
