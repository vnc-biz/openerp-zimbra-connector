import time
import ast
from datetime import datetime

from openerp.osv import fields, osv

class hr_employee(osv.osv):
    _inherit='hr.employee'
    _columns={
              'first_name':fields.char('First Name',size=128),
              'last_name':fields.char('Last Name',size=128),
              'started_career_vnc_on': fields.date('Started career here on'),
              }

    def employee_sync_openerp(self,cr, uid, zuid=False, addbookid=False, context=None):
        
        if not zuid and not addbookid:
            return {'error':'UserID/AddressBook ID missing !'}
        
        deleted_datas = {'deleted_datas':[]}
        zimbra_contactsync_pool = self.pool.get('zimbra.contactsync.log')
        zsync_ids = zimbra_contactsync_pool.search(cr, uid, \
                                                   [('zimbra_uid','=',zuid),('addbook_id','=',addbookid), ('resource', '=', 'hr.employee')])
        
        if zsync_ids:
            data_read = zimbra_contactsync_pool.read(cr, uid, zsync_ids[0])
            
            if data_read['delete_items']:
                deleted_datas['deleted_datas'] = ast.literal_eval(data_read['delete_items'])
                
            emp_ids = self.search(cr, uid, [('write_date','>',\
                            str(datetime.strptime(data_read['last_sync'],'%Y-%m-%d %H:%M:%S')))])
            
            datas = self.export_data(cr,uid,emp_ids, ['id','first_name','last_name',\
                                      'work_phone','work_email','mobile_phone','address_home_id/first_name', 'address_home_id/fax', 'address_home_id/title',\
                                      'address_home_id/city','address_home_id/street','address_home_id/street2',\
                                        'address_home_id/country_id','address_home_id/state_id','address_home_id/zip'])
            
            zimbra_contactsync_pool.write(cr, uid, zsync_ids, 
                                {
                                'last_sync':time.strftime('%Y-%m-%d %H:%M:%S'),
                                })
        else:
            emp_ids = self.search(cr, uid, [])
            datas = self.export_data(cr,uid,emp_ids, ['id','first_name','last_name',\
                                                    'work_phone','work_email','mobile_phone','address_home_id/first_name', 'address_home_id/fax', 'address_home_id/title',\
                                                    'address_home_id/city','address_home_id/street','address_home_id/street2',\
                                                    'address_home_id/country_id','address_home_id/state_id','address_home_id/zip'])
            zimbra_contactsync_pool.create(cr, uid, {
                                'zimbra_uid':zuid,
                                'addbook_id':addbookid,
                                'last_sync':time.strftime('%Y-%m-%d %H:%M:%S'),
                                'resource': 'hr.employee'
                                })

        return datas, deleted_datas
    
    def create(self, cr, uid, vals, context=None):
        if vals.get('name'):
            name = vals['name'].strip()
            name_data = name.split(' ')
            vals['first_name'] = name_data[0]
            vals['last_name'] = name_data[-1]
        return super(hr_employee, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        if not type(ids) is list:
            ids = [ids]
        for data in self.browse(cr, uid, ids):
            if vals.get('name'):
                name = vals['name'].strip()
                name_data = name.split(' ')
                vals['first_name'] = name_data[0]
                vals['last_name'] = name_data[-1]
                
        return super(hr_employee, self).write(cr, uid, ids, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        datas = []
        data_write = []

        all_ids = self.pool.get('zimbra.contactsync.log').search(cr, uid, [('resource', '=', 'hr.employee')])
        for zcs in self.pool.get('zimbra.contactsync.log').browse(cr, uid, all_ids):
            if zcs.delete_items:
                data_write = ast.literal_eval(zcs.delete_items)
                datas = self.export_data(cr, uid, ids, ['id'])
                for d in datas['datas']:
                    data_write.append(d[0])
            else:
                datas = self.export_data(cr, uid, ids, ['id'])
                for d in datas['datas']:
                    data_write.append(d[0])
            self.pool.get('zimbra.contactsync.log').write(cr, uid, zcs.id, {'delete_items':data_write})
        return super(hr_employee, self).unlink(cr, uid, ids, context=context)
        
    def employee_name_cron(self, cr, uid, context={}):
        ids = self.search(cr, uid, [], context=context)
        for data in self.browse(cr, uid, ids, context=context):            
            name = data.name.strip()
            name_data = name.split(' ')
            self.write(cr, uid, data['id'], {'first_name': name_data[0], 'last_name': name_data[-1]},\
                            context)
        return True
        