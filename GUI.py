# -*- coding: <<encoding>> -*-
#-------------------------------------------------------------------------------
#   <<project>>
#   <<created:10/05/08>>
#
#-------------------------------------------------------------------------------
import os
import wx, wx.html
import xml.etree.cElementTree as ET
# if os.name=='nt':
#     from elementtree.ElementTree import Element, SubElement, ElementTree
# else:
from xml.etree.ElementTree import Element, SubElement, ElementTree

from VLFPanel import VLFPanel
import xml.dom.minidom
import sys

import string
from sys import stdout, exc_info, argv
import traceback
from datetime import datetime

_ICON_PATH='./icons'

ID_NEW = 1
ID_SAVE = 2
ID_OPEN = 3
ID_LB = 4
MAX_ID = 4

ID_LOCK = 100

__ver__ = '2012.0615'

#main window
class DAQFrame(wx.Frame):
    def __init__(self, xmlPath=None):
        wx.Frame.__init__(self, None, title="Stanford University VLF", size=wx.Size(880,600), style= wx.SYSTEM_MENU | wx.CAPTION |  wx.CLOSE_BOX)
        self.Centre()
        self.panel = wx.Panel(self, wx.ID_ANY)
        self.xmlPath = xmlPath
        self.start_file_save = None
        self.mainNodes = ['DaqCard', 'GpsClock', 'StationSettings', 'Logger', 'PostProcessorTree', 'TaskManagerSettings', 'Schedule']
        self.locked = False
        self.detailPanel = False
        self.d = {}
        self.numChannels = 0
        self.root = None

        # Main Sizer with horizontal/vertical padding of 5
        self.gbs = wx.GridBagSizer(hgap=5, vgap=5)

        ###########
        # TOOLBAR #
        ###########
        self.tb = self.CreateToolBar(wx.TB_HORIZONTAL | wx.NO_BORDER | wx.TB_FLAT)
        self.tb.AddLabelTool(ID_NEW, "New", wx.Bitmap('%s/filenew.png' % _ICON_PATH), shortHelp="New", longHelp="Long help for 'New'")
        self.Bind(wx.EVT_TOOL, self.loadNewTree, id=ID_NEW)

        self.tb.AddLabelTool(ID_SAVE, "Save", wx.Bitmap('%s/filesave.png' % _ICON_PATH), shortHelp="Save", longHelp="Long help for 'Save'")
        self.Bind(wx.EVT_TOOL, self.writeToXml, id=ID_SAVE)

        self.tb.AddLabelTool(ID_OPEN, "Open", wx.Bitmap('%s/fileopen.png' % _ICON_PATH), shortHelp="Open", longHelp="Long help for 'Open'")
        self.Bind(wx.EVT_TOOL, self.readFromXml, id=ID_OPEN)
        self.tb.AddSeparator()

        self.tb.AddLabelTool(ID_LOCK, "Lock", wx.Bitmap('%s/lock.png' % _ICON_PATH), shortHelp="Lock", longHelp="Long help for 'Lock'")
        self.Bind(wx.EVT_TOOL, self.Lock, id=ID_LOCK)

        self.tb.Realize()

        ###############
        # MODULE TREE #
        ###############
        #self.tree = wx.TreeCtrl(self.panel, wx.ID_ANY, pos=wx.DefaultPosition, size=(240,370),style=wx.TR_DEFAULT_STYLE)
        self.tree = wx.TreeCtrl(self.panel, wx.ID_ANY, pos=wx.DefaultPosition, size=(240,490),style=wx.TR_DEFAULT_STYLE)
        self.gbs.Add(self.tree,pos=(0,0),span=(10,3))
        self.Bind(wx.EVT_TREE_SEL_CHANGED,self.onTreeSelection, self.tree)

        ###########
        # BUTTONS #
        ###########
        self.addButton = wx.Button(self.panel, 10, "Add")
        self.Bind(wx.EVT_BUTTON, self.onAddButtonClick, self.addButton)
        self.removeButton = wx.Button(self.panel, 30, "Remove")
        self.Bind(wx.EVT_BUTTON, self.onRemoveButtonClick, self.removeButton)
        self.gbs.Add(self.addButton,pos=(10,0))
        self.gbs.Add(self.removeButton,pos=(10,1))
        self.addButton.Enable(False)
        self.removeButton.Enable(False)

        # Blank Text - Used to maintain minimum size of box
        self.gbs.Add(wx.StaticText(self.panel, wx.ID_ANY, " "),pos=(11,28))

        # Initialization Greeting Panel
        self.detailPanel = GreetingPanel(self.panel)
        self.gbs.Add(self.detailPanel, pos=(0,4), span=(10,6))

        box = wx.BoxSizer()
        box.Add(self.gbs,0,wx.ALL,10)
        self.panel.SetSizerAndFit(box)
        self.SetClientSize(self.panel.GetSize())
        icon1 = wx.Icon('%s/test.ico' % _ICON_PATH, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon1)

        self.mainPanels = [DAQCardPanel(self), AuxiliaryInfoPanel(self.panel),StationSettingsPanel(self.panel), LoggerPanel(self.panel),\
                            BasicPanel(self.panel,'PostProcessors','Configure the Post Processing units after data acquisition\n\nUse the Add button to add Post Processing sequences'),\
                            BasicPanel(self.panel,'TaskManagerSettings','\n\nUse the Add button to add Tasks'),\
                            SchedulePanel(self.panel)]

        if self.xmlPath is None:
            self.start_file_save = '../DaqSettings.xml'
            self.loadNewTree(None)
        else:
            self.readFromXml(None)

    def changeDetailPanel(self, panel):
        if panel is self.detailPanel:
            return
        if (self.detailPanel):
            self.gbs.Hide(self.detailPanel)
            self.gbs.Detach(self.detailPanel)
        self.detailPanel = panel
        self.gbs.Add(self.detailPanel, pos=(0,4), span=(10,6))
        self.gbs.Show(self.detailPanel)
        self.gbs.Layout()

    def onAddButtonClick(self, event):
        if self.tree.GetItemText(self.selected_item) == 'PostProcessorTree':
            self.numChannels += 1
            self.addChannel()
        elif 'Channel' in self.tree.GetItemText(self.selected_item):
            self.addSequence()
        elif 'Sequence' in self.tree.GetItemText(self.selected_item):
            processorFrame = ProcessorFrame(self)
            processorFrame.Show(True)
        elif 'Schedule' in self.tree.GetItemText(self.selected_item):
            self.addScheduleEntry()
        elif 'TaskManagerSettings' in self.tree.GetItemText(self.selected_item):
            task_frame = TaskFrame(self)
            task_frame.Show(True)

    def onRemoveButtonClick(self, event):
        if ('Channel' in self.tree.GetItemText(self.selected_item)):
            self.numChannels -= 1
        #if ('Sequence' in self.tree.GetItemText(self.selected_item)):
        #    self.numSequences -= 1
        self.tree.Delete(self.selected_item)

    def onTreeSelection(self, event):
        self.selected_item = event.GetItem()
        selectionName = self.tree.GetItemText(self.selected_item)

        # Only enable add for PostProcessors, Channel, and Schedule
        if selectionName == 'DaqConfiguration':
            self.addButton.Enable(False)
            self.removeButton.Enable(False)
            self.changeDetailPanel(GreetingPanel(self.panel))
            return
        elif selectionName in self.mainNodes and selectionName not in ['Schedule','TaskManagerSettings']:
            self.addButton.Enable(False)
            self.removeButton.Enable(False)
        elif selectionName == 'Schedule':
            self.addButton.Enable(True)
            self.removeButton.Enable(False)
        elif selectionName == 'TaskManagerSettings':
            self.addButton.Enable(True)
            self.removeButton.Enable(False)
        elif 'Channel' in selectionName:
            self.addButton.Enable(True)
            self.removeButton.Enable(False)
        elif 'Sequence' in selectionName:
            self.addButton.Enable(True)
            self.removeButton.Enable(True)
        else:
            self.addButton.Enable(False)
            self.removeButton.Enable(True)

        self.changeDetailPanel(self.tree.GetItemPyData(self.selected_item))

    def populateTree(self):
        xml = self.xml.getroot()
        print "Tree being populated"
        tree = self.tree
        root = tree.AddRoot(xml.tag)
        def add(parent, elem):
            for e in elem:
                item = tree.AppendItem(parent, e.tag)
                tree.SetItemPyData(item, BasicPanel(self.panel,e.tag,'Click the Add Button to add more PostProcessors to this Channel'))
                text = e.text.strip()
                if text:
                    val = tree.AppendItem(item, text)
                    tree.SetPyData(val, e)
                add(item, e)
        add(root, xml)
        return root

    def getGUIPanel(self, module_name,root_dir='PostProcessors'):
        name = root_dir + '.' + module_name
        module = sys.modules[name]
        module_methods = dir(module)
        if 'GUIPanel' in module_methods:
            GUIPanel = getattr(module,'GUIPanel')
            return GUIPanel(self.panel)
        else:
            return DefaultXMLPanel(self.panel)


    def getTreeDict(self):
        self.d = {}
        child = self.tree.GetFirstChild(self.root)
        #cookie = 1
        #for i in range(4):
        #    child, cookie = self.tree.GetNextChild(self.root, cookie)
        for parent in self.traverse():
            children = {}
            for child in self.traverse(parent):
                children[self.tree.GetItemText(child)] = self.tree.GetItemPyData(child).getDict()
                self.d[self.tree.GetItemText(parent)] = children
        #print self.d

    def getMainPanelTreeItem(self, text):
        (child,cookie) = self.tree.GetFirstChild(self.root)
        for i in range(4):
            if text in self.tree.GetItemText(child):
                return child
            child = self.tree.GetNextSibling(child)

    def traverse(self, parent=None):
        if parent is None:
            parent = self.root
        nc = self.tree.GetChildrenCount(parent, False)

        def GetFirstChild(parent, cookie):
            return self.tree.GetFirstChild(parent)

        GetChild = GetFirstChild
        cookie = 1
        for i in range(nc):
            child, cookie = GetChild(parent, cookie)
            GetChild = self.tree.GetNextChild
            yield child

    def addScheduleEntry(self):
        entryName = "Entry"
        child = self.tree.AppendItem(self.selected_item, entryName)
        self.tree.SetItemPyData(child, ScheduleEntryPanel(self.panel))
        self.tree.Expand(self.selected_item)
        self.tree.SelectItem(child)
        return child

    def addSequence(self):
        sequenceName = "Sequence"
        child = self.tree.AppendItem(self.selected_item, sequenceName)
        self.tree.SetItemPyData(child, BasicPanel(self.panel,sequenceName,'Click the Add Button to add more PostProcessors to this Sequence'))
        self.tree.Expand(self.selected_item)
        self.tree.SelectItem(child)
        return child

    def addChannel(self):
        channelName = "Channel%d" % (self.numChannels-1)
        child = self.tree.AppendItem(self.selected_item, channelName)
        self.tree.SetItemPyData(child, BasicPanel(self.panel,channelName,'Click the Add Button to add more Sequences to this Channel'))
        self.tree.Expand(self.selected_item)
        self.tree.SelectItem(child)
        return child

    def addProcessor(self, processor_name, dict = None):
        child = self.tree.AppendItem(self.selected_item, processor_name)
        panel = self.getGUIPanel(processor_name)
        if dict:
            loadFromDict = getattr(panel, "loadFromDict", None)
            if callable(loadFromDict):
                panel.loadFromDict(dict)
        self.tree.SetItemPyData(child, panel)
        self.tree.Expand(self.selected_item)
        self.tree.SelectItem(child)
        return child


    def addTaskEntry(self, task_name, dict = None):
        child = self.tree.AppendItem(self.selected_item, task_name)
        panel = self.getGUIPanel(task_name,'Tasks')
        if dict:
            loadFromDict = getattr(panel, "loadFromDict", None)
            if callable(loadFromDict):
                panel.loadFromDict(dict)
        self.tree.SetItemPyData(child, panel)
        self.tree.Expand(self.selected_item)
        self.tree.SelectItem(child)
        return child

    def getProcessorNames(self):
        processorNames = []

        for f in os.listdir(os.path.abspath('PostProcessors')):
            module_name, ext = os.path.splitext(f)
            if ext == '.py' and module_name != '__init__' and module_name != 'VLFPanel':
                processorNames.append(module_name)
        return processorNames


    def getTaskNames(self):
        taskNames = []

        for f in os.listdir(os.path.abspath('Tasks')):
            module_name, ext = os.path.splitext(f)
            if ext == '.py' and module_name != '__init__' and module_name != 'VLFPanel':
                taskNames.append(module_name)
        return taskNames

    def Lock(self, event):
        """
        Locks the toolbar and the information panels so that you can't modify
        the data unless you provide a password to unlock the program.
        """
        for i in range(1, 4):
            self.tb.EnableTool(i, self.locked)
        self.locked = not self.locked

    def recurse(self,parent):
        (child, cookie) = self.tree.GetFirstChild(parent)
        while True:
            #print "%s" % self.tree.GetItemText(child)
            #recurse(child)
            #print "test"
            (child, cookie) = self.tree.GetNextChild(parent, cookie)
            if not child:
                break

    #proper no-whitespace in text-elements xml writing (xml.dom.minidom.toprettyxml is useless)
    def writexml(self, document, writer, indent="", addindent="", newl=""):

        def _write_data(writer, data):
            if data:
                data = data.replace("&", "&amp;").replace("<", "&lt;")
                data = data.replace("\"", "&quot;").replace(">", "&gt;")
                writer.write(data)

        #print document
        writer.write(indent+"<" + document.tagName)

        attrs = document._get_attributes()
        a_names = attrs.keys()
        a_names.sort()

        for a_name in a_names:
