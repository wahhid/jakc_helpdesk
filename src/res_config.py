from openerp.osv import fields, osv

class itms_config_settings(osv.osv_memory):
    _name = 'itms.config.settings'
    _inherit = 'res.config.settings'
    _columns = {
        'server_url': fields.char('Name', size=100, required=True),
    }
    
    