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
    ''' Extra fields for setup the module
    '''
    _inherit = 'res.company'
    
    def get_from_to_dict(self, cr, uid, context = None):
        ''' Return a company proxy for get from to clause
        '''        
        company_id = self.search(cr, uid, [], context = context)
        if not company_id:
            return False
        return self.browse(cr, uid, company_id, context = context)[0]
        
    _columns = {
        # Supplier:  
        'sql_supplier_from_code': fields.char(
            'SQL supplier from code >=', 
            size=10, required=False, readonly=False),
        'sql_supplier_to_code': fields.char(
            'SQL supplier from code <', 
            size=10, required=False, readonly=False),
        # Customer:   
        'sql_customer_from_code': fields.char(
            'SQL customer from code >=', 
            size=10, required=False, readonly=False),
        'sql_customer_to_code': fields.char(
            'SQL customer from code <', 
            size=10, required=False, readonly=False),
        # Destination:
        'sql_destination_from_code': fields.char(
            'SQL destination from code >=',
            size=10, required=False, readonly=False),
        'sql_destination_to_code': fields.char(
            'SQL destination from code <', 
            size=10, required=False, readonly=False),
            
        # TODO    
        # Agent:
        'sql_agent_from_code': fields.char(
            'SQL agent from code >=',
            size=10, required=False, readonly=False),
        'sql_agent_to_code': fields.char(
            'SQL agent from code <', 
            size=10, required=False, readonly=False),
        # Employe    
        'sql_employee_from_code': fields.char(
            'SQL employee from code >=',
            size=10, required=False, readonly=False),
        'sql_employee_to_code': fields.char(
            'SQL employee from code <', 
            size=10, required=False, readonly=False),
        # TODO Bank account???    
        }

