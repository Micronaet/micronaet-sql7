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
from openerp.tools import (
    DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, float_compare)
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)

class product_product(osv.osv):
    _name = 'product.product'
    _inherit = 'product.product'
    
    _columns = {
        'not_analysis': fields.boolean('Not in analysis', required=False),
    }
    _defaults = {
        'not_analysis': lambda *a: False,
    }
    
class micronaet_accounting(osv.osv):
    ''' Object for keep function with the query
        Record are only table with last date of access
    '''
    _name = "micronaet.accounting"
    _description = "Micronaet accounting"

    # Format parameters (for keys):
    KEY_MM_HEADER_FORMAT = "%(CSG_DOC)s%(NGB_SR_DOC)s:" + \
        datetime.now().strftime("%y") + "-%(NGL_DOC)s"
    KEY_MM_LINE_FORMAT = "%(CSG_DOC)s%(NGB_SR_DOC)s:" + \
        datetime.now().strftime("%y") + \
        "-%(NGL_DOC)s[%(NPR_DOC)s.%(NPR_RIGA_ART)s]"

    KEY_OC_LINE_FORMAT = "%(CSG_DOC)s%(NGB_SR_DOC)s:" + \
        datetime.now().strftime("%y") + "-%(NGL_DOC)s[%(NPR_RIGA)s]"
    KEY_OC_FORMAT = "%(CSG_DOC)s%(NGB_SR_DOC)s:" + \
        datetime.now().strftime("%y") + "-%(NGL_DOC)s"
        
    # -----------------
    # Utility function:
    # -----------------
    def connect(self, cr, uid, year=False, context=None):
        ''' Connect action for link to MSSQL DB
            Method is multi year compliant and get year (int) vale for create
            a parametric db access name (name + year(4)), ex.: db2012
            Set correctly parameter of multi year in company SQL settings
        '''        
        try:
            connection = self.pool.get('res.company').mssql_connect(
                cr, uid, year=year, context=context)  # first company
            cursor = connection.cursor()
            if not cursor: 
                _logger.error("Can't access in Company MSSQL Database!")
                return False
            return cursor
        except:
            return False    

    def no_date(self, data_value):
        ''' Test for empty date
            Accounting program use 01/01/1900 for no date
        '''
        return data_value == datetime.strptime("1900-01-01", "%Y-%m-%d")

    def get_empty_date(self):
        ''' Return datetime object for empty date
            Mexal use 01/01/1900 for no date
        '''
        return datetime.strptime("1900-01-01","%Y-%m-%d")
           
    # -------------------------------------------------------------------------   
    #                             Table access method
    # -------------------------------------------------------------------------   
    # ------------
    #  TRANSPORT -
    # ------------
    def get_transportation(self, cr, uid, year=False, context=None):
        ''' Access to anagrafic table of transportation
            Table: MC_CAUS_MOVIMENTI
        '''
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "MC_CAUS_MOVIMENTI" 
        else:
            table = "mc_caus_movimenti"

        cursor = self.connect(cr, uid, year=year, context=context)
        try:#                        ID       Description
            cursor.execute("""SELECT NKY_CAUM, CDS_CAUM FROM %s;""" % table)
            return cursor # with the query setted up                  
        except: 
            return False  # Error return nothing

    # -----------
    #  PAYMENTS -
    # -----------
    def get_payment(self, cr, uid, year=False, context=None):
        ''' Access to anagrafic table of payments
            Table: CP_PAGAMENTI
        '''
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "CP_PAGAMENTI" 
        else:
            table = "cp_pagamenti"

        cursor = self.connect(cr, uid, year=year, context=context)
        try:#                        ID       Description
            cursor.execute("""SELECT NKY_PAG, CDS_PAG FROM %s;""" % table)
            return cursor # with the query setted up                  
        except: 
            return False  # Error return nothing

    def get_payment_partner(self, cr, uid, year=False, context=None):
        ''' Access to anagrafic partner link to table of payments
            Table: PC_CONDIZIONI_COMM
            (only record with payment setted up)
        '''
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "PC_CONDIZIONI_COMM" 
        else:
            table = "pc_condizioni_comm"

        cursor = self.connect(cr, uid, year=year, context=context)
        try:
            cursor.execute("""
                SELECT CKY_CNT, NKY_PAG FROM %s WHERE NKY_PAG>0;""" % table)
            return cursor # with the query setted up                  
        except: 
            return False  # Error return nothing

    def get_parent_partner(self, cr, uid, year=False, context=None):
        ''' Parent partner code for destination
            Table: PC_CONDIZIONI_COMM
        '''
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "PC_CONDIZIONI_COMM" 
        else:
            table = "pc_condizioni_comm"

        cursor = self.connect(cr, uid, year=year, context=context)
        try:#                        ID       Description
            cursor.execute("""
                SELECT CKY_CNT, CKY_CNT_CLI_FATT 
                FROM %s WHERE CKY_CNT_CLI_FATT != '';""" % table)
            return cursor # with the query setted up                  
        except: 
            return False  # Error return nothing

    # ----------
    #  PARTNER -
    # ---------
    def get_partner(self, cr, uid, from_code, to_code, write_date_from=False, 
            write_date_to=False, create_date_from=False, create_date_to=False, 
            year=False, context=None):
        ''' Import partner, customer or supplier, depend on from to code passed
            Table: PA_RUBR_PDC_CLFR
            Extra where clause: from_code, to_code, write from/to, 
            create from/to
        '''
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "PA_RUBR_PDC_CLFR" 
        else:
            table = "pa_rubr_pdc_clfr"
            
        cursor = self.connect(cr, uid, year=year, context=context)
        
        # Compose where clause:
        where_clause = ""
        if from_code: 
            where_clause += "%s CKY_CNT >= '%s' " % (
                "AND" if where_clause else "", from_code)
        if to_code: 
            where_clause += "%s CKY_CNT < '%s' " % (
                "AND" if where_clause else "", to_code)
            
        if create_date_from:
            where_clause += "%s DTT_CRE >= '%s' " % (
                "AND" if where_clause else "", create_date_from)
        if create_date_to:
            where_clause += "%s DTT_CRE <= '%s' " % (
                "AND" if where_clause else "", create_date_to)
            
        if write_date_from:
            where_clause += "%s DTT_AGG_ANAG >= '%s' " % (
                "AND" if where_clause else "", write_date_from)
        if write_date_to:
            where_clause += "%s DTT_AGG_ANAG <= '%s' " % (
                "AND" if where_clause else "", write_date_to)

        try:
            cursor.execute(
                """
                SELECT 
                    CKY_CNT, CDS_CNT, CDS_RAGSOC_COGN, CDS_INDIR, CDS_CAP, 
                    CDS_LOC, CDS_PROV, CDS_TEL_TELEX, CSG_CFIS, CSG_PIVA, 
                    CDS_FAX, CDS_INET, CKY_PAESE, CDS_URL_INET
                FROM %s %s;""" % (
                    table, 
                    "WHERE %s" % where_clause if where_clause else "")
            )
            return cursor # with the query setted up                  
        except: 
            return False  # Error return nothing

    def get_partner_commercial(self, cr, uid, from_code, to_code, year=False, 
            context=None):
        ''' Import partner extra commercial info
            Table: PC_CONDIZIONI_COMM
        '''
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "PC_CONDIZIONI_COMM" 
        else:
            table = "pc_condizioni_comm"

        cursor = self.connect(cr, uid, year=year, context=context)        
        try:
            cursor.execute("""
                SELECT * 
                FROM %s WHERE CKY_CNT >= %s and CKY_CNT < %s;""" % (
                    table,
                    from_code,
                    to_code, 
            ))
            return cursor # with the query setted up                  
        except:
            return False  # Error return nothing

    # -----------
    #  PRODUCTS -
    # -----------
    def is_active(self, record):
        ''' Test if record passed is an active product
        '''
        return record['IFL_ART_CANC'] == 'N' and record['IFL_ART_ANN'] == 'N'
        
    def get_composition(self, cr, uid, year=False, context=None):
        ''' Access to anagrafic table of composition (product)
            Note: Composition: Sxx format
            Table: AR_ANAGRAFICHE
        '''
        if self.pool.get('res.company').table_capital_name(
            cr, uid, context=context):
            table = "AR_ANAGRAFICHE" 
        else:
            table = "ar_anagrafiche"

        cursor = self.connect(cr, uid, year=year, context=context)
        
        # Compose where clause:
        try:
            cursor.execute(
                """
                SELECT 
                    CKY_ART, CDS_ART, CSG_ART_ALT, CDS_AGGIUN_ART 
                FROM %s 
                WHERE CKY_ART like 'S%s' and length(CKY_ART)=3;""" % (
                    table,
                    '%'))
            
            return cursor # with the query setted up                  
        except:
            return False  # Error return nothing


    def get_product(self, cr, uid, active=True, write_date_from=False, 
            write_date_to=False, create_date_from=False, create_date_to=False, 
            year=False, context=None):
        ''' Access to anagrafic table of product and return dictionary read
            only active product
            Table: AR_ANAGRAFICHE
            Where clause: active, from_date, to_date
        '''
        if self.pool.get('res.company').table_capital_name(
                cr, uid, context=context):
            table = "AR_ANAGRAFICHE" 
        else:
            table = "ar_anagrafiche"

        cursor = self.connect(cr, uid, year=year, context=context)
        
        # Compose where clause:
        where_clause = ""
        if active: 
            where_clause += "%s IFL_ART_CANC='N' AND IFL_ART_ANN='N' " % (
                "AND" if where_clause else "")
            
        if create_date_from:
            where_clause += "%s DTT_CRE >= '%s' " % (
                "AND" if where_clause else "", create_date_from)
        if create_date_to:
            where_clause += "%s DTT_CRE <= '%s' " % (
                "AND" if where_clause else "", create_date_to)
            
        if write_date_from:
            where_clause += "%s DTT_AGG_ANAG >= '%s' " % (
                "AND" if where_clause else "", write_date_from)
        if write_date_to:
            where_clause += "%s DTT_AGG_ANAG <= '%s' " % (
                "AND" if where_clause else "", write_date_to)

        try:
            cursor.execute(
                """
                    SELECT 
                        CKY_ART, IST_ART, CDS_ART, CSG_ART_ALT, 
                        CSG_UNIMIS_PRI, NMP_COSTD, CDS_AGGIUN_ART, 
                        NMP_UCA, IFL_ART_DBP, IFL_ART_CANC, 
                        IFL_ART_ANN, CKY_CAT_STAT_ART, NKY_CAT_STAT_ART, 
                        CKY_CNT_FOR_AB, DTT_CRE 
                   FROM %s %s;""" % (
                       table, 
                       "WHERE %s" % where_clause if where_clause else ""))
            
            # NOTE: TAX: AR_CONDIZIONI_COMM
            return cursor # with the query setted up                  
        except:
            return False  # Error return nothing

    def get_product_quantity(self, cr, uid, store, year_ref, year=False, 
            context=None):
        ''' Return quantity element for product
            Table: AQ_QUANTITA, fields:
                CKY_ART NKY_DEP NDT_ANNO NQT_INV NQT_CAR NQT_SCAR NQT_ORD_FOR 
                NQT_ORD_CLI NQT_SOSP_CLI NQT_CLI_AUT NQT_INPR  
            store: deposit reference for search
            year_ref: store quantity depend on year (account particularity)
            year: for multi year SQL database access
        '''
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "AQ_QUANTITA" 
        else:
            table = "aq_quantita"
        
        cursor = self.connect(cr, uid, year=year, context=context)
        try:#                        Code     Inv      Car      Scar
            cursor.execute("""SELECT CKY_ART, NQT_INV, NQT_CAR, NQT_SCAR,
                                     NQT_ORD_FOR, NQT_ORD_CLI,
                                     NQT_SOSP_CLI, NQT_CLI_AUT, NQT_INPR
                              FROM %s
                              WHERE NKY_DEP=%s and NDT_ANNO=%s;""" % (
                                  table, store, year_ref))
            return cursor # with the query setted up                  
        except: 
            return False  # Error return nothing

    def get_product_price(self, cr, uid, year=False, context=None):
        ''' Return price table 
            Table: AR_PREZZI
        '''
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "AR_PREZZI" 
        else:
            table = "ar_prezzi"
        
        cursor = self.connect(cr, uid, year=year, context=context)
        try:
            cursor.execute("""SELECT *
                              FROM %s;""" % table)
            return cursor # with the query setted up                  
        except: 
            return False  # Error return nothing

    def get_product_package(self, cr, uid, year=False, context=None):
        ''' Return quantity per package for product
            Table: AR_VAWC_PEROINKGPE
                   Extra table (not present in all installations)            
        '''        
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "AR_VAWC_PESOINKGPE" 
        else:
            table = "ar_vawc_pesoinkgpe"

        cursor = self.connect(cr, uid, year=year, context=context)
        try:#                        
            cursor.execute("""SELECT * FROM %s; """ % table)
            return cursor 
        except: 
            return False  
            
    def get_product_package_columns(self, cr, uid, year=False, context=None):
        ''' Return list of columns for table (used for get package code: 
            NGD_* where * is the CODE)
            Table: AR_VAWC_PEROINKGPE
                   Extra table (not present in all installations)            
        '''        
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "AR_VAWC_PESOINKGPE" 
        else:
            table = "ar_vawc_pesoinkgpe"

        cursor = self.connect(cr, uid, year=year, context=context)
        try:#                        
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE 
                    TABLE_SCHEMA='dbmirror' AND 
                    TABLE_NAME='%s' AND 
                    COLUMN_NAME like 'NGD_%s';""" % (table, "%")) 
            return cursor 
        except: 
            return False  

    def get_product_level(self, cr, uid, store=1, year=False, context=None):
        ''' Access to anagrafic table of product and return dictionary read
            only active product (level for 
            Table: AB_UBICAZIONI
            @store: store dep. (every order level depend on the store chosen)
        '''
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "AB_UBICAZIONI" 
        else:
            table = "ab_ubicazioni"

        cursor = self.connect(cr, uid, year=year, context=context)
        try:
            cursor.execute("""SELECT CKY_ART, NQT_SCORTA_MIN, NQT_SCORTA_MAX
                              FROM %s %s;""" % (
                                  table, 
                                  "WHERE NKY_DEP=%s" % store))
            return cursor # with the query setted up                  
        except: 
            return False  # Error return nothing

    # --------------------
    #  SUPPLIER ORDER OF -
    # --------------------
    def get_of_line_quantity_deadline(self, cr, uid, year=False, context=None):
        ''' Return quantity element for product
            Table: OF_RIGHE
        '''        
        if self.pool.get('res.company').table_capital_name(
                cr, uid, context=context):
            table = "OF_RIGHE" 
        else:
            table = "of_righe"

        cursor = self.connect(cr, uid, year=year, context=context)
        try:
            cursor.execute("""
                SELECT 
                    NPR_RIGA, CKY_ART, DTT_SCAD, NGB_TIPO_QTA, 
                    NQT_RIGA_O_PLOR, NCF_CONV
                FROM %s;""" % table)
            # Sort: NGL_DOC, NPR_SORT_RIGA                 
            return cursor # with the query setted up                  
        except: 
            return False  # Error return nothing    

    # -------------------
    # CUSTOMER ORDER OC -
    # -------------------
    def get_oc_header(self, cr, uid, year=False, context=None):
        ''' Return list of OC order (header)
            Table: OC_TESTATE
        '''        
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "OC_TESTATE" 
        else:
            table = "oc_testate"

        cursor = self.connect(cr, uid, year=year, context=context)
        try:
            cursor.execute("""
                SELECT 
                    CSG_DOC, NGB_SR_DOC, NGL_DOC, DTT_DOC, CKY_CNT_CLFR, 
                    CKY_CNT_SPED_ALT, CKY_CNT_AGENTE, CKY_CNT_VETT, IST_PORTO, 
                    CDS_NOTE
                FROM %s;""" % table)
            return cursor # with the query setted up
        except: 
            return False  # Error return nothing    
        
    def get_oc_line(self, cr, uid, year=False, context=None):
        ''' Return quantity element for product
            Table: OC_RIGHE
        '''        
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "OC_RIGHE" 
        else:
            table = "oc_righe"

        cursor = self.connect(cr, uid, year=year, context=context)
        try: 
            cursor.execute("""
                SELECT 
                    CSG_DOC, NGB_SR_DOC, NGL_DOC, NPR_RIGA, DTT_SCAD, CKY_ART, 
                    NGB_TIPO_QTA, NQT_RIGA_O_PLOR, NPR_SORT_RIGA, NCF_CONV, 
                    NPZ_UNIT, CDS_VARIAZ_ART
                FROM %s;""" % table)
            # no: NPZ_UNIT, NGL_RIF_RIGA, NPR_SORT_RIGA, NKY_CAUM, NKY_DEP
            return cursor # with the query setted up                  
        except: 
            return False  # Error return nothing    

    def get_oc_funz_line(self, cr, uid, year=False, context=None):
        ''' Object for extra data in OC line
            Table: OC_FUNZ_RIGHE
        '''        
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = "OC_FUNZ_RIGHE" 
        else:
            table = "oc_funz_righe"

        cursor = self.connect(cr, uid, year=year, context=context)
        try: 
            cursor.execute("""
                SELECT 
                    NGB_SR_DOC, CSG_DOC, NGL_DOC, NPR_RIGA, NQT_MOVM_UM1, 
                    NMP_VALMOV_UM1, NGB_COLLI, NMP_PROVV_VLT
                FROM %s;""" % table)
            return cursor # with the query setted up                  
        except: 
            return False  # Error return nothing    

    # ----------------
    #  MOVEMENT LINE -
    # ----------------
    def get_mm_header(self, cr, uid, where_document=None, year=False, 
            context=None):
        ''' Return list of OC order (header)
            Table: MM_TESTATE
        '''    
        table = "mm_testate"
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = table.upper()

        if where_document is None:
            where_document = ()
        elif type(where_document) not in (list, tuple):
            where_document = (where_document, )
        else:
            where_document = tuple(where_document)            
            
        cursor = self.connect(cr, uid, year=year, context=context)
        query = """
                SELECT CSG_DOC, NGB_SR_DOC, NGL_DOC, NPR_DOC, CKY_CNT_CLFR, 
                    DTT_DOC, CSG_DOC_ORI, NGB_SR_DOC_ORI, NGL_DOC_ORI, 
                    DTT_DOC_ORI, CKY_CNT_SPED_ALT, NGB_CASTAT_CLIFOR, CDS_NOTE, 
                    CKY_CNT_AGENTE, NKY_CAUM
                FROM %s%s;""" % (
                    table,
                    " WHERE CSG_DOC in %s" % (
                        where_document, ) if where_document else "")
        query = query.replace(",);", ");") # BAD!!! for remove ","
        try: 
            cursor.execute(query)
            return cursor # with the query setted up
        except: 
            return False  # Error return nothing    

    def get_mm_footer(self, cr, uid, year=False, context=None):
        ''' Return list of OC order (footer)
            Table: MM_PIEDE
        '''    
        table = "mm_piede"
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = table.upper()

        cursor = self.connect(cr, uid, year=year, context=context)
        query = """
                SELECT CSG_DOC, NGB_SR_DOC,	NGL_DOC, NPR_DOC, NKY_PAG 
                FROM %s;""" % table
        try: 
            cursor.execute(query)
            return cursor # with the query setted up
        except: 
            return False  # Error return nothing    
        
    def get_mm_line(self, cr, uid, where_document=False, where_partner=False, 
            year=False, context=None):
        ''' Return quantity element for product
            where_document: list, tuple, string of document searched (ex. BS)
            where_partner: list, tuple, string for partner code searched            
            Table: MM_RIGHE            
        '''        
        query = "Not loaded"
        table = "mm_righe"
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = table.upper()

        cursor = self.connect(cr, uid, year=year, context=context)

        # -------------------
        # Manage where clause
        # -------------------
        # Filter document type:
        where_clause = ""
        if where_document: # force tuple (for list, tuple or string)
            if type(where_document) in (str, unicode):
                where_document = (str(where_document), ) 
            where_clause = "CSG_DOC in %s" % (tuple(where_document), )
            
        # Filter partner
        if where_partner: # force tuple
            if type(where_partner) in (str, unicode):
                where_partner = (str(where_partner), ) 
            if where_clause: # (document clause)
                where_clause += " AND CKY_CNT_CLFR in %s" % (
                    tuple(where_partner), )
            else:
                where_clause += "CKY_CNT_CLFR in %s" % (
                    tuple(where_partner), )

        # Prepare for query:
        if where_clause:
            where_clause = " WHERE %s" % where_clause
            where_clause = where_clause.replace(",)", ")") # BAD! remove ','
            
        query = """
            SELECT 
                CSG_DOC, NGB_SR_DOC, NGL_DOC, NPR_DOC, CKY_CNT_CLFR,
                NPZ_UNIT, NQT_RIGA_ART_PLOR, NCF_CONV,
                NPR_RIGA_ART, CKY_ART, NDC_QTA, 
                CDS_VARIAB_ART, DTT_SCAD
            FROM %s%s;""" % (table, where_clause)            
                
        try:             
            cursor.execute(query)
            return cursor # with the query setted up                  
        except: 
            _logger.error("Problem launch query: %s [%s]" % (
                query, sys.exc_info()))
            return False

    def get_mm_header_line(self, cr, uid, where_document=False, 
        where_partner=False, year=False, originator=False, order_by=False,
        context=None):
        ''' Return quantity element for product
            where_document: list, tuple, string of document searched (ex. BS)
            where_partner: list, tuple, string for partner code searched            
            Table: MM_RIGHE
            where_document: type of document search, ex.: BC, FT
            where_partner: partner code search, ex. 201.00001
            year: for multi year manage database name depend on this param.
            originator: Search where_document in originator not in reference
               (so CSG_DOC_ORI instead of CSG_DOC)
            order_by: clause, like: 'DTT_DOC desc'
        '''        
        query = "Not loaded"
        table_header = "mm_testate"
        table_line = "mm_righe"
        
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table_header = table_header.upper()
            table_line = table_line.upper()

        cursor = self.connect(cr, uid, year=year, context=context)

        # -------------------
        # Manage where clause
        # -------------------
        # Filter document type:
        where_clause = ""
        if where_document: # force tuple (for list, tuple or string)
            if type(where_document) in (str, unicode):
                where_document = (str(where_document), ) 
            if originator:
                where_field = "h.CSG_DOC_ORI"
            else:
                where_field = "l.CSG_DOC"
                
            where_clause = "%s in %s" % (where_field, tuple(where_document))
            
        # Filter partner
        if where_partner: # force tuple
            if type(where_partner) in (str, unicode):
                where_partner = (str(where_partner), ) 
            if where_clause: # (document clause)
                where_clause += " AND l.CKY_CNT_CLFR in %s" % (
                    tuple(where_partner), )
            else:
                where_clause += "l.CKY_CNT_CLFR in %s" % (
                    tuple(where_partner), )

        # Prepare for query:
        if where_clause:
            where_clause = " WHERE %s" % where_clause
            where_clause = where_clause.replace(",)", ")") # BAD! remove ','

        if order_by:
            order_by = " ORDER BY %s" % order_by
        else:
            order_by = ""    
            
        query = """
            SELECT 
                l.CSG_DOC as CSG_DOC, l.NGB_SR_DOC as NGB_SR_DOC, 
                l.NGL_DOC as NGL_DOC, l.NPR_DOC as NPR_DOC, 
                l.CKY_CNT_CLFR as CKY_CNT_CLFR, l.NPZ_UNIT as NPZ_UNIT, 
                l.NQT_RIGA_ART_PLOR as NQT_RIGA_ART_PLOR, 
                l.NCF_CONV as NCF_CONV, l.NPR_RIGA_ART as NPR_RIGA_ART, 
                l.CKY_ART as CKY_ART, l.NDC_QTA as NDC_QTA, 
                l.CDS_VARIAB_ART as CDS_VARIAB_ART, l.DTT_SCAD as DTT_SCAD,
                h.DTT_DOC as DTT_DOC, h.CSG_DOC_ORI as CSG_DOC_ORI,
                h.DTT_DOC_ORI as DTT_DOC_ORI, h.NKY_CAUM as NKY_CAUM
            FROM %s h JOIN %s l 
                ON (h.CSG_DOC = l.CSG_DOC AND h.NGB_SR_DOC = l.NGB_SR_DOC AND
                    h.NGL_DOC = l.NGL_DOC AND h.NPR_DOC = l.NPR_DOC) 
                    %s%s;""" % (
                table_header,
                table_line, 
                where_clause,
                order_by,
                )
                
        try:             
            cursor.execute(query)
            return cursor # with the query setted up                  
        except: 
            _logger.error("Problem launch query: %s [%s]" % (
                query, sys.exc_info()))
            return False

    def get_mm_situation(self, cr, uid, document, partner_code, year=False, 
        originator=False, context=None):
        ''' Return quantity product usually buyed with total and delivery
            where_document: list, tuple, string of document searched (ex. BS)
            where_partner: list, tuple, string for partner code searched            
            Table: MM_RIGHE            
            document: filter for this reference, ex.: BC, FT
            partner_code: filter for this partner code, ex.: 201.00001
            year: query on database (multi year mode) selected
            originator: query on origin document not current 
                (so CSG_DOC_ORI instead of CSG_DOC)
        '''        
        query = "Not loaded"
        table_header = "mm_testate"
        table_line = "mm_righe"
        
        if self.pool.get('res.company').table_capital_name(
                cr, uid, context=context):
            table_header = table_header.upper()
            table_line = table_line.upper()

        cursor = self.connect(cr, uid, year=year, context=context)

        # -------------------
        # Manage where clause
        # -------------------
        # Filter document type:
        #TODO change query linked to header if there's originator
        if originator:
            query = """
                SELECT 
                    l.CKY_CNT_CLFR as CKY_CNT_CLFR, l.CKY_ART as CKY_ART,
                    l.CDS_VARIAB_ART as CDS_VARIAB_ART, 
                    SUM(l.NQT_RIGA_ART_PLOR * 
                        (IF(l.NCF_CONV=0, 1, 1/l.NCF_CONV))) as TOTALE, 
                    count(*) as CONSEGNE 
                FROM %s h JOIN %s l 
                    ON (h.CSG_DOC = l.CSG_DOC AND h.NGB_SR_DOC = l.NGB_SR_DOC 
                    AND
                        h.NGL_DOC = l.NGL_DOC AND h.NPR_DOC = l.NPR_DOC) 
                GROUP BY
                    h.CSG_DOC_ORI, l.CKY_CNT_CLFR, l.CKY_ART, l.CDS_VARIAB_ART 
                HAVING 
                    h.CSG_DOC_ORI = '%s' AND l.CKY_CNT_CLFR = '%s';""" % (
                    table_header,
                    table_line, 
                    document,
                    partner_code,
                    )            
        else: 
            query = """
                SELECT 
                    CKY_CNT_CLFR, CKY_ART, CDS_VARIAB_ART, 
                    SUM(NQT_RIGA_ART_PLOR * (IF(NCF_CONV=0, 1, 1/NCF_CONV))) 
                        as TOTALE, 
                    count(*) as CONSEGNE 
                FROM 
                    %s 
                GROUP BY
                    CSG_DOC, CKY_CNT_CLFR, CKY_ART, CDS_VARIAB_ART 
                HAVING 
                    CSG_DOC = '%s' AND CKY_CNT_CLFR = '%s';
                """ % (table_line, document, partner_code)            

        try:             
            cursor.execute(query)
            return cursor # with the query setted up                  
        except: 
            _logger.error("Problem launch query: %s [%s]" % (
                query, sys.exc_info()))
            return False

    def get_mm_funz_line(self, cr, uid, where_document=None, year=False, 
            context=None):
        ''' Return quantity element for product funz
            Table: MM_FUNZ_RIGHE
        '''        
        table = "mm_funz_righe"
        if self.pool.get('res.company').table_capital_name(cr, uid, 
                context=context):
            table = table.upper()

        if where_document is None:
            where_document = ()
        elif type(where_document) not in (list, tuple): # single string
            where_document = (where_document, )
        else:
            where_document = tuple(where_document)

        cursor = self.connect(cr, uid, year=year, context=context)
        query = """
                SELECT 
                    CSG_DOC, NGB_SR_DOC, NGL_DOC, NPR_DOC, CKY_CNT_CLFR, 
                    NPR_RIGA_ART, NQT_MOVM_UM1, NMP_VALMOV_UM1
                FROM %s%s;""" % (
                    table,
                    " WHERE CSG_DOC in %s" % (
                        where_document, ) if where_document else "", )                    
        query = query.replace(",);", ");") # BAD!!! for remove ","
        try: #                       
            cursor.execute(query)
            return cursor # with the query setted up                  
        except:
            return False  # Error return nothing
        
    _columns = {
        'name':fields.char('SQL table', size=80, required=True),
        'datetime': fields.datetime('Last read'),
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