##            print a_name
            writer.write(" %s=\"" % a_name)
            _write_data(writer, attrs[a_name].value)
            writer.write("\"")
        if document.childNodes:
            writer.write(">%s"%(newl))
            for node in document.childNodes:
                #print "\n"
##                print "node.toxml(): "+node.toxml()
                if node.toxml()[-2:]=="/>":
                    continue
                if node.nodeType!=node.TEXT_NODE:
                    self.writexml(node,writer,indent+addindent,addindent,newl)
                else:

                    if os.name=='nt':
                        writer.seek(writer.tell()-2)    #Need -2 for windows ( -1 for linux)
                    else:
                        writer.seek(writer.tell()-1)
##                    self.writexml(node,writer,"",addindent,"")
                    writer.write(node.toxml())
##                    writer.write('hi')
            if document.childNodes[-1].nodeType!=node.TEXT_NODE:
                writer.write("%s</%s>%s" % (indent,document.tagName,newl))
            else:
                writer.write("</%s>%s" % (document.tagName,newl))
        else:
            writer.write("/>%s"%(newl))


    def writeToXml(self, event):
        #open a filesave dialog
        if os.name=='nt':
            saveDialog = wx.FileDialog(parent=self,message="Save XML settings as",style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        else:
            saveDialog = wx.FileDialog(parent=self,message="Save XML settings as",style=wx.SAVE|wx.OVERWRITE_PROMPT)
            
        saveDialog.SetWildcard("XML files (*.xml)|*.xml")
        (head,tail) = os.path.split(self.start_file_save)
        saveDialog.SetDirectory(head)
        saveDialog.SetFilename(tail)
        if saveDialog.ShowModal() != wx.ID_OK:
            return
        filename=saveDialog.GetPath()
        self.start_file_save = filename
        saveDialog.Destroy()
        root = Element(self.tree.GetItemText(self.root))
        (module, cookie) = self.tree.GetFirstChild(self.root)
        while module:
            moduleNode = SubElement(root, self.tree.GetItemText(module))
            print  "module node: %s" % moduleNode
            
            (channel, channelCookie) = self.tree.GetFirstChild(module)
            
            #print channel, channelCookie
            #print "module: %s" % self.tree.GetItemText(module)
            
            if (channel and "Channel" in self.tree.GetItemText(channel)):
                while channel:
                    #print channel
                    channelNode = SubElement(moduleNode, 'PostProcessorSequence')
                    #print "Channel: %s" % self.tree.GetItemText(channel)
                    (sequence, seqCookie) = self.tree.GetFirstChild(channel)
                    while sequence:
                        sequenceNode = SubElement(channelNode, 'PostProcessorSequence')
                        #print "Sequence: %s" % self.tree.GetItemText(sequence)
                        (postProcessor, ppCookie) = self.tree.GetFirstChild(sequence)
                        while postProcessor:
                            #print postProcessor
                            #print "PP: %s" % self.tree.GetItemText(postProcessor)
                            postProcessorNode = SubElement(sequenceNode, 'PostProcessor')
                            postProcessorNode.attrib["module"] = self.tree.GetItemText(postProcessor)
                            #print self.tree.GetItemText(postProcessor)
                            d = self.tree.GetItemPyData(postProcessor).getDict()
                            for value in d:
                                valueNode = SubElement(postProcessorNode, value)
                                valueNode.text = d[value]
                            (postProcessor, ppCookie) = self.tree.GetNextChild(sequence, ppCookie)
                        (sequence, seqCookie) = self.tree.GetNextChild(channel, seqCookie)
                    (channel, channelCookie) = self.tree.GetNextChild(module, channelCookie)
            elif (channel and self.tree.GetItemText(channel)=="Entry"):
                while channel:
                    entryNode = SubElement(moduleNode,'Entry')
                    d = self.tree.GetItemPyData(channel).getDict()
                    for value in d:
                        valueNode = SubElement(entryNode, value)
                        valueNode.text = d[value]
                    (channel, channelCookie) = self.tree.GetNextChild(module, channelCookie)
            elif self.tree.GetItemText(module)=='TaskManagerSettings':
                taskManagerNode = moduleNode
                #print "TM Module: %s" % self.tree.GetItemText(sequence)
                (task, taskCookie) = self.tree.GetFirstChild(module)
                while task:
                    #print postProcessor
                    #print "PP: %s" % self.tree.GetItemText(postProcessor)
                    taskNode = SubElement(taskManagerNode, 'Task')
                    taskNode.attrib["module"] = self.tree.GetItemText(task)
                    #print self.tree.GetItemText(postProcessor)
                    d = self.tree.GetItemPyData(task).getDict()
                    for value in d:
                        valueNode = SubElement(taskNode, value)
                        valueNode.text = d[value]
                    (task, taskCookie) = self.tree.GetNextChild(module, taskCookie)
            else:

                d = self.tree.GetItemPyData(module).getDict()
                
                for value in d:
                    valueNode = SubElement(moduleNode, value)
                    #print "Valuenode: %s" % valueNode
                    
                    if value=="Module":
                        moduleNode.attrib["module"] = d[value]
                        
                    valueNode.text = d[value]
                    
            (module, cookie) = self.tree.GetNextChild(self.root, cookie)
            
            print "*****************"
            
        ElementTree(root).write('tempcompact.xml')
        
        #reformat the temporary xml file to something human-readable/editable
        xmldoc = xml.dom.minidom.parse('tempcompact.xml')
        
        fout = open(filename,'w')
        header_string = "<!-- Settings generated at %s [LT] by GUI version %s -->\n\n" % (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),__ver__)
        print header_string
        fout.write(header_string)
        #fout.write(xmldoc.toprettyxml(indent='\t',newl='\n',encoding='ascii'))
        self.writexml(xmldoc.firstChild,fout,indent="",addindent="\t",newl="\n")
        fout.close()
        print 'Finished writing to %s' % filename


    def readFromXml(self, event):
        try:
            #open a fileopen dialog
            if self.xmlPath is None:
                if os.name=='nt':
                    openDialog = wx.FileDialog(parent=self,message="Open XML settings",style=wx.FD_OPEN)
                else:
                    openDialog = wx.FileDialog(parent=self,message="Open XML settings",style=wx.OPEN)
                (head,tail) = os.path.split(self.start_file_save)
                openDialog.SetFilename(tail)
                openDialog.SetDirectory(head)
                openDialog.SetWildcard("XML files (*.xml)|*.xml")
                if openDialog.ShowModal() != wx.ID_OK:
                    return

                filename=openDialog.GetPath()
                openDialog.Destroy()
            else:
                filename =self.xmlPath
                self.xmlPath = None
            self.start_file_save = filename

            # Clear current tree / reinitialize numChannels to 0
            if self.root is not None:
                self.tree.Delete(self.root)
            self.numChannels = 0

            root = ET.parse(filename).getroot()
            self.root = self.tree.AddRoot(root.tag)
