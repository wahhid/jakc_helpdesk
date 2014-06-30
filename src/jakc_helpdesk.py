from openerp.addons.base_status.base_state import base_state
from openerp.addons.base_status.base_stage import base_stage

from imaplib import IMAP4
from imaplib import IMAP4_SSL
from poplib import POP3
from poplib import POP3_SSL
import xmlrpclib


from openerp.osv import fields, osv
from datetime import datetime
from openerp import netsvc
from openerp.tools import html2plaintext
from openerp.tools.translate import _
from parsemail import Attachment

import string
import random
import time
import re
import email
from email.message import Message
import base64
import dateutil
import pytz

import logging

_logger = logging.getLogger(__name__)

AVAILABLE_STATES = [
    ('draft','New'),    
    ('open','Open'),    
    ('response','Response'),
    ('request','Request For Approval'),    
    ('request_response','Request For Approval Response'),    
    ('cancel', 'Cancelled'),
    ('done', 'Closed'),
    ('pending','Pending'),
    ('cancel_pending','Cancel Pending')
]

pop3server = 'localhost'
pop3port = '110'
pop3user  = 'helpdesk@jakc.com'
pop3password = 'P@ssw0rd'
helpdesk_manager = 'whidayat@jakc.com'
helpdesk_email = 'helpdesk@jakc.com'
reportserver = 'localhost'
reportserverport = '8888'
intapprovalserver = 'localhost'
intapprovalserverport = '5000'
extapprovalserver = 'localhost'
extapprovalserverport = '5000'

class helpdesk_category(osv.osv):
    _name = "helpdesk.category"
    _description = "Helpdesk Category"
    _columns = {
        'name': fields.char('Name', size=100, required=True),            
    }    
helpdesk_category()

class helpdesk_priority(osv.osv):
    _name = "helpdesk.priority"
    _description = "Helpdesk Priority"
    _columns = {
        'name': fields.char('Name', size=100, required=True),            
    }        
    
helpdesk_priority()
    
class helpdesk_conversation_employee(osv.osv):
    _name = "helpdesk.conversation.employee"
    _description = "Helpdesk Conversation Employee"
    _columns = {
        'conversation_id': fields.many2one('helpdesk.conversation', 'Conversation', readonly=True),       
        'employee_id': fields.many2one('hr.employee', 'Employee', readonly=True),               
    }
    
helpdesk_conversation_employee()