class res_partner(osv.osv):
    ''' Extend res.partner
    '''    
    _inherit = 'res.partner'
    
    # -------------------------------------------------------------------------
    #                                 Utility
    # -------------------------------------------------------------------------
    def get_partner_from_sql_code(self, cr, uid, code, context=None):
        ''' Return partner_id read from the import code passed
            (search in customer, supplier, destiantion)
        '''
        partner_id = self.search(cr, uid, ['|', '|',
            ('sql_supplier_code', '=', code),
            ('sql_customer_code','=', code),
            ('sql_destination_code', '=', code),
            #('sql_agent_code', '=', code),
            #('sql_employee_code', '=', code),
            ])
            
        if partner_id:
            return partner_id[0]
        return False

    # -------------------------------------------------------------------------
    #                 Placeholder function (will be overrided)
    # -------------------------------------------------------------------------
    def get_swap_parent(self, cr, uid, context=None):
        ''' Virtual function that will be overridef from module that manage
            parent_id swap partner (not implemented here)
        '''
        return {}

    # -------------------------------------------------------------------------
    #                             Scheduled action
    # -------------------------------------------------------------------------
    def schedule_sql_partner_import(self, cr, uid, verbose_log_count=100, 
        capital=True, write_date_from=False, write_date_to=False, 
        create_date_from=False, create_date_to=False, sync_vat=False,
        address_link=False, only_block=False, context=None):
        ''' Import partner from external DB
            verbose_log_count: number of record for verbose log (0 = nothing)
            capital: if table has capital letters (usually with mysql in win)
            write_date_from: for smart update (search from date update record)
            write_date_to: for smart update (search to date update record)
            create_date_from: for smart update (search from date create record)
            create_date_to: for smart update (search to date create record)
            sync_vat: Supplier update partner customer with same VAT
            address_link: Link to parent partner as an address the destination
            only_block: update only passed block name:
                (supplier, customer destination... TODO agent, employee)
            context: context of procedure
            
        '''            
        # Load country for get ID from code
        countries = {}
        country_pool = self.pool.get('res.country')
        country_ids = country_pool.search(cr, uid, [], context=context)
        country_proxy = country_pool.browse(
            cr, uid, country_ids, context=context)
        for item in country_proxy:
            countries[item.code] = item.id

        try:
            _logger.info('Start import SQL: customer, supplier, destination')
            company_pool = self.pool.get('res.company')
            company_proxy = company_pool.get_from_to_dict(
                cr, uid, context=context)
            if not company_proxy:
                _logger.error('Company parameters not setted up!')

            import_loop = [
                (1,                                     # order
                'sql_customer_code',                    # key field
                company_proxy.sql_customer_from_code,   # form_code
                company_proxy.sql_customer_to_code,     # to_code
                'customer'),                            # type
                
                (2,
                'sql_supplier_code', 
                company_proxy.sql_supplier_from_code, 
                company_proxy.sql_supplier_to_code, 
                'supplier'),
                
                (3,
                'sql_destination_code', 
                company_proxy.sql_destination_from_code, 
                company_proxy.sql_destination_to_code,
                'destination'),

                # TODO (vedere come comportarsi durante la creazione (simli a fornitori, agganciarli a fiscalcode=
                #(4,
                #'sql_agent_code', 
                #company_proxy.sql_agent_from_code, 
                #company_proxy.sql_agent_to_code,
                #'agent'),

                #(5,
                #'sql_employee_code', 
                #company_proxy.sql_employee_from_code, 
                #company_proxy.sql_employee_to_code,
                #'employee'),
                ]
            parents = {}              # Client / Supplier converter
            destination_parents = {}  # Partner code for Destination
            swap_parent = self.get_swap_parent(cr, uid, context=context)
            
            # Add parent for destination in required:
            if address_link:
                _logger.info('Read parent for destinations')
                cursor = self.pool.get(
                    'micronaet.accounting').get_parent_partner(
                        cr, uid, context=context)
                if not cursor:
                    _logger.error(
                        "Unable to connect to parent for destination!")
                else:
                    for record in cursor: 
                        # Swapped:    
                        destination_parents[ 
                            record['CKY_CNT']] = swap_parent.get(
                                record['CKY_CNT_CLI_FATT'], # search invoice to
                                record['CKY_CNT_CLI_FATT']) # default invoice
                                

            for order, key_field, from_code, to_code, block in import_loop:
                if only_block and only_block != block:                    
                    _logger.warning("Jump block: %s!" % block)
                    continue
                cursor = self.pool.get('micronaet.accounting').get_partner(
                    cr, uid, from_code=from_code, to_code=to_code, 
                    write_date_from=write_date_from, 
                    write_date_to=write_date_to, 
                    create_date_from=create_date_from, 
                    create_date_to=create_date_to, context=context) 
                if not cursor:
                    _logger.error("Unable to connect, no partner!")
                    continue # next block

                _logger.info('Start import %s from: %s to: %s' % (
                    block, from_code, to_code))                          
                i = 0
                for record in cursor:
                    i += 1
                    if verbose_log_count and i % verbose_log_count == 0:
                        _logger.info(
                            'Import %s: %s record imported / updated!' % (
                                block, i, ))      
                    try:
                        data = {
                            'name': record['CDS_CNT'],
                            #'sql_customer_code': record['CKY_CNT'],
                            'sql_import': True,
                            'is_company': True,
                            'street': record['CDS_INDIR'] or False,
                            'city': record['CDS_LOC'] or False,
                            'zip': record['CDS_CAP'] or False,
                            'phone': record['CDS_TEL_TELEX'] or False,
                            'email': record['CDS_INET'] or False,
                            'fax': record['CDS_FAX'] or False,
                            #'mobile': record['CDS_INDIR'] or False,
                            'website': record['CDS_URL_INET'] or False,
                            'vat': record['CSG_PIVA'] or False,
                            key_field: record['CKY_CNT'], # key code
                            'country_id': countries.get(
                                record['CKY_PAESE'], False),
                            }
                        
                        if block == 'customer': 
                            data['type'] = 'default'
                            data['customer'] = True
                            data['ref'] = record['CKY_CNT']

                        if block == 'supplier': 
                            data['type'] = 'default'
                            data['supplier'] = True

                        if address_link and block == 'destination': 
                            data['type'] = 'delivery' 
                            data['is_address'] = True

                            parent_code = destination_parents.get(
                                record['CKY_CNT'], False)
                            if parent_code: # Convert value with dict
                                data['parent_id'] = parents.get(
                                    parent_code, False)

                                # if not in convert dict try to search
                                if not data['parent_id']:
                                    parent_ids = self.search(cr, uid, ['|',
                                        ('sql_customer_code', '=', parent_code),
                                        ('sql_supplier_code', '=', parent_code),
                                        ], context=context)
                                    if parent_ids:
                                        data['parent_id'] = parent_ids[0]

                        partner_ids = self.search(cr, uid, [
                            (key_field, '=', record['CKY_CNT'])])

                        # Search per vat (only for customer and supplier)
                        if sync_vat and not partner_ids and block != 'destination': 
                            partner_ids = self.search(cr, uid, [
                                ('vat', '=', record['CSG_PIVA'])])

                        # Update / Create
                        if partner_ids:
                            try:
                                partner_id = partner_ids[0]
                                self.write(cr, uid, partner_id, data, 
                                    context = context)
                            except:
                                data['vat'] = False
                                try: # Remove vat for vat check problems:
                                    self.write(cr, uid, partner_id, data, 
                                        context = context)
                                except:    
                                    _logger.error(
                                        '%s. Error updating partner [%s]: %s' % (
                                             i, partner_id, sys.exc_info()))
                                    continue
                        else:
                            try:
                                partner_id = self.create(
                                    cr, uid, data, context=context)
                            except:
                                data['vat'] = False
                                try: # Remove vat for vat check problems:
                                    partner_id = self.create(cr, uid, data, 
                                        context=context)
                                except:    
                                    _logger.error(
                                        '%s. Error creating partner [%s]: %s' % (
                                            i, partner_id, sys.exc_info()))
                                    continue
        
                        if address_link and block != 'destination':
                            # Save partner for destination search
                            parents[record['CKY_CNT']] = partner_id

                    except:
                        _logger.error('Error importing partner [%s], jumped: %s' % (
                            record['CDS_CNT'], sys.exc_info()))
                                            
                _logger.info('All %s is updated!' % block)
        except:
            _logger.error('Error generic import partner: %s' % (
                sys.exc_info(), ))
            return False
        return True

    # -------------------------------------------------------------------------
    #                                 Columns
    # -------------------------------------------------------------------------
    _columns = {
        'sql_import': fields.boolean('SQL import', required=False),
        'sql_supplier_code':fields.char('SQL supplier code', size=10, 
            required=False, readonly=False),
        'sql_customer_code':fields.char('SQL customer code', size=10, 
            required=False, readonly=False),
        'sql_destination_code':fields.char('SQL destination code', size=10, 
            required=False, readonly=False),
        # TODO    
        #'sql_agent_code':fields.char('SQL agent code', size=10, 
        #    required=False, readonly=False),
        #'sql_employee_code':fields.char('SQL employee code', size=10, 
        #    required=False, readonly=False),
        }
    
    _defaults = {
        'sql_import': lambda *a: False,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
