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
    'name' : 'SQL external conversion',
    'version' : '0.0.1',
    'category' : 'Generic Modules/Utility',
    'description' : """ Utility for save in external Berkley DB conversion for
                        table during importation.
                        ex. Partner account ID >> Openerp ID
                        (quite like a dict but on DB saved on file)
                    """,
    'author' : 'Micronaet s.r.l.',
    'website' : 'http://www.micronaet.it',
    'depends' : [
                 'base',
                ],
    'init_xml' : [], 
    'data' : [
              'security/ir.model.access.csv',
              'conversion_view.xml',
             ],
    'demo_xml' : [],
    'active' : False, 
    'installable' : True, 
}