class helpdesk_ticket(base_state, base_stage, osv.osv):
    _name = "helpdesk.ticket"
    _description = "Helpdesk Ticket"            
                
    def connectpop3server(self, cr, uid, context=None):
        connection = POP3(pop3server, int(pop3port))        
        connection.user(pop3user)
        connection.pass_(pop3password)
        return connection
    
    def _parse_track_id(self, subject):
        track_id_prefix = subject.find('<')
        track_id_suffix = subject.find('>')
        if  track_id_prefix > -1 and  track_id_suffix > -1:
            track_id = subject[track_id_prefix+1:track_id_suffix]
            return track_id
        else:            
            return None    
    
    def _get_employee_by_email(self, cr, uid, email_from, context=None):
        obj = self.pool.get('hr.employee')
        ids =  obj.search(cr, uid, [('work_email','=',email_from)], context=context)
        if len(ids) > 0:
            employees = obj.browse(cr, uid, ids, context=context)
            return employees[0]
        else:
            return None
        
    def _get_employee(self, cr, uid, id, context=None):
        obj = self.pool.get('hr.employee')        
        employee = obj.browse(cr, uid, id, context=context)        
        return employee
        
    
    def _get_ticket_by_trackid(self, cr, uid, track_id, context=None):        
        ids = self.pool.get('helpdesk.ticket').search(cr, uid, [('trackid','=',track_id)], context=context)
        if len(ids) > 0:
            tickets = self.pool.get('helpdesk.ticket').browse(cr, uid, ids, context=context)
            return tickets[0]
        else:
            return None

    #Fetch Helpdesk Ticket by ID
    def _get_ticket(self, cr, uid, id, context=None):
        ticket = self.pool.get('helpdesk.ticket').browse(cr, uid, id, context=context)                                        
        return ticket
                       
    def _create_conversation(self, cr, uid, values , context=None):
        return self.pool.get('helpdesk.conversation').create(cr, uid, values, context=context)
    
    def _send_email_notification(self, cr, uid, values, context=None):
        _logger.info(values['start_logger'])
        mail_mail = self.pool.get('mail.mail')
        mail_ids = []
        mail_ids.append(mail_mail.create(cr, uid, {
            'email_from': values['email_from'],
            'email_to': values['email_to'],
            'subject': values['subject'],
            'body_html': values['body_html'],
            }, context=context))
        mail_mail.send(cr, uid, mail_ids, context=context)
        _logger.info(values['end_logger'])          
    
    def fetchmail(self,cr,uid,context=None):
        _logger.info('Start Fetch Helpdesk Email')        
        mailattach = Attachment()                                   
        pop_server = self.connectpop3server(cr,uid,context=context)
        (numMsgs, totalSize) = pop_server.stat()
        pop_server.list()
        for num in range(1, numMsgs + 1):
            (header, msges, octets) = pop_server.retr(num)
            raw = '\n'.join(msges)                      
            msg=email.message_from_string(raw)            
            attachments=mailattach.get_mail_contents(msg)                       
            subject=mailattach.getmailheader(msg.get('Subject', ''))
            desc = html2plaintext(msg.get('body'))
            from_= mailattach.getmailaddresses(msg, 'from')
            from_=('', '') if not from_ else from_[0]                                
            for attach in attachments:
                # dont forget to be careful to sanitize 'filename' and be carefull
                # for filename collision, to before to save :
                print '\tfilename=%r is_body=%s type=%s charset=%s desc=%s size=%d' % (attach.filename, attach.is_body, attach.type, attach.charset, attach.description, 0 if attach.payload==None else len(attach.payload))

                if attach.is_body=='text/plain':
                    # print first 3 lines
                    body = ''
                    payload, used_charset=mailattach.decode_text(attach.payload, attach.charset, 'auto') 
                    for line in payload.split('\n'):
                        # be careful console can be unable to display unicode characters
                        if line:
                            print '\t\t', line            
                            body += line + '\n'
                            
            employee = self._get_employee_by_email(cr, uid, from_[1], context=context)    
            
            if employee:                               
                track_id = self._parse_track_id(subject)            
                if track_id is None:
                    #create ticket
                    ticket_data = {}
                    #Define Employee
                    ticket_data['employee'] = employee.id
                    #Define Subject
                    ticket_data['name'] = subject
                    #Define Description               
                    ticket_data['description'] = body
                    ticket_id = self.pool.get('helpdesk.ticket').create(cr, uid, ticket_data,context=context)                                
                    ticket = self.pool.get('helpdesk.ticket').browse(cr, uid, ticket_id, context=context)                
                else:
                    ticket = self._get_ticket_by_trackid(cr, uid, track_id, context=context)                
                    ticket_id = ticket.id                        
                    conversation_data = {            
                        'ticket_id': ticket_id,
                        'message_date': datetime.now(),
                        'email_from' : employee.id,
                        'name': subject,
                        'description': body,        
                        'inbound': True,
                    }                        

                    conversation_id = self.pool.get('helpdesk.conversation').create(cr, uid, conversation_data, context=context)                            
                    _logger.info("Save Conversation")

                    email_data = {}
                    email_data['start_logger'] = 'Start Email Ticket Conversation Notification'
                    email_data['email_from'] = helpdesk_email
                    email_data['email_to'] = employee.work_email
                    email_data['subject'] = "<" + track_id + "> "  + subject
                    email_data['body_html'] = body
                    email_data['end_logger'] = 'End Email Ticket Conversation Notification'
                    self._send_email_notification(cr, uid, email_data, context=context)                     
                
                #Send Email to All Technician
                
                pop_server.dele(num)   
                print "POP Deleted" 
            else:
                email_data = {}
                email_data['start_logger'] = 'Start Email Not Register Notification'
                email_data['email_from'] = helpdesk_email
                email_data['email_to'] = form_[1]
                email_data['subject'] = "Failed Ticket Request"
                email_data['body_html'] = "Requester not register on the system, please contact IT Support"
                email_data['end_logger'] = 'End Email Not Register Notification'
                self._send_email_notification(cr, uid, email_data, context=context)                                     
                pop_server.dele(num)   
                print "POP Deleted" 
                
        pop_server.quit()
        _logger.info('End Fetch Helpdesk Email')               
        
        return True
           
    #Call Add Conversation Form
    
    
    def add_conversation_action(self, cr, uid, ids, context=None):               
        print ids
        print context
        return {
               'type': 'ir.actions.act_window',
               'name': 'Add Conversation',
               'view_mode': 'form',
               'view_type': 'form',               
               'res_model': 'helpdesk.conversation',
               'nodestroy': True,
               'target':'new',
               'context': {'ticket_id': ids[0]},
    }       
    
    def approve_reject_action(self, cr, uid, ids, context=None):               
        return {
               'type': 'ir.actions.act_window',
               'name': 'Approve or Reject',
               'view_mode': 'form',
               'view_type': 'form',                              
               'res_model': 'helpdesk.approved',
               'nodestroy': True,
               'target':'new',
               'context': {'ticket_id': ids[0]},
    } 
    

    def case_response(self, cr, uid, ids, context=None):
        #Change Status
        self.write(cr,uid,ids,{'response_date':datetime.now(),'state':'response'},context=context)           
        return True
    
    def case_request(self, cr, uid, ids, context=None):
        #Fetch Ticket Informations
        ticket  = ticket = self.pool.get('helpdesk.ticket').browse(cr, uid, ids[0], context=context)                                               

        if not ticket.resolution:            
            #raise osv.except_osv(_('Error!'),_('Please complete resolution field.'))            
            return False
            #warning = {
            #    'title': 'Error',
            #    'message': 'Please complete the resolution for this request'
            #}
            #return {'warning': warning}
        
        #Change Status
        self.write(cr,uid,ids,{'state':'request'},context=context)
        
        return True
    
    
    def case_pending(self, cr, uid, ids, context=None):        
        self.write(cr,uid,ids,{'state':'pending'})  
        return True
    
    def case_cancel_pending(self, cr, uid, ids, context=None):        
        self.write(cr,uid,ids,{'state':'cancel_pending'})          
        return True
    
    def case_close(self, cr, uid, ids, context=None):        
        self.write(cr,uid,ids,{'end_date': datetime.now(),'state':'done'})              
        return True
        
    def case_reset(self, cr, uid, ids, context=None):
        self.write(cr,uid,ids,{'state':'cancel'})        
        return True        
        
        
    def _id_generator(self,cr,uid,context=None):
        size = 10
        chars= string.ascii_uppercase + string.digits
        return ''.join(random.choice(chars) for _ in range(size))
    
    _columns = {
        'trackid': fields.char('Track ID', size=20, readonly=True),        
        'name': fields.char('Subject', size=100, required=True),            
        'employee': fields.many2one('hr.employee','Employee', required=True),
        'category': fields.many2one('helpdesk.category','Category'),
        'priority': fields.selection([('1', 'Highest'),('2', 'High'),('3', 'Normal'),('4', 'Low'),('5', 'Lowest'),],'Priority'),
        'technician': fields.many2one('res.users', 'Responsible'),        
        'asset': fields.many2one('asset.assets','Asset'),
        'description': fields.text('Description'),        
        'start_date': fields.datetime('Start Date', readonly=True),
        'response_date': fields.datetime('Response Date', readonly=True),
        'approved_date': fields.datetime('Approve or Reject Date', readonly=True),        
        'end_date': fields.datetime('End Date', readonly=True),        
        'resolution': fields.text('Resolution'),
        'approved_comment': fields.text('Comment'),
        'duration': fields.float('Duration', readonly=True),
        'active': fields.boolean('Active', required=False),
        'state':  fields.selection(AVAILABLE_STATES, 'Status', size=16, readonly=True),
        'approved_state': fields.selection([('1', 'Not Approved'),('2', 'Approved'),('3', 'Rejected')],'Approved Status',readonly=True),
        'conversation_ids': fields.one2many('helpdesk.conversation', 'ticket_id', 'Conversation'),
    }    
    _defaults = {        
        'active': lambda *a: 1,                        
        'state': lambda *a: 'draft',
        'approved_state': lambda *a: '1',
        'start_date': lambda *a: fields.datetime.now(),
        'priority': lambda *a: '3',
    }
    
    _order = 'start_date desc'
        
    def create(self, cr, uid, values, context=None):		                                
        trackid = self._id_generator(cr, uid, context=context)        
        _logger.info("Track ID : " + trackid)
        #tos=mailattach.getmailaddresses(msg, 'to')                                                                                                           
        values.update({'trackid':trackid})   
        #values.update({'technician': uid})
	ticket_id =  super(helpdesk_ticket, self).create(cr, uid, values, context=context)        
                                
        conversation_data = {            
            'ticket_id': ticket_id,
            'message_date': datetime.now(),
            'email_from' : values['employee'],
            'name': values['name'],
            'description': values['description'],        
            'inbound': True,
        }                        

        conversation_id = self.pool.get('helpdesk.conversation').create(cr, uid, conversation_data, context=context)                            
        _logger.info("Save Conversation")

        employee = self.pool.get('hr.employee').browse(cr, uid, values['employee'], context=context)
        email_data = {}
        email_data['start_logger'] = 'Start Email Ticket Created Notification'
        email_data['email_from'] = helpdesk_email
        email_data['email_to'] = employee.work_email
        email_data['subject'] = "<" + trackid + "> Ticket Receieved Notification"
        msg = '<br/>'.join([
            'Dear Mr/Mrs ' + employee.name,
            '',
            '',
            'We already receive your request with Track ID :' + trackid,
            '',
            'Subject',
            '',
            ticket.name,
            '',
            '',
            'Problem',
            '',
            #ticket.description.replace('\n','<br/>'),
            ticket.description,
            '',
            '',
            '',
            'Regards',
            '',
            '',
            'IT Department'
        ])
        email_data['body_html'] = msg

        #email_data['body_html'] = "Ticket Receieved with track id : " + trackid
        email_data['end_logger'] = 'End Email Ticket Created Notification'
        self._send_email_notification(cr, uid, email_data, context=context)                 
        
        #Send Notification to Technician
        
        return ticket_id
    
    def write(self,cr, uid, ids, values, context=None ):
        result = super(helpdesk_ticket,self).write(cr, uid, ids, values, context=context)        
        if isinstance( ids[0], int ):
            ticket  = self.pool.get('helpdesk.ticket').browse(cr, uid, ids[0], context=context)
        else:
            ticket  = self.pool.get('helpdesk.ticket').browse(cr, uid, int(ids[0]), context=context)
            
        print ticket
        employee = self.pool.get('hr.employee').browse(cr, uid, ticket.employee.id, context=context)
        
        if ticket.state == 'response':            
            super(helpdesk_ticket,self).write(cr, uid, ids, {'state':'open'}, context=context)
            #Create Conversation
            values = {}
            values['ticket_id'] = ticket['id']                    
            values['message_date'] = datetime.now()
            values['description'] = "Ticket was responsed"
            conversation_id = self.pool.get('helpdesk.conversation').create(cr, uid, values, context=context)

            #Send Email Notification
            email_data = {}
            email_data['start_logger'] = 'Start Email Ticket Response Notification'
            email_data['email_from'] = helpdesk_email
            email_data['email_to'] = employee.work_email
            email_data['subject'] = "<" + ticket.trackid + "> " + ticket.name
            email_data['body_html'] = "Dear " + employee.name + "<br/>"  + " We already receieve your  with subject : " + ticket.name + ". We will proceed your request immediately. Thank you"
            email_data['end_logger'] = 'Start Email Ticket Response Notification'
            self._send_email_notification(cr, uid, email_data, context=context)  
            
        if ticket.state == 'request':
            #Create Conversation
            values = {}
            values['ticket_id'] = ticket['id']                    
            values['message_date'] = datetime.now()
            values['description'] = "Request for approval"
            conversation_id = self.pool.get('helpdesk.conversation').create(cr, uid, values, context=context)

            #Send Email Notification
            email_data = {}
            email_data['start_logger'] = 'Start Email Ticket Response Notification'
            email_data['email_from'] = helpdesk_email
            email_data['email_to'] = helpdesk_manager
            email_data['subject'] = "<" + ticket.trackid + "> " + ticket.name
            msg = '<br/>'.join([
                'Dear Ibu Maryland',
                '',
                '',
                'Mohon review and approval untuk request ini :',
                '',
                'Problem',
                '',
                ticket.description,
                '',
                '',
                'Resolution',
                '',
                ticket.resolution.replace('\n','<br/>'),
                '',
                '',
                '',
                'Internal <a href="http://' + intapprovalserver + ':' + intapprovalserverport + '/approval/' + str(ticket.id) +'">Approve or Reject</a>',
                'External <a href="http://' + extapprovalserver + ':' + extapprovalserverport + '/approval/' + str(ticket.id) +'">Approve or Reject</a>',
            ])
            email_data['body_html'] = msg
            email_data['end_logger'] = 'Start Email Ticket Response Notification'
            self._send_email_notification(cr, uid, email_data, context=context)                    
            
        if ticket.state == 'pending':
            #Create Conversation        
            values = {}
            values['ticket_id'] = ids[0]
            values['message_date'] = datetime.now()
            values['description'] = "Ticket Pending"        
            conversation_id = self.pool.get('helpdesk.conversation').create(cr, uid, values, context=context)                    
            
        if ticket.state == 'cancel_pending':
            super(helpdesk_ticket,self).write(cr, uid, ids, {'state':'open'}, context=context)            
            #Create Conversation        
            values = {}
            values['ticket_id'] = ids[0]
            values['message_date'] = datetime.now()
            values['description'] = "Ticket Cancel Pending"
            conversation_id = self.pool.get('helpdesk.conversation').create(cr, uid, values, context=context)                    
        
        if ticket.state == 'cancel':
            super(helpdesk_ticket,self).write(cr, uid, ids, {'state':'open'}, context=context)            
            #Create Conversation        
            values = {}
            values['ticket_id'] = ids[0]
            values['message_date'] = datetime.now()
            values['description'] = "Ticket was re-opened"
            conversation_id = self.pool.get('helpdesk.conversation').create(cr, uid, values, context=context)                    
    
        if ticket.state == 'request_response':
            #Approved            
            if ticket.approved_state == '2':
                super(helpdesk_ticket,self).write(cr, uid, ids, {'approved_state':'2','approved_date':datetime.now(),'state':'done'}, context=context)            
                conversation_data = {            
                    'ticket_id': ticket.id,
                    'message_date': datetime.now(),
                    #'email_from' : values['employee'],
                    'name': 'Ticket Approved',
                    'description': 'Ticket Approved',        
                    'inbound': False,
                }                        
                conversation_id = self.pool.get('helpdesk.conversation').create(cr, uid, conversation_data, context=context)                            
                _logger.info("Save Conversation")
                
                email_data = {}
                email_data['start_logger'] = 'Start Email Ticket Approval Notification'
                email_data['email_from'] = helpdesk_email
                email_data['email_to'] = employee.work_email
                email_data['subject'] = "<" + ticket.trackid + "> " + ticket.name + " (Approved)"
                serverUrl = 'http://' + reportserver + ':' + reportserverport + '/jasperserver'
                j_username = 'itms_operator'
                j_password = 'itms123'
                ParentFolderUri = '/itms'
                reportUnit = '/itms/itsr_form'
                url = serverUrl + '/flow.html?_flowId=viewReportFlow&standAlone=true&_flowId=viewReportFlow&ParentFolderUri=' + ParentFolderUri + '&reportUnit=' + reportUnit + '&TICKET_ID=' + str(ticket.id) + '&APPROVED_STATE=2&decorate=no&j_username=' + j_username + '&j_password=' + j_password + '&output=pdf'

                msg = '<br/>'.join([
                    'Dear ' + employee.name,
                    '',
                    '',
                    'Your ticket with track id : ' + ticket.trackid + ' already approved by IT Manager',
                    'Please download ITSR Form and sign by Department Head',
                    '',
                    '',
                    '<a href="' + url +  '">Download ITSR</a>',
                    '',
                    '',
                    '',
                    'Regards',
                    '',
                    'IT Helpdesk'
                ])        
                email_data['body_html'] = msg
                email_data['end_logger'] = 'End Email Ticket Approval Notification'
                self._send_email_notification(cr, uid, email_data, context=context)                                 
            #Rejected
            if ticket.approved_state == '3':
                super(helpdesk_ticket,self).write(cr, uid, ids, {'approved_state':'3','approved_date':datetime.now(),'state':'open'}, context=context)            
                values = {}
                values['ticket_id'] = ticket.id
                values['message_date'] = datetime.now()
                values['description'] = "Ticket Rejected by IT Manager"                
                conversation_id = self.pool.get('helpdesk.conversation').create(cr, uid, values, context=context)

                
        if ticket.state == 'done':
            values = {}
            values['ticket_id'] = ticket.id
            values['message_date'] = datetime.now()
            values['description'] = "Ticket Closed"
            conversation_id = self.pool.get('helpdesk.conversation').create(cr, uid, values, context=context)

            #Send Email Notification
            email_data = {}
            email_data['start_logger'] = 'Start Email Ticket Closed Notification'
            email_data['email_from'] = helpdesk_email
            email_data['email_to'] = employee.work_email
            email_data['subject'] = "<" + ticket.trackid + "> " + ticket.name + " (Closed)"
            email_data['body_html'] = "Ticket track id : " + ticket.trackid + " was closed"        
            email_data['end_logger'] = 'End Email Ticket Closed Notification'
            self._send_email_notification(cr, uid, email_data, context=context)   
            
        return result    
    
helpdesk_ticket()

class helpdesk_approve_reject(osv.osv_memory):
    _name = "helpdesk.approved"
    _description = "Helpdesk Approved" 
    
    def approve_reject(self, cr, uid, ids, context=None):                
        params = self.browse(cr, uid, ids, context=context)
        param = params[0]           
        ticket_id = context.get('ticket_id',False)
        ticket = {}            
        ticket['approved_state'] = param.approved_state
        ticket['approved_comment'] = param.approved_comment if param.approved_comment else ''                
        ticket['state'] = 'request_response'                
        self.pool.get('helpdesk.ticket').write(cr, uid, [ticket_id], ticket, context=context)                                                
        return True
    
    _columns = {
        'ticket_id': fields.integer('Ticket'),
        'approved_state': fields.selection([('2', 'Approved'),('3', 'Rejected')],'Approved Status'),
        'approved_comment': fields.text('Comment')
    }    
    
    _defaults = {        
        'approved_state': lambda *a: '2',
    }
    
helpdesk_approve_reject()