##            self.tree.Expand(self.root)
            #print root.tag
            self.tree.SelectItem(self.root)
##            self.selected_item = self.tree.GetSelection()

            done_tm = False

            # Iterate through the modules and add them to the root
            for module in root:
                #print "module.tag = " + module.tag
                child = self.tree.AppendItem(self.root, module.tag)
##                self.tree.SetItemPyData(child, self.mainPanels[i])
                self.tree.SetItemPyData(child,self.mainPanels[self.mainNodes.index(module.tag)])
                self.tree.SelectItem(child)
                if self.tree.GetItemText(child)=="Schedule":
                    sched = child
                loadFromDict = getattr(self.mainPanels[self.mainNodes.index(module.tag)], "loadFromDict", None)
                d = {}
                # All modules except the PostProcessor module has a loadFromDict function, so we access them here
                if callable(loadFromDict) and module.tag not in ["Schedule","TaskManagerSettings"]:
                    # Load saved data for the modules
                    if module.attrib.has_key("module"):
                        d["Module"]=module.attrib["module"]
                    for value in module:
                        #print value.tag
                        #Strip out whitespace in formatted xml files
                        if value.text is not None:
                            d[value.tag] = value.text.lstrip().rstrip()
                    #print "d: %s" % d.keys()
                    self.tree.GetItemPyData(child).loadFromDict(d)

                # The PostProcessor module doesn't have a loadFromDict function, so we deal with it here
                else:
                    # Iterate through all the channels and add them to the PostProcessor module
                    for channel in module:
                        #print "channel.tag: " + channel.tag
                        if "PostProcessor" in channel.tag:
                            self.tree.SelectItem(child)
                            self.numChannels += 1
                            channelNode = self.addChannel()
                            for sequence in channel:
                                self.tree.SelectItem(channelNode)
                                sequenceNode = self.addSequence()
                                # Iterate through all post processors in the sequence and add them
                                for postProcessor in sequence:
                                    # Populate dictionary to load saved data
                                    d = {}
                                    for value in postProcessor:
                                        d[value.tag] = value.text.lstrip().rstrip()
                                    # Import the PostProcessor object before using it
                                    name = 'PostProcessors.' + postProcessor.get('module')
                                    __import__(name)
                                    postProcessorNode = self.addProcessor(postProcessor.get('module'), d)
                                    self.tree.SelectItem(sequenceNode)
                                    #print d
                                    self.tree.GetPyData(postProcessorNode).loadFromDict(d)
                            self.tree.Collapse(child)

                        if "Entry" in channel.tag:
                            entryNode = channel
                            if sched:
                                self.tree.SelectItem(sched)
                            entry = self.addScheduleEntry()
                            d = {}
                            for value in entryNode:
                                d[value.tag] = value.text.lstrip().rstrip()
                            self.tree.GetPyData(entry).loadFromDict(d)
                            self.tree.Collapse(sched)

                        if "TaskManagerSettings" == module.tag:
                            if not done_tm:
                                done_tm = True

