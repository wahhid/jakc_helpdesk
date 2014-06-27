from imaplib import IMAP4
from imaplib import IMAP4_SSL
from poplib import POP3
from poplib import POP3_SSL

import sys, os, re, StringIO
import email, mimetypes

invalid_chars_in_filename='<>:"/\\|?*\%\''+reduce(lambda x,y:x+chr(y), range(32), '')
invalid_windows_name='CON PRN AUX NUL COM1 COM2 COM3 COM4 COM5 COM6 COM7 COM8 COM9 LPT1 LPT2 LPT3 LPT4 LPT5 LPT6 LPT7 LPT8 LPT9'.split()

# email address REGEX matching the RFC 2822 spec from perlfaq9
#    my $atom       = qr{[a-zA-Z0-9_!#\$\%&'*+/=?\^`{}~|\-]+};
#    my $dot_atom   = qr{$atom(?:\.$atom)*};
#    my $quoted     = qr{"(?:\\[^\r\n]|[^\\"])*"};
#    my $local      = qr{(?:$dot_atom|$quoted)};
#    my $domain_lit = qr{\[(?:\\\S|[\x21-\x5a\x5e-\x7e])*\]};
#    my $domain     = qr{(?:$dot_atom|$domain_lit)};
#    my $addr_spec  = qr{$local\@$domain};
# 
# Python's translation

atom_rfc2822=r"[a-zA-Z0-9_!#\$\%&'*+/=?\^`{}~|\-]+"
atom_posfix_restricted=r"[a-zA-Z0-9_#\$&'*+/=?\^`{}~|\-]+" # without '!' and '%'
atom=atom_rfc2822
dot_atom=atom  +  r"(?:\."  +  atom  +  ")*"
quoted=r'"(?:\\[^\r\n]|[^\\"])*"'
local="(?:"  +  dot_atom  +  "|"  +  quoted  +  ")"
domain_lit=r"\[(?:\\\S|[\x21-\x5a\x5e-\x7e])*\]"
domain="(?:"  +  dot_atom  +  "|"  +  domain_lit  +  ")"
addr_spec=local  +  "\@"  +  domain

email_address_re=re.compile('^'+addr_spec+'$')

class Attachment:
    def __init__(self, part, filename=None, type=None, payload=None, charset=None, content_id=None, description=None, disposition=None, sanitized_filename=None, is_body=None):
        self.part=part          # original python part
        self.filename=filename  # filename in unicode (if any) 
        self.type=type          # the mime-type
        self.payload=payload    # the MIME decoded content 
        self.charset=charset    # the charset (if any) 
        self.description=description    # if any 
        self.disposition=disposition    # 'inline', 'attachment' or None
        self.sanitized_filename=sanitized_filename # cleanup your filename here (TODO)  
        self.is_body=is_body        # usually in (None, 'text/plain' or 'text/html')
        self.content_id=content_id  # if any
        if self.content_id:
            # strip '<>' to ease searche and replace in "root" content (TODO) 
            if self.content_id.startswith('<') and self.content_id.endswith('>'):
                self.content_id=self.content_id[1:-1]

def getmailheader(header_text, default="ascii"):
    """Decode header_text if needed"""
    try:
        headers=email.Header.decode_header(header_text)
    except email.Errors.HeaderParseError:
        # This already append in email.base64mime.decode()
        # instead return a sanitized ascii string
        # this faile '=?UTF-8?B?15HXmdeh15jXqNeVINeY15DXpteUINeTJ9eV16jXlSDXkdeg15XXldeUINem15PXpywg15TXptei16bXldei15nXnSDXqdecINek15zXmdeZ?==?UTF-8?B?157XldeR15nXnCwg157Xldek16Ig157Xl9eV15wg15HXodeV15bXnyDXk9ec15DXnCDXldeh15gg157Xl9eR16rXldeqINep15wg15HXmdeQ?==?UTF-8?B?15zXmNeZ?='
        return header_text.encode('ascii', 'replace').decode('ascii')
    else:
        for i, (text, charset) in enumerate(headers):
            try:
                headers[i]=unicode(text, charset or default, errors='replace')
            except LookupError:
                # if the charset is unknown, force default 
                headers[i]=unicode(text, default, errors='replace')
        return u"".join(headers)

