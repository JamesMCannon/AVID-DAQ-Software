from logging.handlers import SMTPHandler

class EmailHandler(SMTPHandler):
    """
    A handler class which sends an SMTP email for each logging event.
    """
    def __init__(self, sitename, mailhost, fromaddr, toaddrs, subject, credentials, secure, log_file_name):
        
        # Init superclass
        super(EmailHandler, self).__init__(mailhost, fromaddr, toaddrs, subject, credentials, secure)
        
        # Our extra bits
        self.sitename = sitename
        self.logfile = log_file_name
        self.secure = ()
    
    def getSubject(self, record):
        """
        Determine the subject for the email.

        If you want to specify a subject line which is record-dependent,
        override this method.
        """
        
        subject = "%s (%s)" %(self.subject, self.sitename)
        return subject

    def emit(self, record):
        """
        Emit a record.

        Format the record and send it to the specified addressees.
        """
        try:
            import smtplib
            from email.utils import formatdate
            from email.MIMEMultipart import MIMEMultipart
            from email.MIMEBase import MIMEBase
            from email import Encoders

            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP(self.mailhost, port)
            
            msg = MIMEMultipart()
            msg['Subject'] = self.getSubject(record) 
            msg['From'] = self.fromaddr
            msg['To'] = ", ".join(self.toaddrs)
            msg['Date'] = formatdate()
            
            # part = MIMEBase('application', "octet-stream")
            # part.set_payload(open(self.logfile, "rb").read())
            # Encoders.encode_base64(part)
            # part.add_header('Content-Disposition', 'attachment; filename="text.txt"')

            # msg.attach(part)
            
            # msg.attach(self.format(record))
            
            msg = self.format(record)
            msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\nDate: %s\r\n\r\n%s" % (
                           self.fromaddr,
                           ",".join(self.toaddrs),
                           self.getSubject(record),
                           formatdate(), msg)
                            
            if self.username:
                if self.secure is not None:
                    smtp.ehlo()
                    smtp.starttls(*self.secure)
                    smtp.ehlo()
                smtp.login(self.username, self.password)
                
            smtp.sendmail(self.fromaddr, self.toaddrs, msg)
            smtp.quit()
            
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)