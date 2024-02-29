#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import os
import pdb
import sys
import erppeek
import ConfigParser

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
cfg_file = os.path.expanduser('../openerp.cfg')

config = ConfigParser.ConfigParser()
config.read([cfg_file])
dbname = config.get('dbaccess', 'dbname')
user = config.get('dbaccess', 'user')
pwd = config.get('dbaccess', 'pwd')
server = config.get('dbaccess', 'server')
port = config.get('dbaccess', 'port')   # verify if it's necessary: getint

# -----------------------------------------------------------------------------
# Connect to ODOO:
# -----------------------------------------------------------------------------
odoo = erppeek.Client(
    'http://%s:%s' % (server, port),
    db=dbname,
    user=user,
    password=pwd,
    )

# Pool used:
partner_pool = odoo.model('res.partner')
company_pool = odoo.model('res.company')
country_pool = odoo.model('res.country')
fiscal_pool = odoo.model('account.fiscal.position')
accounting_pool = odoo.model('micronaet.accounting')

# -----------------------------------------------------------------------------
#                             Parameters
# -----------------------------------------------------------------------------
# Procedure:
verbose_log_count = 200
capital = True
write_date_from = False
write_date_to = False
create_date_from = False
create_date_to = False
sync_vat = True
address_link = True
only_block = False
dest_merged = False
set_lang = False

# OpenERP:
company_ids = company_pool.search([])
if not company_ids:
    print('Company parameters not set up!')
    sys.exit()
company_proxy = company_pool.browse(company_ids[0])

# -----------------------------------------------------------------------------
#                          MASTER LOOP:
# -----------------------------------------------------------------------------
# order, key field, from code, to code, type
import_loop = [
    (1,
     'sql_customer_code',
     company_proxy.sql_customer_from_code,
     company_proxy.sql_customer_to_code,
     'customer'),

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

    # todo (vedere come comportarsi durante la creazione
    # (simili a fornitori, agganciarli a fiscalcode)
    # (4,
    # 'sql_agent_code',
    # company_proxy.sql_agent_from_code,
    # company_proxy.sql_agent_to_code,
    # 'agent'),

    # (5,
    # 'sql_employee_code',
    # company_proxy.sql_employee_from_code,
    # company_proxy.sql_employee_to_code,
    # 'employee'),
    ]

# =============================================================================
#                             FOREIGN KEYS:
# =============================================================================
# Load fiscal position type CEI:
# -----------------------------------------------------------------------------
fiscal_position_db = {}
fiscal_ids = fiscal_pool.search([])
for fiscal in fiscal_pool.browse(fiscal_ids):
    try:
        cei_ref = fiscal.cei_ref
    except:
        print(
            'No CEI Management in fiscal position. '
            'No fiscal position loaded!')
        break
    fiscal_position_db[cei_ref] = fiscal.id

# -----------------------------------------------------------------------------
# Load Country:
# -----------------------------------------------------------------------------
countries = {}
country_ids = country_pool.search([])
country_proxy = country_pool.browse(country_ids)
for item in country_proxy:
    countries[item.code] = item.id

