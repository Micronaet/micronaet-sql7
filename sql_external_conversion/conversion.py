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
from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging


_logger = logging.getLogger(__name__)

class sql_conversion(osv.osv):
    ''' Conversion utility
    '''
    _name = "sql.conversion"
    _description = "Conversione utility"

    # -----------------
    # Utility function:
    # -----------------
    def _get_db_path(self):
        ''' Create path name (standard folder)
        '''
        import os
        # TODO read DB data for first setup: 
        return os.path.join(os.path.expanduser("~"), "openerpdb")
        
    def get_db(self, cr, uid, object_name, context = None):
        ''' Get DB (or create if not exist)
            DB name has a standard syntax for filename
        '''
        import bsddb
        path = self._get_db_path()
        
        # TODO create folder during init event not always
        try:
            os.mkdir(path)
        except:
            pass # if yet exist
        return bsddb.btopen(os.path.join(path, '%s_%s.db' % (cr.dbname, object_name)), 'c') 
        
    def export_object(self, cr, uid, object_name, key_field, context = None):
        ''' Export object for speed up information
        '''
        db = self.get_db(cr, uid, object_name, context = context)

        obj_pool = self.pool.get(object_name)
        
        # all record with the key:
        _logger.info("Export object: %s with key: %s" % (object_name, key_field))
        obj_ids = obj_pool.search(cr, uid, [(key_field, '!=', False)], context = context)
        _logger.info("Records: %s" % (len(obj_ids), ))
        i = 0
        for obj in obj_pool.read(cr, uid, obj_ids, ('id', key_field, ), context = context):
            i += 1
            db[str(obj[key_field])] = "%d" % (obj['id'])
        db.close()
        _logger.info("End export, total records: %s" % (i, ))
        return True
        
    _columns = {
        'name': fields.char('Default path folder', size=64, required = True, help="Default path, write as a tuple list, ex.: ('~','openerpdb')"),
    }    

    _defaults = {
        'name': lambda *x: ('~','openerpdb'),
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
