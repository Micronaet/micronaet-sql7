# -*- encoding: utf-8 -*-
##############################################################################
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

{
    'name': 'SQL Accounting header analysis',
    'version': '0.0.1',
    'category': 'Generic Modules/Customization',
    'description': """
        Analysis for movement (DBMS may be MSSQL server or MySQL)
        Header movement
        """,
    'author': 'Micronaet s.r.l.',
    'website': 'http://www.micronaet.it',
    'depends': [
        'base',
        'product',
        'base_mssql',
        'base_mssql_accounting',
        'sql_product',
        'sql_partner',
        'l10n_it_sale',
        'sql_accounting_analysis',
       ],
    'init_xml': [], 
    'data': [
        'security/ir.model.access.csv',
        'scheduler.xml',
        'header_views.xml',
    ],
    'demo_xml': [],
    'active': False, 
    'installable': True, 
}
