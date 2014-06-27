from openerp.osv import fields, osv
import logging

_logger = logging.getLogger(__name__)

class itms_config_settings(osv.osv_memory):
    _name = 'itms.config.settings'
    _inherit = 'res.config.settings'
    _columns = {
        'email_server': fields.char('POP3 Server', size=100),        
        'username': fields.char('Username', size=100),
        'password': fields.char('Password', size=100),
        'report_server_url': fields.char('Report Server Url', size=100),
        'helpdesk_manager': fields.char('Helpdesk Manager', size=100),
        'helpdesk_email': fields.char('Helpdesk Email', size=100),
    }
    
    