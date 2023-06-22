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
import logging
import pdb
from openerp.osv import osv, fields
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)


class product_categ(osv.osv):
    """ Extend product.category
    """
    _inherit = 'product.category'

    def name_get(self, cr, uid, ids, context=None):
        """ Force detailed view
        """
        if context is None:
            context = {}

        # Detailed mode:
        if isinstance(ids, (list, tuple)) and not len(ids):
            return []

        if isinstance(ids, int):
            ids = [ids]

        res = []
        for record in self.browse(cr, uid, ids, context=context):
            res.append((record.id, '%s%s' % (
                record.name,
                ('[%s]' % record.account_ref) if record.account_ref else '',
            )))
        return res

    def preload_category_from_account_old(
            self, cr, uid, force_category_csv=False, context=None):
        """ Preload from file
        """
        if not force_category_csv:
            force_category_csv = '~/account/catstatpan.csv'
        stat_file = os.path.expanduser(force_category_csv)
        _logger.info('Reading Cat. Stat. from %s' % stat_file)

        i = 0
        all_product_id = 1

        current_stat = {}

        stat_ids = self.search(cr, uid, [
            ('auto_category_type', '=', 'statistic_category'),
        ], context=context)
        for stat in self.browse(cr, uid, stat_ids, context=context):
            if stat.account_ref:
                current_stat[stat.account_ref] = stat.id

        parent_code_db = {}
        for line in open(stat_file, 'r'):
            i += 1
            line = line.strip()
            if not line:
                _logger.warning('%s. Jump empty line' % i)
                continue

            row = line.split(';')
            if len(row) != 2:
                _logger.warning('%s. Different number of columns!' % i)
                continue

            account_ref = row[0].strip()
            name = row[1].strip().title().replace('/', ' - ')
            parent_code = '%s00' % account_ref[:1]
            if account_ref in current_stat:
                stat_id = current_stat[account_ref]
                self.write(cr, uid, [stat_id], {
                    'name': name,
                }, context=context)
                del(current_stat[account_ref])
            else:
                stat_id = self.create(cr, uid, {
                    'name': name,
                    'account_ref': account_ref,
                    'code_list': account_ref,
                    'parent_id': parent_code_db.get(
                        parent_code, all_product_id),
                    'auto_category_type': 'statistic_category',
                }, context=context)

            # Saved for parent ID in child (need alphabetic sort for list)
            if account_ref[1:] == '00':
                parent_code_db[account_ref] = stat_id

        # Delete old items:
        for item_id in current_stat.values():
            self.write(cr, uid, [item_id], {
                'account_ref': False,
                'code_list': False,
            }, context=context)
        return True

    def preload_category_from_account(
            self, cr, uid, force_category_csv=False, context=None):
        """ Preload from file
        """
        if not force_category_csv:
            force_category_csv = '~/account/catstatpan.csv'
        stat_file = os.path.expanduser(force_category_csv)
        _logger.info('Reading Cat. Stat. from %s' % stat_file)

        i = 0
        # all_product_id = 1
        current_stat = {}

        stat_ids = self.search(cr, uid, [
            ('auto_category_type', '=', 'statistic_category'),
        ], context=context)
        for stat in self.browse(cr, uid, stat_ids, context=context):
            if stat.account_ref:
                current_stat[stat.account_ref] = stat.id

        # parent_code_db = {}
        for line in open(stat_file, 'r'):
            i += 1
            line = line.strip()
            if not line:
                _logger.warning('%s. Jump empty line' % i)
                continue

            row = line.split(';')
            if len(row) != 2:
                _logger.warning('%s. Different number of columns!' % i)
                continue

            account_ref = row[0].strip()
            name = row[1].strip().title().replace('/', ' - ')
            # parent_code = '%s00' % account_ref[:1]
            if account_ref in current_stat:
                # Update only name:
                stat_id = current_stat[account_ref]
                self.write(cr, uid, [stat_id], {
                    'name': name,
                }, context=context)
                del(current_stat[account_ref])  # Delete remain after in DB!
            else:
                stat_id = self.create(cr, uid, {
                    'name': name,
                    'account_ref': account_ref,
                    'code_list': account_ref,
                    # 'parent_id': parent_code_db.get(
                    #     parent_code, all_product_id),
                    'auto_category_type': 'statistic_category',
                }, context=context)

            # Saved for parent ID in child (need alphabetic sort for list)
            # if account_ref[1:] == '00':
            #    parent_code_db[account_ref] = stat_id

        # Delete old items:
        for item_id in current_stat.values():
            self.write(cr, uid, [item_id], {
                'account_ref': False,
                'code_list': False,
            }, context=context)
        return True

    # Scheduled action: #######################################################
    def schedule_update_product_category(
            self, cr, uid, force_category_csv=False, context=None):
        """ Update product category from external DB
        """
        _logger.info('Start updating product category')

        # Update category list:
        self.preload_category_from_account(
            cr, uid, force_category_csv, context=context)

        # Read category range:
        category_ids = self.search(cr, uid, [
            ('code_list', '!=', False),
            ('auto_category_type', '=', 'statistic_category'),
        ], context=context)
        category_proxy = self.browse(cr, uid, category_ids, context=context)

        # Update category product in range:
        product_pool = self.pool.get('product.product')
        for category in category_proxy:
            for code in category.code_list.split('|'):
                try:
                    code = code.strip()
                    field_name = category.auto_category_type
                    product_ids = product_pool.search(cr, uid, [
                        (field_name, '=', code),
                    ], context=context)
                    if product_ids:
                        product_pool.write(
                            cr, uid, product_ids, {
                                'categ_id': category.id
                            }, context=context)
                        _logger.info('\nUpdate category: %s [Tot.: %s]' % (
                            category.name,
                            len(product_ids),
                        ))
                except:
                    _logger.error(
                        'Error update product category (%s) products! [%s]' % (
                            category.name,
                            sys.exc_info(),
                        ))
        _logger.info('All product category is updated!')
        return True

    _columns = {
        'account_ref': fields.char('Codice contabile', size=10),
        'code_list': fields.text(
            'Lista codici', help='Elenco codici di questa categoria, usare '
                                 'il carattere | per dividerli'),

        'auto_category_type': fields.selection([
            ('default_code', 'Default code'),
            ('statistic_category', 'Statistic category'),
            ], 'Auto category type'),
        }
