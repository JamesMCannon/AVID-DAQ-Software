"""
# IndexWriter maintains database of XML files, the entries of which contain information
# on each data file that has been written.  The IndexWriter must immediately follow a MatFileWriter
# in the PostProcessor sequence.
#
# Each time the MatFileWriter opens a new data file, IndexWriter appends a new entry to the currently opened
# index XML file.  Each entry contains the .Mat filename, start time, duration in seconds, and sample rate.
#
# The current index XML file is periodically closed and a new one is opened.  This is done for several reasons.
# First, each index file will be small in size, thus allowing us to use minidom when parsing without using too much
# memory.  Second, it will be easier to delete old data entries, because data will likely have a finite lifetime in order
# to save hard disk space.
"""


from xml.dom.minidom import parse, Document
import os,os.path, sys
sys.path.append(['..'])
from datetime import datetime, timedelta

__all__ = ['IndexWriter']

try:
	import wx
	from VLFPanel import VLFPanel
	class GUIPanel(VLFPanel):
		def __init__(self, parent):
			VLFPanel.__init__(self, parent, "IndexWriter")
			self.widgets = {
			'FilenameRoot':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
			'Duration':wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),
			}
			self.addWidgets()
except:
	print "WARNING: CAN'T IMPORT WX AND/OR VLFPanel"


class IndexWriter:

	def __init__(self, config):

		#the name of the index file to write to
		self.fileNameRoot=str(config.getElementsByTagName('FilenameRoot')[0].firstChild.data)
		(head,tail) = os.path.split(self.fileNameRoot)
		if len(head)>0:
			if not os.path.isdir(head):
				os.makedirs(head)

		#the duration of the index file in hours
		self.duration=int(config.getElementsByTagName('Duration')[0].firstChild.data)

		#keep a delayed copy of the data file name so that
		#we can detect when a new file has been opened
		self.daqFile = None
		self.daqFilePrev = None

		#the timestamp for the last index file created
		self.fileStart = None
		self.fileName = None
        
        #self.logger = logger

	def Process(self, data):

		#check to see if a new entry file should be opened
		#if so, create a skeleton xml file
		if(self.TimeToStartNewFile(data[1])):
			self.fileName = "%s_%s.xml" % (self.fileNameRoot, data[1].strftime("%Y_%m_%d_%H_%M_%S"))
			self.fileStart = data[1]
			fid=open(self.fileName,'w')
			fid.write('<?xml version="1.0"?>\n\n<Index>\n')
			fid.write('')
			fid.write('</Index>')
			fid.close()

		self.daqFilePrev = self.daqFile
		self.daqFile = data[0]

		#if a new data file was opened, add an index entry for it
		if((self.daqFile != self.daqFilePrev)):
			self.AppendEntry(data)

		return 0

	def AppendEntry(self, data):
		fid=open(self.fileName,'r+')
		fid.seek(-8,2) #seek to the end of the file

		#look for the closing index tag
		while(fid.read() != '</Index>'):
			fid.seek(-9,2)

		#when we've found it, skip past it and begin overwriting it
		fid.seek(-9,2)

		fid.write('\n   <Entry>\n')

		#write the file name
		fid.write('      <Filename>%s</Filename>\n'%(self.daqFile))

		#write the start time
		fid.write('      <StartYear>%s</StartYear>\n'%(data[1].year))
		fid.write('      <StartMonth>%s</StartMonth>\n'%(data[1].month))
		fid.write('      <StartDay>%s</StartDay>\n'%(data[1].day))
		fid.write('      <StartHour>%s</StartHour>\n'%(data[1].hour))
		fid.write('      <StartMinute>%s</StartMinute>\n'%(data[1].minute))
		fid.write('      <StartSecond>%s</StartSecond>\n'%(data[1].second))

		#write the duration
		fid.write('      <Duration>%d</Duration>\n'%(data[2]))

		#write the sample rate
		fid.write('      <SampleRate>%d</SampleRate>\n'%(data[3]))

		fid.write('   </Entry>\n')
		fid.write('</Index>')

		#close the open index file
		fid.close()


	def TimeToStartNewFile(self, timestamp):
		if(self.fileStart == None):
			return True
		if(((timestamp - self.fileStart).seconds) % (self.duration*3600))==0:
##			print (timestamp - self.fileStart).seconds  #Patrick: This was printing out once per hour
			return True
		if((timestamp - self.fileStart) >= timedelta(hours=self.duration)):
			return False
		return False

