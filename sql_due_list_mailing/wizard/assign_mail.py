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
import openerp.netsvc
import logging
from openerp.osv import osv, orm, fields
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class duelist_assign_mail(osv.osv_memory):
    ''' Assign mail to customer for duelist
    '''
    _name = "res.partner.assign.duelist.mail"
    _description = "Assign mail wizard"

    # Wizard button:
    def action_assign_mail(self, cr, uid, ids, context=None):
        ''' Assign mail to partner
        '''
        if context is None:
            context = {}        
        
        payment_pool = self.pool.get("sql.payment.duelist")
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]
        emails = wiz_proxy.email      
        if wiz_proxy.email:                
            emails = emails.replace(" ", "")  # Remove blank 
            emails = emails.replace(";", ",") # Replace semicolon with comma
            emails = emails.replace(",", ", ") # Replace for better layout
        
            for email in emails.split(", "): # check every email
                if not payment_pool.validate_mail(email):
                    raise osv.except_osv(
                        _('Email check'), 
                        _("'%s' seems not to be a valid email address!") % emails)
        try:
            payment_proxy = payment_pool.browse(
                cr, uid, context.get('active_id', False), context=context)
                
            return self.pool.get('res.partner').write(cr, uid, 
                payment_proxy.partner_id.id, {
                    'duelist_mail': emails, }, context=context)
        except:
            return False
               
    def get_email_default(self, cr, uid, context=None):
        ''' Search in partner for payment current email
        '''
        try:
            duelist_pool = self.pool.get('sql.payment.duelist')
            duelist_proxy = duelist_pool.browse(
                cr, uid, context.get('active_id', False), context=context)
            return duelist_proxy.partner_id.duelist_mail or ""
        except:            
            return ""
        
    _columns = {
        'email': fields.char('Duelist Email', size=400),
        }           
    _defaults = {
        'email': lambda s, cr, uid, ctx: s.get_email_default(cr, uid, ctx),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