##                                print module.tag
                                for task in module:
                                    self.tree.SelectItem(child)
    ##                                print task.get('module')
                                    # Populate dictionary to load saved data
                                    d = {}
                                    for value in task:
    ##                                    print value.tag
                                        d[value.tag] = value.text.lstrip().rstrip()
                                    # Import the PostProcessor object before using it
                                    name = 'Tasks.' + task.get('module')
                                    __import__(name)
                                    taskNode = self.addTaskEntry(task.get('module'), d)
                                    self.tree.SelectItem(taskNode)
                                    #print d
                                    self.tree.GetPyData(taskNode).loadFromDict(d)
                            self.tree.Collapse(child)
            self.tree.SelectItem(self.root)


        except Exception, ecc:
            print ecc
            (excType, excValue, excTb) = exc_info()
            for tb in traceback.extract_tb(excTb):
                print '%s'% str(excValue)
                print '\tLine %s in function %s: %s'% (tb[1],tb[2],tb[3])
            wx.MessageBox("Open Failed","Alert")
            for panel in self.mainPanels:
                #print dir(panel)
                panel.Hide()
            self.loadNewTree(None)


    def loadNewTree(self, event):
        # Clear current tree / reinitialize numChannels to 0
        if self.root:
            self.tree.Delete(self.root)
        self.numChannels = 0
        self.start_file_save = "../DaqSettings.xml"

        self.root = self.tree.AddRoot('DaqConfiguration')
        self.tree.Expand(self.root)
        self.tree.SelectItem(self.root)
        self.selected_item = self.tree.GetSelection()



        i = 0
        for nodeName in self.mainNodes:
            child = self.tree.AppendItem(self.root, nodeName)
            self.tree.SetItemPyData(child, self.mainPanels[i])
            self.tree.SelectItem(child)
            i += 1

        self.tree.SelectItem(self.root)

class ProcessorFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, title="Select your Processor", size=(600,400))
        self.Centre()
        self.parent = parent
        self.panel = wx.Panel(self, wx.ID_ANY)

        self.processorList = parent.getProcessorNames()
        for processor in self.processorList:
            __import__('PostProcessors.' + processor)
        title = wx.StaticText(self, -1, "Select Your Processor", (20, 10))
        font = wx.Font(18, wx.SWISS, wx.NORMAL, wx.NORMAL)
        title.SetFont(font)
        self.lb = wx.ListBox(self, -1, (20, 35), (200, 325), self.processorList, wx.LB_SINGLE)
        self.description = wx.StaticText(self, -1, 'Select a PostProcessor module on the left to view its documentation', (240, 35), (320,275))
        self.Bind(wx.EVT_LISTBOX, self.onClickProcessor, self.lb)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.onOK, self.lb)

        ok_button = wx.Button(self, wx.ID_ANY, "Ok", (520,335))
        self.Bind(wx.EVT_BUTTON, self.onOK, ok_button)
        cancel_button = wx.Button(self, wx.ID_ANY, "Cancel", (440,335))
        self.Bind(wx.EVT_BUTTON, self.onCancel, cancel_button)

    def onClickProcessor(self, event):
        self.description.Destroy()
        name = 'PostProcessors.' + event.GetString()
        __import__(name)
        self.description = wx.StaticText(self, -1, sys.modules[name].__doc__, (240, 35), (320,275))

    def onOK(self, event):
        self.parent.addProcessor(self.processorList[self.lb.GetSelection()])
        self.Destroy()

    def onCancel(self, event):
        self.Destroy()


