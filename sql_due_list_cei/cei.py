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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    Adding code for generate email and send from template thanks to OpenCode
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

class sql_payment_duelist(osv.osv):
    ''' Payment stage for sending e-mail
    '''
    _name = 'sql.payment.duelist'
    _inherit = 'sql.payment.duelist'

    _columns = {
        'type_cei': fields.related('partner_id', 'type_cei', type='selection', 
        string='CEI', selection=[
           ('i', 'Italy'),
           ('c', 'CEE'),
           ('e', 'Extra CEE'),               
           ]),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
