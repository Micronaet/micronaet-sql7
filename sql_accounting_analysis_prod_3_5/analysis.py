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
import os
import sys
from datetime import datetime, timedelta
from openerp.osv import osv, fields
import logging


_logger = logging.getLogger(__name__)

class etl_move_line(osv.osv):
    ''' Objetc populated with accounting movement
    '''    
    _name = 'sql.move.line'
    _inherit = 'sql.move.line'

    def _function_get_code_short(self, cr, uid, ids, fields=None, args=None, context=None):
        ''' Trunk code to 3 and 5 char
        '''
        res = {}
        for move in self.browse(cr, uid, ids, context=context):
            res[move.id] = {}            
            res[move.id]['code3'] = (move.product_id.default_code or "")[:3]
            res[move.id]['code5'] = (move.product_id.default_code or "")[:5]
            current_year = int(move.date[2:4])
            if move.date[5:7] >= "09":
                res[move.id]['season'] = "%02d-%02d" % (current_year, current_year + 1)
            else: #< "09"    
                res[move.id]['season'] = "%02d-%02d" % (current_year -1, current_year)                
        return res
        
    _columns = {
        'code3': fields.function(_function_get_code_short, method=True,
            type='char', size=3, string='Code 3', store=True, multi=True),
        'code5': fields.function(_function_get_code_short, method=True,
            type='char', size=5, string='Code 5', store=True, multi=True),
        'season': fields.function(_function_get_code_short, method=True,
            type='char', size=10, string='Season', store=True, multi=True),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