class TaskFrame(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, title="Select your Task", size=(600,400))
        self.Centre()
        self.parent = parent
        self.panel = wx.Panel(self, wx.ID_ANY)

        self.taskList = parent.getTaskNames()
        for task in self.taskList:
            __import__('Tasks.' + task)
        title = wx.StaticText(self, -1, "Select Your Task", (20, 10))
        font = wx.Font(18, wx.SWISS, wx.NORMAL, wx.NORMAL)
        title.SetFont(font)
        self.lb = wx.ListBox(self, -1, (20, 35), (200, 325), self.taskList, wx.LB_SINGLE)
        self.description = wx.StaticText(self, -1, 'Select a Task module on the left to view its documentation', (240, 35), (320,275))
        self.Bind(wx.EVT_LISTBOX, self.onClickTask, self.lb)
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.onOK, self.lb)

        ok_button = wx.Button(self, wx.ID_ANY, "Ok", (520,335))
        self.Bind(wx.EVT_BUTTON, self.onOK, ok_button)
        cancel_button = wx.Button(self, wx.ID_ANY, "Cancel", (440,335))
        self.Bind(wx.EVT_BUTTON, self.onCancel, cancel_button)

    def onClickTask(self, event):
        self.description.Destroy()
        name = 'Tasks.' + event.GetString()
        __import__(name)
        self.description = wx.StaticText(self, -1, sys.modules[name].__doc__, (240, 35), (320,275))

    def onOK(self, event):
        self.parent.addTaskEntry(self.taskList[self.lb.GetSelection()])
        self.Destroy()

    def onCancel(self, event):
        self.Destroy()