pdb.set_trace()
try:
    print('Start import SQL: customer, supplier, destination')
    parents = {}              # Client / Supplier converter
    destination_parents = {}  # Partner code for Destination
    swap_parent = partner_pool.get_swap_parent()

    # Add parent for destination in required:
    if address_link:
        print('Read parent for destinations')
        cursor = accounting_pool.get_parent_partner()
        if not cursor:
            print('Unable to connect to parent for destination!')
        else:
            for record in cursor:
                # Swapped:
                destination_parents[
                    record['CKY_CNT']] = swap_parent.get(
                        record['CKY_CNT_CLI_FATT'],  # search inv. to
                        record['CKY_CNT_CLI_FATT'])  # default invoice

    for order, key_field, from_code, to_code, block in import_loop:
        if only_block and only_block != block:
            print('Jump block: %s!' % block)
            continue
        cursor = accounting_pool.get_partner(
            from_code=from_code, to_code=to_code,
            write_date_from=write_date_from,
            write_date_to=write_date_to,
            create_date_from=create_date_from,
            create_date_to=create_date_to)
        if not cursor:
            print('Unable to connect, no %s block!' % block)
            continue  # next block

        print('Start import %s from: %s to: %s' % (block, from_code, to_code))
        i = 0
        for record in cursor:
            i += 1
            if verbose_log_count and not i % verbose_log_count:
                print(
                    'Import %s: %s record imported / updated!' % (
                        block, i, ))
            try:
                # if record['CKY_CNT'] in ('06.03132', '06.03173'):
                #    pdb.set_trace()
                data = {
                    'name': record['CDS_CNT'],
                    # 'sql_customer_code': record['CKY_CNT'],
                    'sql_import': True,
                    'is_company': True,
                    'street': record['CDS_INDIR'] or False,
                    'city': record['CDS_LOC'] or False,
                    'zip': record['CDS_CAP'] or False,
                    'phone': record['CDS_TEL_TELEX'] or False,
                    'email': record['CDS_INET'] or False,
                    'fax': record['CDS_FAX'] or False,
                    # 'mobile': record['CDS_INDIR'] or False,
                    'website': record['CDS_URL_INET'] or False,
                    'vat': record['CSG_PIVA'] or False,
                    key_field: record['CKY_CNT'],  # key code
                    'country_id': countries.get(
                        record['CKY_PAESE'], False),
                    }

                if block == 'customer':
                    data['type'] = 'default'
                    data['customer'] = True
                    data['ref'] = record['CKY_CNT']
                    if fiscal_position_db:
                        data['property_account_position'] = \
                            fiscal_position_db.get(record['IST_NAZ'])

                if block == 'supplier':
                    data['type'] = 'default'
                    data['supplier'] = True
                    if fiscal_position_db:
                        data['property_account_position'] = \
                            fiscal_position_db.get(record['IST_NAZ'])

                if address_link and block == 'destination':
                    data['type'] = 'delivery'
                    data['is_address'] = True
                    # No fiscal position

                    # Swap parent code:
                    parent_code = destination_parents.get(record['CKY_CNT'])
                    if parent_code:  # Convert value with dict
                        # Cache search:
                        data['parent_id'] = parents.get(
                            parent_code, False)

                        # if not in convert dict try to search
                        if not data['parent_id']:
                            # Normal search:
                            parent_ids = partner_pool.search([
                                '|',
                                ('sql_customer_code', '=', parent_code),
                                ('sql_supplier_code', '=', parent_code),
                                ])
                            if parent_ids:
                                data['parent_id'] = parent_ids[0]

                partner_ids = partner_pool.search([
                    (key_field, '=', record['CKY_CNT'])])

                # Search per vat (only for customer and supplier)
                if sync_vat and not partner_ids and block != \
                        'destination':
                    partner_ids = partner_pool.search([
                        ('vat', '=', record['CSG_PIVA'])])

                # Update / Create
                if partner_ids:
                    partner_id = partner_ids[0]
                    try:
                        partner_pool.write([partner_id], data)
                    except:
                        data['vat'] = False
                        try:  # Remove vat for vat check problems:
                            partner_pool.write([partner_id], data)
                        except:
                            print(
                                '%s. Error updating partner [%s]: '
                                '%s' % (
                                     i, record, sys.exc_info()))
                            continue
                else:
                    try:
                        partner_id = partner_pool.create(data)
                    except:
                        data['vat'] = False
                        try:  # Remove vat for vat check problems:
                            partner_id = partner_pool.create(data)
                        except:
                            print(
                                '%s. Error creating partner [%s]: '
                                '%s' % (
                                    i, record, sys.exc_info()))
                            continue

                if address_link and block != 'destination':
                    # Save partner for destination search
                    parents[record['CKY_CNT']] = partner_id
            except:
                print(
                    'Error importing partner [%s], jumped: %s' % (
                        record['CDS_CNT'], sys.exc_info()))
                continue
        print('>>>> All record in block %s is updated!' % block)
except:
    print(
        'Error generic import partner: %s' % (sys.exc_info(), ))
