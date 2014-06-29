from openerp.osv import fields, osv
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

reportserver = 'localhost'
reportserverport = '8888'

class helpdesk_daily_detail_report(osv.osv_memory):
    _name = "helpdesk.daily.detail.report"
    _columns = {
        'start_date' : fields.date('Start Date', required=True),
        'end_date' : fields.date('End Date', required=True)
    } 
    _default = {
        'start_date': lambda *a: fields.datetime.now(),
        'end_date': lambda *a: fields.datetime.now(),
    }
    
    def generate_report(self, cr, uid, ids, context=None):
        params = self.browse(cr, uid, ids, context=context)
        param = params[0]   
        serverUrl = 'http://' + reportserver + ':' + reportserverport +'/jasperserver'
        j_username = 'itms_operator'
        j_password = 'itms123'
        ParentFolderUri = '/itms'
        reportUnit = '/itms/helpdesk_daily_detail_report'
        url = serverUrl + '/flow.html?_flowId=viewReportFlow&standAlone=true&_flowId=viewReportFlow&ParentFolderUri=' + ParentFolderUri + '&reportUnit=' + reportUnit + '&START_DATE=' +  param.start_date + '&decorate=no&j_username=' + j_username + '&j_password=' + j_password
        return {
            'type':'ir.actions.act_url',
            'url': url,
            'nodestroy': True,
            'target': 'new' 
        }
        
helpdesk_daily_detail_report()

class helpdesk_monthly_detail_report(osv.osv_memory):
    _name = "helpdesk.monthly.detail.report"
    _columns = {
        'start_date' : fields.date('Start Date', required=True),
        'end_date' : fields.date('End Date', required=True)
    }     
    
    def generate_report(self, cr, uid, ids, context=None):
        params = self.browse(cr, uid, ids, context=context)
        param = params[0]   
        serverUrl = 'http://' + reportserver + ':' + reportserverport +'/jasperserver'
        j_username = 'itms_operator'
        j_password = 'itms123'
        ParentFolderUri = '/itms'
        reportUnit = '/itms/helpdesk_daily_detail_report'
        url = serverUrl + '/flow.html?_flowId=viewReportFlow&standAlone=true&_flowId=viewReportFlow&ParentFolderUri=' + ParentFolderUri + '&reportUnit=' + reportUnit + '&START_DATE=' +  param.start_date + '&decorate=no&j_username=' + j_username + '&j_password=' + j_password
        return {
            'type':'ir.actions.act_url',
            'url': url,
            'nodestroy': True,
            'target': 'new' 
        }    
        
helpdesk_monthly_detail_report()

class helpdesk_monthly_summary_report(osv.osv_memory):
    _name = "helpdesk.monthly.summary.report"
    _columns = {
        'start_date' : fields.date('Start Date', required=True),
        'end_date' : fields.date('End Date', required=True)
    }     
    
    def generate_report(self, cr, uid, ids, context=None):
        params = self.browse(cr, uid, ids, context=context)
        param = params[0]   
        serverUrl = 'http://' + reportserver + ':' + reportserverport +'/jasperserver'
        j_username = 'itms_operator'
        j_password = 'itms123'
        ParentFolderUri = '/itms'
        reportUnit = '/itms/helpdesk_daily_detail_report'
        url = serverUrl + '/flow.html?_flowId=viewReportFlow&standAlone=true&_flowId=viewReportFlow&ParentFolderUri=' + ParentFolderUri + '&reportUnit=' + reportUnit + '&START_DATE=' +  param.start_date + '&decorate=no&j_username=' + j_username + '&j_password=' + j_password
        return {
            'type':'ir.actions.act_url',
            'url': url,
            'nodestroy': True,
            'target': 'new' 
        }    
        
helpdesk_monthly_summary_report()