class DefaultXMLPanel(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY, pos=wx.DefaultPosition, size=(300,470))
        self.gbs = wx.GridBagSizer(hgap=5, vgap=0)

        title = wx.StaticText(self, wx.ID_ANY, "Default XML Panel")
        font = wx.Font(18, wx.SWISS, wx.NORMAL, wx.NORMAL)
        title.SetFont(font)
        self.gbs.Add(title,pos=(0,0),span=(1,2))
        self.gbs.Add(wx.TextCtrl(self, wx.ID_ANY,"This is the default panel", wx.DefaultPosition, size=(565,427), style=wx.TE_MULTILINE|wx.TE_PROCESS_ENTER),pos=(1,0))

        box = wx.BoxSizer()
        box.Add(self.gbs,0,wx.ALL,10)
        self.SetSizerAndFit(box)

class GreetingPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, wx.ID_ANY, pos=wx.DefaultPosition, size=(300,470))
        self.gbs = wx.GridBagSizer(hgap=5, vgap=5)

        title = wx.StaticText(self, wx.ID_ANY, "Welcome to the Stanford VLF DAQ")
        font = wx.Font(18, wx.SWISS, wx.NORMAL, wx.NORMAL)
        title.SetFont(font)
        self.gbs.Add(title,pos=(0,0),span=(1,3))

        box = wx.BoxSizer()
        box.Add(self.gbs,0,wx.ALL,10)
        self.SetSizerAndFit(box)

class BasicPanel(wx.Panel):
    def __init__(self, parent, titleText, descriptionText):
        wx.Panel.__init__(self, parent, wx.ID_ANY, pos=wx.DefaultPosition, size=(300,470))
        self.gbs = wx.GridBagSizer(hgap=5, vgap=5)

        title = wx.StaticText(self, wx.ID_ANY, titleText)
        titleFont = wx.Font(18, wx.SWISS, wx.NORMAL, wx.NORMAL)
        title.SetFont(titleFont)
        self.gbs.Add(title,pos=(0,0),span=(1,3))

        description = wx.StaticText(self, wx.ID_ANY, descriptionText)
        descriptionFont = wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL)
        description.SetFont(descriptionFont)
        self.gbs.Add(description,pos=(1,0),span=(2,2))

        box = wx.BoxSizer()
        box.Add(self.gbs,0,wx.ALL,10)
        self.SetSizerAndFit(box)

class SchedulePanel(VLFPanel):
    def __init__(self, parent):
        VLFPanel.__init__(self, parent, 'Click \'Add\' to create new schedule entries')
        self.widgets = {}
        self.addWidgets()


class ScheduleEntryPanel(VLFPanel):
    def __init__(self,parent):
        VLFPanel.__init__(self,parent,"Entry")
        self.widgets = {
            'Start':(wx.TextCtrl(self, wx.ID_ANY, size= (150,-1)),'HH:MM'),
            'Duration':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Seconds]; -1 or 86400: Cont. mode')
        }
        self.addWidgets()

class StationSettingsPanel(VLFPanel):
    def __init__(self,parent):
        VLFPanel.__init__(self,parent,"StationSettings")
        self.widgets = {
            'station_id':wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),
            'station_name':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
            'station_description':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
            'hardware_description':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
            'antenna_bearings':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
            'antenna_description':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
            'install_date':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
            'contact_info':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
            'adc_type':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
            'computer_sn':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
            'adc_sn':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
            'gps_sn':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
##            'VERSION':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE)
        }
        self.addWidgets()


class AuxiliaryInfoPanel(VLFPanel):
    def __init__(self, parent):
        VLFPanel.__init__(self, parent, 'GpsClock')
        self.widgets = {
##            'Module':wx.TextCtrl(self,wx.ID_ANY,size= self.STRING_SIZE),
            'Module':wx.Choice(self, wx.ID_ANY, size= (150,-1),choices = ['MotorolaClock','TrueTimeClock','VirtualClock']),
            'ComPortNumber':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
            'BaudRate':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'MO,TT: 9600'),
            'DataBits':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'MO: 8, TT: 7'),
            'Parity':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'MO: N, TT: E'),
            'StopBits':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'MO,TT: 1')
        }
        self.addWidgets()
        
