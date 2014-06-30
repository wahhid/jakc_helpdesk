from openerp.osv import fields,osv

class hr_employee(osv.osv):    
    _name = 'hr.employee'
    _inherit = 'hr.employee'    
    _columns = {
        'company': fields.many2one('itms.company', 'Company'),
    }
    
hr_employee()    