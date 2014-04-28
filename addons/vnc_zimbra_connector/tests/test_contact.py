# -*- coding: utf-8 -*-

from openerp import tools
from openerp.tests import common
import time

class TestContact(common.TransactionCase):

    def setUp(self):
        """*****setUp*****"""
        super(TestContact, self).setUp()
        cr, uid = self.cr, self.uid
        
        self.res_partner = self.registry('res.partner')
                
    def test_00_create_contact(self):
        cr, uid = self.cr, self.uid
        self.values = {'first_name': 'First name', 'middle_name': 'Middle name', 'last_name': 'Last name', 'is_company': False}
        self.partner_id = self.res_partner.create(cr, uid, self.values, context=None)
        self.cr.commit()
        self.assertTrue(type(self.partner_id), int)

    def test_01_update_contact(self):
        cr, uid = self.cr, self.uid
        self.search_ids = self.res_partner.search(cr, uid, [('first_name', 'ilike', 'First name')])
        self.updated_vals = {'first_name': 'Test First', 'middle_name': 'Test middle', 'last_name': 'Test last'}
        if self.search_ids:
            self.assertTrue(self.res_partner.write(cr, uid, self.search_ids, self.updated_vals))
            self.cr.commit()
        
    def test_02_delete_contact(self):
        cr, uid = self.cr, self.uid
        self.search_ids = self.res_partner.search(cr, uid, [('first_name', 'ilike', 'Test First')])
        if self.search_ids:
            self.assertTrue(self.res_partner.unlink(cr, uid, self.search_ids))
            self.cr.commit()
        