def getmailaddresses(msg, name):
    """retrieve addresses from header, 'name' supposed to be from, to,  ..."""
    addrs=email.utils.getaddresses(msg.get_all(name, []))
    for i, (name, addr) in enumerate(addrs):
        if not name and addr:
            # only one string! Is it the address or is it the name ?
            # use the same for both and see later
            name=addr
            
        try:
            # address must be ascii only
            addr=addr.encode('ascii')
        except UnicodeError:
            addr=''
        else:
            # address must match address regex
            if not email_address_re.match(addr):
                addr=''
        addrs[i]=(getmailheader(name), addr)
    return addrs

def get_filename(part):
    """Many mail user agents send attachments with the filename in 
    the 'name' parameter of the 'content-type' header instead 
    of in the 'filename' parameter of the 'content-disposition' header.
    """
    filename=part.get_param('filename', None, 'content-disposition')
    if not filename:
        filename=part.get_param('name', None) # default is 'content-type'
        
    if filename:
        # RFC 2231 must be used to encode parameters inside MIME header
        filename=email.Utils.collapse_rfc2231_value(filename).strip()

    if filename and isinstance(filename, str):
        # But a lot of MUA erroneously use RFC 2047 instead of RFC 2231
        # in fact anybody miss use RFC2047 here !!!
        filename=getmailheader(filename)
        
    return filename

def _search_message_bodies(bodies, part):
    """recursive search of the multiple version of the 'message' inside 
    the the message structure of the email, used by search_message_bodies()"""
    
    type=part.get_content_type()
    if type.startswith('multipart/'):
        # explore only True 'multipart/*' 
        # because 'messages/rfc822' are also python 'multipart' 
        if type=='multipart/related':
            # the first part or the one pointed by start 
            start=part.get_param('start', None)
            related_type=part.get_param('type', None)
            for i, subpart in enumerate(part.get_payload()):
                if (not start and i==0) or (start and start==subpart.get('Content-Id')):
                    _search_message_bodies(bodies, subpart)
                    return
        elif type=='multipart/alternative':
            # all parts are candidates and latest is best
            for subpart in part.get_payload():
                _search_message_bodies(bodies, subpart)
        elif type in ('multipart/report',  'multipart/signed'):
            # only the first part is candidate
            try:
                subpart=part.get_payload()[0]
            except IndexError:
                return
            else:
                _search_message_bodies(bodies, subpart)
                return

        elif type=='multipart/signed':
            # cannot handle this
            return
            
        else: 
            # unknown types must be handled as 'multipart/mixed'
            # This is the peace of code could probably be improved, I use a heuristic : 
            # - if not already found, use first valid non 'attachment' parts found
            for subpart in part.get_payload():
                tmp_bodies=dict()
                _search_message_bodies(tmp_bodies, subpart)
                for k, v in tmp_bodies.iteritems():
                    if not subpart.get_param('attachment', None, 'content-disposition')=='':
                        # if not an attachment, initiate value if not already found
                        bodies.setdefault(k, v)
            return
    else:
        bodies[part.get_content_type().lower()]=part
        return
    
    return

def search_message_bodies(mail):
    """search message content into a mail"""
    bodies=dict()
    _search_message_bodies(bodies, mail)
    return bodies

def get_mail_contents(msg):
    """split an email in a list of attachments"""

    attachments=[]

    # retrieve messages of the email
    bodies=search_message_bodies(msg)
    # reverse bodies dict
    parts=dict((v,k) for k, v in bodies.iteritems())

    # organize the stack to handle deep first search
    stack=[ msg, ]
    while stack:
        part=stack.pop(0)
        type=part.get_content_type()
        if type.startswith('message/'): 
            # ('message/delivery-status', 'message/rfc822', 'message/disposition-notification'):
            # I don't want to explore the tree deeper her and just save source using msg.as_string()
            # but I don't use msg.as_string() because I want to use mangle_from_=False 
            from email.Generator import Generator
            fp = StringIO.StringIO()
            g = Generator(fp, mangle_from_=False)
            g.flatten(part, unixfrom=False)
            payload=fp.getvalue()
            filename='mail.eml'
            attachments.append(Attachment(part, filename=filename, type=type, payload=payload, charset=part.get_param('charset'), description=part.get('Content-Description')))
        elif part.is_multipart():
            # insert new parts at the beginning of the stack (deep first search)
            stack[:0]=part.get_payload()
        else:
            payload=part.get_payload(decode=True)
            charset=part.get_param('charset')
            filename=get_filename(part)
                
            disposition=None
            if part.get_param('inline', None, 'content-disposition')=='':
                disposition='inline'
            elif part.get_param('attachment', None, 'content-disposition')=='':
                disposition='attachment'
                
            attachments.append(Attachment(part, filename=filename, type=type, payload=payload, charset=charset, content_id=part.get('Content-Id'), description=part.get('Content-Description'), disposition=disposition, is_body=parts.get(part)))

    return attachments

