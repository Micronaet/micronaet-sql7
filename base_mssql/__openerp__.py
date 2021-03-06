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
    'name' : 'Base MS SQL',
    'version' : '0.0.1',
    'category' : 'Generic Modules/Customization',
    'description' : """MS SQL parameter setup for access to DB 
                       Used ad a base for module that need to link to company
                       element a MS SQL profile to access DB
                       
                       This module require installation of pymssql module 
                       downlodable from: 
                       http://code.google.com/p/pymssql/
                    """,
    'author' : 'Micronaet s.r.l.',
    'website' : 'http://www.micronaet.it',
    'depends' : ['base',],
    'init_xml' : [], 
    'update_xml' : [
        'security/SQL_group.xml',
        'mxsql_view.xml',
    ],
    'demo_xml' : [],
    'active' : False, 
    'installable' : True, 
}
