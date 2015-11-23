# -*- encoding: utf-8 -*-
################################################################################
#
#    OpenERP module
#    Copyright (C) 2010 Micronaet srl (<http://www.micronaet.it>) 
#    
#    Italian OpenERP Community (<http://www.openerp-italia.com>)
#
################################################################################
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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
import os
import sys
from datetime import datetime, timedelta
from openerp.osv import osv, fields
import logging


_logger = logging.getLogger(__name__)
# TODO remove override set import only BS
# TODO set scheduled action: (0,500,False,0,(0,0),"BS")

#class micronaet_accounting_override(osv.osv):
#    ''' Override some import method for force only BS movements:
#    '''
#    _name = 'micronaet.accounting'
#    _inherit = 'micronaet.accounting'
#     
#    # -------------------
#    # Overrided function:
#    # -------------------
#    def get_mm_line(self, cr, uid, where_document=None, context=None):
#        ''' Return quantity element for product
#            Table: MM_RIGHE 
#            only BS
#        '''        
#        return super(micronaet_accounting_override, self, ).get_mm_line(cr, uid, where_document="BS", context=context)
#        
#    def get_mm_funz_line(self, cr, uid, where_document=None, context=None):
#        ''' Return quantity element for product funz
#            Table: MM_FUNZ_RIGHE
#        '''        
#        return super(micronaet_accounting_override, self, ).get_mm_funz_line(cr, uid, where_document="BS", context=context)
#            
#    def get_mm_header(self, cr, uid, context=None):
#        ''' Return list of OC order (header)
#            Table: MM_TESTATE
#        '''    
#        return super(micronaet_accounting_override, self, ).get_mm_header(cr, uid, where_document="BS", context=context)

class sql_move_line(osv.osv):
    ''' Add scheduled action for import extra document
    '''
    _name = 'sql.move.line'
    _inherit = 'sql.move.line'
    
    # ------------------
    # Scheduled actions:
    # ------------------
    def reimport_not_bs_document(self, cr, uid, where_document, context=None):
        ''' DELETE all document (not BS) and reimport WHERE_DOCUMENT
            @where_document = list of code document to reimport (not BS)
        '''
        if where_document is None:
            return True # Do nothing
        elif type(where_document) not in (list, tuple): # single string
            where_document = [where_document, ]

        _logger.info("Start import extra document only for analysys: %s" % (
            where_document, ))

        # Deleted all document stock move in the list:
        move_ids = self.search(cr, uid, [
            ('type', 'in', where_document),
            ('date', '>=', datetime.now().strftime("%Y-01-01")),
        ], context=context)
        self.unlink(cr, uid, move_ids, context=context)
        
        # Reload documents (call same function passing yet deleted documents):
        self.schedule_etl_move_line_import(cr, uid, 0, 500, False, 0, (0, 0), where_document, context=context)
        
        _logger.info("End import extra document only for analysys")
        return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
