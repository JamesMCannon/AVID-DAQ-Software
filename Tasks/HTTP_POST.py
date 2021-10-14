"""
HTTP_POST module
"""

import urllib2


# requires poster module (http://pypi.python.org/pypi/poster/)
from poster.encode import multipart_encode
from poster.streaminghttp import register_openers

__all__ = ['HTTP_POST']

from Task import *

try:
    import wx
    from VLFPanel import VLFPanel

    class GUIPanel(VLFPanel):
        def __init__(self, parent):
            VLFPanel.__init__(self, parent, "HTTP_POST")
            self.widgets = {
                'Directory':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'Period':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Seconds]'),
                'Hostname':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
    ##            'Prefix':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),''),
            }
            self.addWidgets()

except:
    print "WARNING: CAN'T IMPORT WX AND/OR VLFPanel"

class HTTP_POST(Task):

###############################################################################

    def __init__(self, config, logger, tasknum):


        Task.__init__(self, config, logger, tasknum)

        self.randInterval = 60
        
        self.taskname = 'T%d.HTTP_POST' % tasknum

        self.directory = config.GetStrElemVal('Directory')
        
        self.logger.info("Setting Directory: %s" % self.directory)
        
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)

        self.interval = config.GetIntElemVal('Period',3600)
        self.hostname = config.GetStrElemVal('Hostname')
        self.prefix = config.GetStrElemVal('Prefix','')

        self.exclude_list = ['.mau']


###############################################################################

    def DoTask(self):

        self.logger.debug('Scanning for new files...')

        #get a list of all files in the local directory, sorted by latest file first
        #file_list = sorted(os.listdir(self.directory), key=os.path.getctime, reverse=True)
        file_list = os.listdir(self.directory)

        #we'll assume the local directory contains only files, so filter out all directories from the list
        #this simplifies things by removing the need to do recursive directory copies
        file_list = filter(lambda x: not os.path.isdir(os.path.join(self.directory, x)), file_list)

        # Maybe should delete all other files > 100?
        
        #strip out certain extensions
        for extension in self.exclude_list:
            if not self.running:
                break   #don't wait for everything to copy when software called to exit
            file_list = filter(lambda x: not x.endswith(extension), file_list)

        if len(file_list)==0:
            self.logger.debug('No new files')
            return

        # Prepare the HTTP handlers
        register_openers()

        #transfer and then delete each file in the local FTP directory
        for filename in file_list:
            if not self.running:
                break #don't wait for everything to POST when software called to exit

            try:

                old_file_path = os.path.join(self.directory, filename)
                file_path = os.path.join(self.directory, self.prefix + filename)
                os.rename(old_file_path,file_path)
                self.logger.info('Sending %s using POST' % file_path)

                # Start the multipart/form-data encoding of the file "test_image.jpg"
                # "image1" is the name of the parameter, which is normally set
                # via the "name" parameter of the HTML <input> tag.
                # headers contains the necessary Content-Type and Content-Length
                # datagen is a generator object that yields the encoded parameters
                f = open(file_path, "rb")
                datagen, headers = multipart_encode({"file": f})

                # Create the Request object
                request = urllib2.Request(self.hostname, datagen, headers)

                # Do request, record response

                response = urllib2.urlopen(request)
                f.close()
                os.remove(file_path)

            # Check for exceptions
            except urllib2.URLError:
                self.logger.exception('urllib exception.')
                """
                except urllib2.URLError, e:
                    if hasattr(e, 'reason'):
                        self.logger.debug('Failed to reach server.')
                        self.logger.debug('Reason: %s', e.reason)
                    elif hasattr(e, 'code'):
                        self.logger.debug('The server couldn\'t fultill the request.')
                        self.logger.debug('Error code: %s', e.code)
                        self.logger.debug('Error Header: %s', e.headers)
                """
                ###added raise
                return
            except Exception:
                self.logger.exception('Filename: %s' % filename)
                ###added raise
                return

###############################################################################

#---------
#Unit Test
#---------
if __name__ == '__main__':

    from xml.dom.minidom import parseString
    import numpy
    from datetime import datetime, timedelta
    import time
    import os

    config  = """
        <Task module = "HTTP_POST">
            <Directory>POST</Directory>
            <Period>10</Period>
            <Hostname>http://vlf-engineering.stanford.edu/uploader/test/upload_file.php</Hostname>
        </Task>
        """

    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)

    # define a Handler which writes DEBUG messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter('%(name)-2s: %(levelname)s %(message)-60s'))
    logger.addHandler(console)

    http_post = HTTP_POST(parseString(config),logger)

    http_post.Start()
    time.sleep(5)
    http_post.Stop()
