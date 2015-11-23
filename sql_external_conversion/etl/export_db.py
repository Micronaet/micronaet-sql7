# -*- encoding: utf-8 -*-
# List field and first 5 element of table in argv
import xmlrpclib

# Set up parameters (for connection to Open ERP Database) ********************************************
dbname = 'database'
user = 'admin'
pwd = 'password'
server = 'localhost'
port = 8069

# For final user: Do not modify nothing below this line (Python Code) ********************************
sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/common'%(server, port))
uid = sock.login(dbname ,user ,pwd)
sock = xmlrpclib.ServerProxy('http://%s:%s/xmlrpc/object'%(server, port))

# Export all anagrafic utilized with search in external DB:

# Export product: ##############################################################
print sock.execute(dbname, uid, pwd, "sql.conversion", 'export_object', 'product.product', 'default_code')

# Export partner: ##############################################################
print sock.execute(dbname, uid, pwd, "sql.conversion", 'export_object', 'res.partner', 'sql_supplier_code')
print sock.execute(dbname, uid, pwd, "sql.conversion", 'export_object', 'res.partner', 'sql_customer_code')
print sock.execute(dbname, uid, pwd, "sql.conversion", 'export_object', 'res.partner', 'sql_destination_code')

# Export sql.move.line: ########################################################
print sock.execute(dbname, uid, pwd, "sql.conversion", 'export_object', 'sql.move.line', 'name')