def decode_text(payload, charset, default_charset):
    if charset:
        try: 
            return payload.decode(charset), charset
        except UnicodeError:
            pass

    if default_charset and default_charset!='auto':
        try: 
            return payload.decode(default_charset), default_charset
        except UnicodeError:
            pass
        
    for chset in [ 'ascii', 'utf-8', 'utf-16', 'windows-1252', 'cp850' ]:
        try: 
            return payload.decode(chset), chset
        except UnicodeError:
            pass

    return payload, None

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
        
if __name__ == "__main__":

    raw="""Return-Path: whidayat@jakc.com
Received: from wahhidPC (localhost [127.0.0.1])
        by WAHHID-PC
        ; Wed, 18 Jun 2014 21:31:33 +0700
Message-ID: <7A97266BA8EE4F56B572AFB119CCF85A@wahhidPC>
From: "Wahyu Hidayat" <whidayat@jakc.com>
To: <helpdesk@jakc.com>
Subject: Testing 50
Date: Wed, 18 Jun 2014 21:31:33 +0700
MIME-Version: 1.0
Content-Type: multipart/alternative;
        boundary="----=_NextPart_000_0041_01CF8B3C.AD3257D0"
X-Priority: 3
X-MSMail-Priority: Normal
Importance: Normal
X-Mailer: Microsoft Windows Live Mail 15.4.3538.513
X-MimeOLE: Produced By Microsoft MimeOLE V15.4.3538.513

This is a multi-part message in MIME format.

------=_NextPart_000_0041_01CF8B3C.AD3257D0
Content-Type: text/plain;
        charset="iso-8859-1"
Content-Transfer-Encoding: quoted-printable

Testing 50
------=_NextPart_000_0041_01CF8B3C.AD3257D0
Content-Type: text/html;
        charset="iso-8859-1"
Content-Transfer-Encoding: quoted-printable

<HTML><HEAD></HEAD>
<BODY dir=3Dltr>
<DIV dir=3Dltr>
<DIV style=3D"FONT-SIZE: 12pt; FONT-FAMILY: 'Calibri'; COLOR: #000000">
<DIV>Testing 50</DIV></DIV></DIV></BODY></HTML>

------=_NextPart_000_0041_01CF8B3C.AD3257D0--
"""

    if len(sys.argv)>1:
        raw=open(sys.argv[1]).read()
        
    pop_server = connectpop3server()
    (numMsgs, totalSize) = pop_server.stat()
    pop_server.list()
    for num in range(1, numMsgs + 1):
        (header, msges, octets) = pop_server.retr(num)
        raw = '\n'.join(msges)                      
        msg=email.message_from_string(raw)
        attachments=get_mail_contents(msg)

        subject=getmailheader(msg.get('Subject', ''))
        from_=getmailaddresses(msg, 'from')
        from_=('', '') if not from_ else from_[0]
        tos=getmailaddresses(msg, 'to')

        print 'Subject: %r' % subject
        print 'From: %r' % (from_, )
        print 'To: %r' % (tos, )

        for attach in attachments:
            # dont forget to be careful to sanitize 'filename' and be carefull
            # for filename collision, to before to save :
            print '\tfilename=%r is_body=%s type=%s charset=%s desc=%s size=%d' % (attach.filename, attach.is_body, attach.type, attach.charset, attach.description, 0 if attach.payload==None else len(attach.payload))

            if attach.is_body=='text/plain':
                # print first 3 lines
                payload, used_charset=decode_text(attach.payload, attach.charset, 'auto') 
                for line in payload.split('\n')[:3]:
                    # be careful console can be unable to display unicode characters
                    if line:
                        print '\t\t', line
                        
        pop_server.dele(num)   
        print "Deleted"