class LoggerPanel(VLFPanel):
    def __init__(self, parent):
        VLFPanel.__init__(self, parent, 'Logger')
        self.widgets = {
            'LogDir': wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
            'ErrorEmail': wx.CheckBox(self, wx.ID_ANY, size=(150,-1), label="Email on Errors", name = "checkBox"),
            'ErrorPost': wx.CheckBox(self, wx.ID_ANY, size=(150,-1), label="HTTP POST on Errors", name = "checkBox"),
            'LogPostUrl':(wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),'URL for POST errors'),
            'LogPostServer':(wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),'Server for POST errors'),
            'LogLevel':(wx.Choice(self, wx.ID_ANY, size= (150,-1),choices = ['INFO', 'WARNING', 'CRITICAL', 'DEBUG']), "Overall logger filter. Set this at highest level you need."), 
            'ConsoleLevel':(wx.Choice(self, wx.ID_ANY, size= (150,-1),choices = ['INFO', 'WARNING', 'CRITICAL', 'DEBUG']), "Console display log level. Use *Debug* at your own risk."), 
            'LogFileLevel':(wx.Choice(self, wx.ID_ANY, size= (150,-1),choices = ['WARNING', 'CRITICAL', 'INFO', 'DEBUG']), "Log file log level. Use *Debug* at your own risk."), 
            'PostLevel':(wx.Choice(self, wx.ID_ANY, size= (150,-1),choices = ['WARNING', 'CRITICAL', 'INFO', 'DEBUG']), "HTTP POST log level. Use *Debug* at your own risk.") 
        }
        self.addWidgets()
        
    #def onUpdateChannels(self, event):
        
class DAQCardPanel(VLFPanel):
    def __init__(self, parent):
        VLFPanel.__init__(self, parent.panel, 'DAQCard')
        self.widgets = {
##            'Module':wx.TextCtrl(self, wx.ID_ANY, size= self.STRING_SIZE),
            'Module':wx.Choice(self, wx.ID_ANY, size= (150,-1),choices = ['NIDAQmx']),
            'DevName':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'DevX'),
            'NumChannels':wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),
            '_ ':wx.Button(self,wx.ID_ANY,"Update # of Channels in PostProcessorTree"),
            'SampleRate':wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),
            'SampleClockName':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'Usually: PFI2 (sampling clock)'),
            'SampleClockPolarity':(wx.Choice(self,wx.ID_ANY,size=self.DROP_BOOL_SIZE,choices = ['1','0']),'0: Falling; 1: Rising (default)'),
            'StartTriggerName':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'Usually: PFI0 (1 pps)'),
            'StartTriggerPolarity':(wx.Choice(self,wx.ID_ANY,size=self.DROP_BOOL_SIZE,choices = ['0','1']),'0: Falling (default); 1: Rising'),
        }
        self.addWidgets()
        self.parent = parent
        self.Bind(wx.EVT_BUTTON,self.onUpdateChannels,self.widgets['_ '])


    def onUpdateChannels(self, event):
        numChannels = self.widgets['NumChannels'].GetValue()
        #print numChannels
        try:
            numChannels = string.atoi(numChannels)
        except:
            wx.MessageBox("Not a valid number","Alert")
            return
        ppt = self.parent.getMainPanelTreeItem("PostProcessorTree")
        #if there are already fewer channels, add more
        if self.parent.numChannels < numChannels:
            for i in range(numChannels-self.parent.numChannels):
                self.parent.tree.SelectItem(ppt)
                self.parent.numChannels += 1
                self.parent.addChannel()
        #otherwise, delete until you get the right number of them
        elif self.parent.numChannels > numChannels:
            for i in range(self.parent.numChannels-numChannels):
                self.parent.tree.SelectItem(ppt)
                channel = self.parent.tree.GetLastChild(ppt)
                self.parent.tree.Delete(channel)
                self.parent.numChannels -= 1

# Testing purposes
if __name__ == "__main__":

    from optparse import OptionParser

    parser=OptionParser(version= __ver__,
                        description='GUI to edit VLF DAQ settings xml file. ')
    parser.add_option("--settings",dest='settings',type="string",
                      help="Settings (.xml) filename.  Default: %default (If None, creates new settings tree)")

    (options,args) = parser.parse_args()

    app = wx.App(redirect=False)
    top = DAQFrame(options.settings)
    top.Show()
    #wx.lib.inspection.InspectionTool().Show()
    app.MainLoop()
