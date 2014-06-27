from imaplib import IMAP4
from imaplib import IMAP4_SSL
from poplib import POP3
from poplib import POP3_SSL

import base64
import datetime
import dateutil
import email
from email.header import decode_header
import logging
import pytz
import re
import time
import xmlrpclib
from email.message import Message

import string


import logging

_logger = logging.getLogger(__name__)

def decode(text):
    """Returns unicode() string conversion of the the given encoded smtp header text"""
    if text:
        text = decode_header(text.replace('\r', ''))
        return ''.join([tools.ustr(x[0], x[1]) for x in text])
    
def connectpop3server():
    pop3server = 'localhost'
    port = '110'
    user = 'helpdesk@jakc.com'
    password = 'P@ssw0rd'
    connection = POP3(pop3server, int(port))        
    connection.user(user)
    connection.pass_(password)
    return connection

def fetchemail():
    try:
        pop_server = connectpop3server()
        (numMsgs, totalSize) = pop_server.stat()
        pop_server.list()
        for num in range(1, numMsgs + 1):
            (header, msges, octets) = pop_server.retr(num)
            msg = '\n'.join(msges)          
            print msg
            res_id = message_process(msg)                
            #pop_server.dele(num)                
    except:
        print "Error"
        
def message_process(message):       
    try:
     
        # extract message bytes - we are forced to pass the message as binary because
        # we don't know its encoding until we parse its headers and hence can't
        # convert it to utf-8 for transport between the mailgate script and here.
        if isinstance(message, xmlrpclib.Binary):
            message = str(message.data)
        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        if isinstance(message, unicode):
            message = message.encode('utf-8')
            
        msg_txt = email.message_from_string(message)

        # parse the message, verify we are not in a loop by checking message_id is not duplicated
        msg = message_parse(msg_txt)

        #print "Message : " + msg
        #if msg.get('message_id'):   # should always be True as message_parse generate one if missing
            #new_msg_id = model_pool.message_post(cr, uid, [thread_id], context=context, subtype='mail.mt_comment', **msg)
        return True
    except:
        print "Error Message Process"
        return False

def message_parse(message):
    try:    
        msg_dict = {}

        if not isinstance(message, Message):
            if isinstance(message, unicode):
                # Warning: message_from_string doesn't always work correctly on unicode,
                # we must use utf-8 strings here :-(
                message = message.encode('utf-8')
            message = email.message_from_string(message)

        message_id = message['message-id']
        if not message_id:
            # Very unusual situation, be we should be fault-tolerant here
            message_id = "<%s@localhost>" % time.time()
            print "Generate Message ID"

        msg_dict['message_id'] = message_id

        if message.get('Subject'):
            msg_dict['subject'] = message.get('Subject')

        # Envelope fields not stored in mail.message but made available for message_new()
        msg_dict['from'] = message.get('from')
        msg_dict['to'] = message.get('to')
        msg_dict['cc'] = message.get('cc')

        msg_dict['email_from'] = message.get('from')

        if message.get('Date'):
            try:
                date_hdr = message.get('Date')
                parsed_date = dateutil.parser.parse(date_hdr, fuzzy=True)
                if parsed_date.utcoffset() is None:
                    # naive datetime, so we arbitrarily decide to make it
                    # UTC, there's no better choice. Should not happen,
                    # as RFC2822 requires timezone offset in Date headers.
                    stored_date = parsed_date.replace(tzinfo=pytz.utc)
                else:
                    stored_date = parsed_date.astimezone(tz=pytz.utc)
            except Exception:
                print "Error Message Date"
                stored_date = datetime.datetime.now()
            msg_dict['date'] = stored_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)

        #msg_dict['body'], msg_dict['attachments'] = self._message_extract_payload(message)
        return msg_dict        
    except:
        print "Error Message Parse"
    
def _message_extract_payload(message):
    try:            
        """Extract body as HTML and attachments from the mail message"""
        attachments = []
        body = u''
        if save_original:
            attachments.append(('original_email.eml', message.as_string()))

        if not message.is_multipart() or 'text/' in message.get('content-type', ''):
            encoding = message.get_content_charset()
            body = message.get_payload(decode=True)
            body = tools.ustr(body, encoding, errors='replace')
            if message.get_content_type() == 'text/plain':
                # text/plain -> <pre/>
                body = tools.append_content_to_html(u'', body, preserve=True)
        else:
            alternative = (message.get_content_type() == 'multipart/alternative')
            for part in message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue  # skip container
                filename = part.get_filename()  # None if normal part
                encoding = part.get_content_charset()  # None if attachment
                # 1) Explicit Attachments -> attachments
                if filename or part.get('content-disposition', '').strip().startswith('attachment'):
                    attachments.append((filename or 'attachment', part.get_payload(decode=True)))
                    continue
                # 2) text/plain -> <pre/>
                if part.get_content_type() == 'text/plain' and (not alternative or not body):
                    body = tools.append_content_to_html(body, tools.ustr(part.get_payload(decode=True),
                                                                         encoding, errors='replace'), preserve=True)
                # 3) text/html -> raw
                elif part.get_content_type() == 'text/html':
                    html = tools.ustr(part.get_payload(decode=True), encoding, errors='replace')
                    if alternative:
                        body = html
                    else:
                        body = tools.append_content_to_html(body, html, plaintext=False)
                # 4) Anything else -> attachment
                else:
                    attachments.append((filename or 'attachment', part.get_payload(decode=True)))
        return body, attachments    
    except:
        print "Error Payload"
        return body, attachments    
    
    
try:
    fetchemail()    
except:
    print "Error Connected"
