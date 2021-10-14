import wx
class VLFPanel(wx.Panel):

    def __init__(self, parent, titleText):
        wx.Panel.__init__(self, parent, wx.ID_ANY, pos=wx.DefaultPosition, size=(300,470))

        self.gbs = wx.GridBagSizer(hgap=5, vgap=5)

        title = wx.StaticText(self, wx.ID_ANY, titleText)
        font = wx.Font(18, wx.SWISS, wx.NORMAL, wx.NORMAL)
        title.SetFont(font)
        self.gbs.Add(title,pos=(0,0),span=(1,2))

        self.BOOL_SIZE = (35,-1)
        self.FLOAT_SIZE = (60,-1)
        self.DIR_SIZE = (350,-1)
        self.STRING_SIZE = (200,-1)
        self.DROP_BOOL_SIZE = (45,-1)

    def addWidgets(self):
        i = 1
        ids = []
        gui_comments = {}
        for widget in self.widgets:
            if isinstance(self.widgets[widget],tuple):
                gui_comments[widget] = self.widgets[widget][1]
                self.widgets[widget] = self.widgets[widget][0]
            else:
                gui_comments[widget] = ''
            ids.append(self.widgets[widget].GetId())
        ids.sort(reverse=True)
        for id in ids:
            for widget in self.widgets:
                if self.widgets[widget].GetId()==id:
                    self.gbs.Add(wx.StaticText(self, wx.ID_ANY, widget),pos=(i,0))
                    self.gbs.Add(self.widgets[widget],pos=(i,1))
                    if self.widgets[widget].GetName()=='choice':
                        self.widgets[widget].SetSelection(0)
                    self.gbs.Add(wx.StaticText(self,wx.ID_ANY,gui_comments[widget]),pos=(i,2))
                    i += 1
        box = wx.BoxSizer()
        box.Add(self.gbs,0,wx.ALL,10)
        self.SetSizerAndFit(box)

    def getDict(self):
        d = {}
        for widget in self.widgets:
            #check to make sure widget has a GetValue method
            if hasattr(self.widgets[widget],"GetValue"):
                temp = self.widgets[widget].GetValue()
                
                # Handle booleans 
                if temp == True:
                    d[widget] = '1'
                elif temp == False:
                    d[widget] = '0'
                else:
                    d[widget] = temp
                
            elif hasattr(self.widgets[widget],"GetStringSelection"):
                d[widget] = self.widgets[widget].GetStringSelection()
        return d

    def loadFromDict(self,load):
        for value in load:
            #print "Value: %s" % value
            
            for widget in self.widgets:
                #print "Widget: %s" %widget
                
                if widget == value:
                    
                    #print "Widget: %s" % self.widgets[widget].GetName()
                
                    if self.widgets[widget].GetName()=='choice':
                        try:
                            index = self.widgets[widget].GetItems().index(load[value])
                        except:
                            index = 0
                        #print 'index: %d' % index
                        self.widgets[widget].SetSelection(index)
                    elif self.widgets[widget].GetName()== "checkBox":
                        #print self.widgets[widget]
                        try:
                            selection = self.widgets[widget].GetValue()
                        except:
                            selection = False
                            
                        #print 'load(value): %s' % load[value]
                        #print 'default: %d' % selection

                        if load[value] == '1':
                            self.widgets[widget].SetValue(True)
                            #print "setting to true"
                        elif load[value] == '0':
                            self.widgets[widget].SetValue(False)
                            #print "setting to false"
                        else:
                            if selection == '1':
                                self.widgets[widget].SetValue(True)
                                #print "derault to true"
                            else:
                                self.widgets[widget].SetValue(False)
                                #print "default to false"
                    else:
                        self.widgets[widget].SetValue(load[value])

                    break
