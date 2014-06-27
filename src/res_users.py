from openerp.osv import fields,osv

class res_users(osv.osv):    
    _name = 'res.users'
    _inherit = 'res.users'    
    _columns = {
        'technician': fields.boolean('Technician'),
    }
    
res_users()