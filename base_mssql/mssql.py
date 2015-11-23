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

class res_company(osv.osv):
    ''' Extra fields for res.company object
    '''
    _name = "res.company"
    _inherit = "res.company"

    # Button event:
    def test_database_connection(self, cr, uid, ids, context=None):
        ''' Test if with the current configuration OpenERP can connect to database
            Test for current name 
            TODO parametrize depend on multi year params
        '''
        cursor = self.mssql_connect(cr, uid, company_id=0, as_dict=True, 
            context=context)
            
        if cursor:
            raise osv.except_osv(
                _("Success Connection test:"), 
                _(
                    "OpenERP succesfully connected with SQL database "
                    "using this parameters! \n Reference: [%s]" % cursor))
        else:
            raise osv.except_osv(
                _("Error Connection test:"), 
                _(
                    "OpenERP cannot connect with SQL database using "
                    "this parameters!"))
        return True

    def table_capital_name(self, cr, uid, company_id=0, context=None):
        ''' Test if table MySQL has capital name
        '''
        try: 
            if not company_id:
                company_id = self.search(cr, uid, [], context=context)[0]            
            company_proxy = self.browse(cr, uid, company_id, context=context)            
            return company_proxy.capital_name
        except:
            return True
                
    def mssql_connect(self, cr, uid, company_id=0, as_dict=True, year=False, context=None):
        ''' Connect to the ids (only one) passed and return the connection 
            for manage DB
            ids = select company_id, if not present take the first company
            year = year value for multi access database (int, like 2014)
        '''
        try: # Every error return no cursor
            current_year = datetime.now().year # current
            if not year:                

                year = current_year
            if not company_id:
                company_id = self.search(cr, uid, [], context=context)[0]
            
            company_proxy = self.browse(cr, uid, company_id, context=context)
            if company_proxy.multi_year and (not company_proxy.no_year_current or current_year != year):
                db_format = company_proxy.multi_year_format                
                if db_format == 'dotfull':                    
                    database = "%s.%s" % (
                        company_proxy.mssql_database, 
                        year)
                elif db_format == 'dotshort':
                    database = "%s.%s" % (
                        company_proxy.mssql_database, 
                        str(year)[-2:])
                elif db_format == 'underfull':
                    database = "%s_%s" % (
                        company_proxy.mssql_database, 
                        year)
                elif db_format == 'undershort':
                    database = "%s_%s" % (
                        company_proxy.mssql_database, 
                        str(year)[-2:])
                elif db_format == 'short':
                    database = "%s%s" % (
                        company_proxy.mssql_database, 
                        str(year)[-2:])
                else: # full format if not present
                    database = "%s%s" % (
                        company_proxy.mssql_database, 
                        year)
            else:
                # if no multi DB or no year current
                database = company_proxy.mssql_database      
            
            if company_proxy.mssql_type == 'mssql':
                try:
                    import pymssql
                except:
                    _logger.error('Error no module pymssql installed!')                            
                    return False
                    
                conn = pymssql.connect(
                    host=r"%s:%s" % (
                        company_proxy.mssql_host, 
                        company_proxy.mssql_port), 
                    user=company_proxy.mssql_username, 
                    password=company_proxy.mssql_password, 
                    database=database,
                    as_dict=as_dict, )

            elif company_proxy.mssql_type=='mysql':
                try:
                     import MySQLdb, MySQLdb.cursors
                except:
                    _logger.error('Error no module MySQLdb installed!')                            
                    return False
                    
                conn = MySQLdb.connect(
                    host=company_proxy.mssql_host,
                    user=company_proxy.mssql_username,
                    passwd=company_proxy.mssql_password,
                    db=database,
                    cursorclass=MySQLdb.cursors.DictCursor,
                    charset='utf8', )
            else:
                return False

            return conn #.cursor()
        except:
            return False

    _columns = {
        'mssql_host': fields.char('MS SQL server host', size=64, 
            required=False, readonly=False, 
            help="Host name, IP address: 10.0.0.2 or hostname: server.example.com"),
        'mssql_port': fields.integer('MS SQL server port', required=False, 
            readonly=False, 
            help="Host name, example: 1433 (form MSSQL), 3306 (for MySQL)"),
        'mssql_username': fields.char('MS SQL server username', size=64, 
            required=False, readonly=False, 
            help="User name, example: sa or root"),
        'mssql_password': fields.char('MS SQL server password', size=64, 
            required=False, readonly=False, password=True),
        'mssql_database': fields.char('MS SQL server database name', size=64, 
            required=False, readonly=False),
        'capital_name': fields.boolean('MS SQL capital name', 
            help='If true the table has all the capital letter name'),
        'multi_year': fields.boolean('Multi year',
            help='If checked the database name is parametrized with year'
                'like: DB name = "example", real DBs like: "example2014, "'
                'example2013, example2012 (depend on format)'),
        'multi_year_format': fields.selection([
            ('full', 'DatabaseYear(4)'),
            ('short', 'DatabaseYear(2)'),
            ('dotfull', 'Database.Year(4)'),
            ('dotshort', 'Database.Year(2)'),
            ('underfull', 'Database_Year(4)'),
            ('undershort', 'Database_Year(2)'),
        ], 'Type', select=True,),                
        'bottom_year': fields.integer('Bottom year', 
            help="Year value for start database SQL year in multi DB"
            "used also for analysis setup",),
        'mssql_type': fields.selection([
            ('mysql', 'MySQL'),
            ('mssql', 'MS SQL Server'),
        ], 'Type', select=True,),
        'no_year_current': fields.boolean('No year current', 
            help="If checked current year use db name without year extension"),
        # add fields.many2many for recipient for notification
    }    
    _defaults = {
        'mssql_port': lambda *a: 3306,
        'mssql_type': lambda *a: 'mysql',
        'capital_name': lambda *a: True,
        'multi_year': lambda *a: False,
        'multi_year_format': lambda *a: 'full',
        'bottom_year': lambda *x: False,
        'no_year_current': lambda *a: False,
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
