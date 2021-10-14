"""
Displays real-time scrolling spectrogram
"""


from datetime import datetime, timedelta
import os.path
import os, sys
sys.path.append(['..'])
from time import sleep, clock, time
if os.name != 'nt':
    clock=time

from shutil import copyfile
import sys

from Queue import Full, Empty

from multiprocessing import Queue, Process

import matplotlib
##matplotlib.use('WXAgg')
from matplotlib.figure import Figure

#Using either threading or processing module:
use_processing = True

#Hack for Scipy vs > 0.6
import scipy.misc
import scipy
scipy.factorial = scipy.misc.factorial

from scipy.signal import firwin
from scipy.signal.filter_design import freqz

import numpy as np
from matplotlib.pyplot import figure
from matplotlib import rcParams
from matplotlib.colorbar import make_axes, Colorbar
import scipy.fftpack as fft
import math as ma

from utilities import read_config

import np_extensions as ne

__all__ = ['ScrollingSpecgram']

try:
    import wx
    from VLFPanel import VLFPanel

    from matplotlib.backends.backend_wxagg import \
        FigureCanvasWxAgg as FigCanvas, \
        NavigationToolbar2WxAgg as NavigationToolbar

    class GUIPanel(VLFPanel):
        def __init__(self, parent):
            VLFPanel.__init__(self, parent, "ScrollingSpecgram")
            self.widgets = {
                'adc_channel_number':wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),
                'Duration':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Seconds]'),
                'NFFT':wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),
                'fmin':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[kHz]'),
                'fmax':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[kHz]'),
                'cmin':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[dB]'),
                'cmax':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[dB]'),
            }
            self.addWidgets()
except:
    print "WARNING (ScrollingSpecgram): CAN'T IMPORT WX AND/OR VLFPanel"

def calcQuadPeak(y1,y2,y3):
    """
    returns index and amplitude of quadratic maxima (x0,y0)
    from values y1,y2,y3 spaced on [x1,x2,x3] = [-1,0,1]
    """
    x0 =  .5*(y1-y3)/(y1-2.0*y2 + y3)
    return x0,y2 - .25*(y1-y3)*x0

def find_nan(x):
    return np.where((~(x >= 0)) & (~(x<0)))[0]

def linInterpValue(x,indices):
    """
    values = linInterpValue(x,indices)

    input numpy arrays x and (scalar,list, or numpy array) indices
    returns linear-interpolated values indexed by indices

    """
    indices = np.atleast_1d(indices)
    if((indices.min()<0) or (indices.max()>len(x)-1)):
        raise 'Indices must be between 0 and len(x)-1'

    ceil_index =np.asarray(np.ceil(indices),np.int)
    floor_index = np.asarray(np.floor(indices),np.int)
    return (x[ceil_index] - x[floor_index])*(indices-floor_index) + x[floor_index]

def gausswin(L,a=2.5):
    """ copies MATLAB gausswin """
    n = np.linspace(0.0,L-1.0,L)-(L-1.0)/2.0
    return np.exp(-.5*((a*n/((L-1.0)/2.0))**2.0))

def nextpow2(i):
    """ returns the power, not the number """
    N = 1   #number
    n = 0   #power
    while N < i:
        n = n + 1.0
        N = N * 2.0
    return n






class STFT():
    """
    STFT
    """

    """
    Earlier documentation:
                (t,f[:N/2+1],2z[:N/2+1]) for one-sided
            *norm*:
                'tone': normalize so that tone magnitudes can be read directly
                'psd': normalize so that each fft bin is a periodogram
                'none': no normalization (straight FFT's)

    earlier code:
        if(norm.lower()=='none'):
            one_sided_fctr = 2.0
        elif(norm.lower()=='tone'):
            z /= win.sum()
            one_sided_fctr = 2.0
        else:    #'psd'
            z = sqrt(abs(z)**2/sum(win**2)/fs)
            one_sided_fctr = sqrt(2.0)


    if two_sided:
        return (t,f,z)
    else:
        z[:,1:framelen/2] *= one_sided_fctr  #Don't multiply DC or nyquist by 2 (or sqrt(2) for psd)
        return (t,f[0:framelen/2+1],z[:,0:framelen/2+1])
    """


    def __init__(self,duration,fs,NFFT=1024,win=None):
        """
        hamming window applied by default; may specify win
        fields: (t,f,z)

        THis version accepts a second at a time, keeps a duration second record
        """
        NUM_BINS_IN_FIGURE = 1000.0    #number of time bins per second

        self.iscomplex = False

        self.noverlap = int(np.round(NFFT - fs*duration/NUM_BINS_IN_FIGURE))
        print 'noverlap = %d' % self.noverlap
        self.axis = None
        self.end = 'cut'
        self.endvalue = 0
        if win==None:
            win = np.hamming(NFFT)
        self.framelen = len(win)
        self.win = win
        x = np.zeros(fs)    #one second

        z = self.segment_axis(x,self.framelen,self.noverlap,self.axis,self.end,self.endvalue)
        z = fft.fft(z*self.win,NFFT)
        self.one_sec_len = z.shape[0]

        self.z = np.zeros((self.one_sec_len*duration,z.shape[1]))


        #keep everything but data:
        self.duration = duration
        self.NFFT = NFFT
        self.win = win
        self.fs =fs
        self.t = (np.linspace(0,self.z.shape[0]-1,self.z.shape[0])*(self.framelen-self.noverlap) + (self.framelen-1)/2)/self.fs
        self.t -= self.t[-1]
        self.f = np.arange(float(self.NFFT))*fs/self.NFFT





    def update(self,x):
        z = self.segment_axis(x,self.framelen,self.noverlap,self.axis,self.end,self.endvalue)
        z = fft.fft(z*self.win,self.NFFT)

##        print z.shape, self.z[:(self.duration-1)*self.one_sec_len].shape, self.z[self.one_sec_len:].shape, self.z.shape, self.one_sec_len, (self.duration-1)*self.one_sec_len
        self.z[:(self.duration-1)*self.one_sec_len] = self.z[self.one_sec_len:]
        self.z[(self.duration-1)*self.one_sec_len:] = z

    def read_out_params(self):
        return (self.fs, self.NFFT,self.noverlap, self.win)

    def __str__(self):
        return 'Time: %2.2f-%2.2f; Freq: %2.2f-%2.2f' % (self.t.min(),self.t.max(),self.f.min(),self.f.max())

    def get_df(self):
        return self.f[1] - self.f[0]


    def avg_tone_height(self):

        upper_f_index = self.NFFT/2+1

        z = np.abs(self.z[:,:upper_f_index])/self.win.sum()
        z[:,1:self.NFFT/2] *= 2.0
        z = np.mean(z,0);


        return (self.f[:upper_f_index],z)

    def get_max_first_col(self):
        """
        return maximum absolute value (tone normalization) of first column
        """
        first_col =  np.abs(self.z[0,:])/self.win.sum()
        return np.max(first_col)

    def specgram(self,axes,clim=None,cmap = None,tlim = None,flim=None):
        """
        if tlim [sec] is not None, will limit t range
        if flim [kHz] is not None, will limit f range
        """

        upper_f_index = self.NFFT/2+1

        z = np.abs(self.z[:,:upper_f_index])/self.win.sum()

        z[:,1:self.NFFT/2] *= 2.0

        freqs = self.f[:upper_f_index]

        #----------------------------------
        z = 20*np.log10(np.flipud(np.transpose(z)))
        (extent,z) = self.get_tf_extent(z,freqs,tlim,flim)

        if not axes._hold: axes.cla()
        if(clim is None):
            im = axes.imshow(z, cmap, extent=extent,interpolation = 'nearest')
        else:
            im = axes.imshow(z, cmap, extent=extent,vmin = clim[0],vmax = clim[1],interpolation='nearest')
        axes.axis('auto')

        return im



    def get_complex_mag(self):
        z = np.transpose(np.abs(self.z)/self.win.sum())

        temp1 = z[1:int(self.NFFT/2),:]
        temp2 = z[self.NFFT/2+1:,:]

        z = 20*np.log10(temp1 + np.flipud(temp2))

        z = np.flipud(z)
        return z


    def get_tf_extent(self,z,freqs,tlim,flim):
        tmin = np.min(self.t)
        tmax = np.max(self.t)
        fmin = freqs[0]/1e3
        fmax = freqs[-1]/1e3



        if flim is not None:    #restrict time range
            ii_lo,slope = self.linInterpInv(freqs/1e3,flim[0])
            ii_hi,slope = self.linInterpInv(freqs/1e3,flim[1])
            if len(ii_lo)==0:
                ii_lot = 0
            else:
                ii_lot = int(ii_lo[0])
            if len(ii_hi)==0:
                ii_hit = len(freqs)-1
            else:
                ii_hit = int(ii_hi[0])

            ii_lo = len(freqs)-1-ii_hit
            ii_hi = len(freqs)-1-ii_lot

            z = z[ii_lo:ii_hi+1,:]
            fmin,fmax = freqs[ii_lot]/1e3,freqs[ii_hit]/1e3

        extent = (tmin,tmax,fmin,fmax)
        return extent,z

    def linInterpInv(self,x,y):
        """
        (indices,slope)=linInterpInv(x,y)
        x is a numpy array
        y is a scalar

        Returns the indices (and slope of x) where x crosses y
        """
        assert isinstance(y,(int,float)), ' y must be a scalar'
        (indices,slope) = self.findZeroCrossings(x-y)
        return (indices,slope)

    def findZeroCrossings(self,x):
        """ Indices of all zero crossings """

        #indicesLo = where((abs(sign(append(x[1:],0.0)) - sign(x))==2) | (append(x[0:-1],-1.0)==0))[0]
        indicesLo = np.where((np.abs(np.sign(x[1:])-np.sign(x[:-1]))>1) | (x[:-1]==0))[0]
        slope = x[indicesLo+1]-x[indicesLo]
        indices = -x[indicesLo]/slope + indicesLo*1.0

        if(x[-1]==0):
            indices = np.append(indices,len(x)*1.0-1.0)
            slope = np.append(slope,x[-1]-x[-2])
        return(indices,slope)



    def segment_axis(self,a, length, overlap=0, axis=None, end='cut', endvalue=0):
        """Generate a new array that chops the given array along the given axis into overlapping frames.

        example:
        >>> segment_axis(arange(10), 4, 2)
        array([[0, 1, 2, 3],
               [2, 3, 4, 5],
               [4, 5, 6, 7],
               [6, 7, 8, 9]])

        arguments:
        a       The array to segment
        length  The length of each frame
        overlap The number of array elements by which the frames should overlap
        axis    The axis to operate on; if None, act on the flattened array
        end     What to do with the last frame, if the array is not evenly
                divisible into pieces. Options are:

                'cut'   Simply discard the extra values
                'wrap'  Copy values from the beginning of the array
                'pad'   Pad with a constant value

        endvalue    The value to use for end='pad'

        The array is not copied unless necessary (either because it is
        unevenly strided and being flattened or because end is set to
        'pad' or 'wrap').
        """

        if axis is None:
            a = np.ravel(a) # may copy
            axis = 0

        l = a.shape[axis]

        if overlap>=length:
            raise ValueError, "frames cannot overlap by more than 100%"
##        if overlap<0 or length<=0:
##            raise ValueError, "overlap must be nonnegative and length must be positive"

        if l<length or (l-length)%(length-overlap):
            if l>length:
                roundup = length + (1+(l-length)//(length-overlap))*(length-overlap)
                rounddown = length + ((l-length)//(length-overlap))*(length-overlap)
            else:
                roundup = length
                rounddown = 0
            assert rounddown<l<roundup
            assert roundup==rounddown+(length-overlap) or (roundup==length and rounddown==0)
            a = a.swapaxes(-1,axis)

            if end=='cut':
                a = a[...,:rounddown]
            elif end in ['pad','wrap']: # copying will be necessary
                s = list(a.shape)
                s[-1]=roundup
                b = np.empty(s,dtype=a.dtype)
                b[...,:l] = a
                if end=='pad':
                    b[...,l:] = endvalue
                elif end=='wrap':
                    b[...,l:] = a[...,:roundup-l]
                a = b

            a = a.swapaxes(-1,axis)


        l = a.shape[axis]
        if l==0:
            raise ValueError, "Not enough data points to segment array in 'cut' mode; try 'pad' or 'wrap'"
        assert l>=length
        assert (l-length)%(length-overlap) == 0
        n = 1+(l-length)//(length-overlap)
        s = a.strides[axis]
        newshape = a.shape[:axis]+(n,length)+a.shape[axis+1:]
        newstrides = a.strides[:axis]+((length-overlap)*s,s) + a.strides[axis+1:]

        try:
            return np.ndarray.__new__(np.ndarray,strides=newstrides,shape=newshape,buffer=a,dtype=a.dtype).astype(np.complex)
        except TypeError:
            a = a.copy()
            # Shape doesn't change but strides does
            newstrides = a.strides[:axis]+((length-overlap)*s,s) + a.strides[axis+1:]
            return np.ndarray.__new__(np.ndarray,strides=newstrides,shape=newshape,buffer=a,dtype=a.dtype).astype(np.complex)


class myPanel(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self,parent)

    def label(self,text,id=-1,**kwargs):
        return  wx.StaticText(self,id,text,**kwargs)

    def textbox(self,width=30,**kwargs):
        return wx.TextCtrl(self,size=(width,-1),style=wx.TE_PROCESS_ENTER,**kwargs)

    def checkbox(self):
        return wx.CheckBox(self)

    def button(self,text,id=-1,**kwargs):
        return  wx.Button(self, id, text,**kwargs)

def launch_gui(queue,params):

    app = wx.PySimpleApp()
    app.frame = specgram_window(queue,params)
    app.frame.Show()
    app.MainLoop()

class specgram_window(wx.Frame):
    """ The main frame of the application
    """
    title = 'Spectrogram'

    def __init__(self,queue,params):
        wx.Frame.__init__(self, None, -1, self.title,size = (1000,500))
        self.panel = myPanel(self)


        self.queue = queue
        self.params = params
        self.dpi = 100

        self.fig = Figure((8.0, 6.0), dpi=self.dpi)
        self.canvas = FigCanvas(self.panel, -1, self.fig)
        self.ax = self.fig.add_axes([.05,.1,.8,.8])
        self.cax = self.fig.add_axes([.9,.1,.04,.8])

        #add canvases and toolbars to plot panels:
        vbox= wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.panel.SetSizer(vbox)
        self.firstLoop=True



        TIMER_ID = 100

        wx.EVT_TIMER(self,TIMER_ID,self.update_figure)
        self.timer = wx.Timer(self,TIMER_ID)
        self.timer.Start(1000)


    def update_figure(self,evt):
        try:
            data = self.queue.get(timeout=.5)
        except Empty:
            return
        tt = clock()

        if self.firstLoop:
            self.fs = data[1]
            self.stft = STFT(self.params['duration'],self.fs,NFFT=self.params['NFFT'])


        if not self.firstLoop:
            self.ax.images.remove(self.im)
            del(self.im)

        current_time = data[2] + timedelta(0,1)

        self.stft.update(data[0])

        self.im = self.stft.specgram(self.ax,clim = [self.params['cmin'],self.params['cmax']],flim = [self.params['fmin'],self.params['fmax']])

        if self.firstLoop:
            Colorbar(self.cax, self.im)
            self.cax.set_title('dB (raw)')
            self.ax.set_ylabel('Frequency [kHz]')
            self.ax.set_title('%s; Channel %d (Df = %3.2f Hz)' % (self.params['station_name'],self.params['adc_channel_number'],self.stft.get_df()))

        self.ax.set_xlabel('Time [seconds] referenced to current time: %s [UT]' % current_time)
        self.canvas.draw()

        self.firstLoop = False
##        print 'Time to post new second: % 2.3f' % (clock()-tt)


class ScrollingSpecgram():
    """
	The MatFileWriter class is a Post Processor class that writes data to file
	in the format of a Level-4 MAT File.
	"""

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config,logger):
        """
		Constructs the MatFileWriter object according to the supplied XML
		description.
		"""
        # Initialize data members

        params = {'adc_channel_number': read_config.GetIntElemVal(config, "adc_channel_number"),
                  'station_name':       read_config.GetStrElemVal(config, "station_name",'X'),
                  'station_id':         read_config.GetStrElemVal(config, "station_id",'XX'),
                  'NFFT':               read_config.GetIntElemVal(config, "NFFT",1024),
                  'fmin'              : read_config.GetDblElemVal(config, "fmin",0.0),
                  'fmax'              : read_config.GetDblElemVal(config, "fmax",50.0),   #[kHz]
                  'cmin':               read_config.GetDblElemVal(config, "cmin",-10.0),
                  'cmax':               read_config.GetDblElemVal(config, "cmax",70.0),
                  'duration':           read_config.GetIntElemVal(config, "Duration",10) #[seconds]
                  }

        self.logger = logger
        if params['duration']>60:
            self.logger.warning('Scrolling spectrogram can only be 60 seconds long; reducing duration to 60')
            params['duration'] = 60


        self.queue = Queue(5)
        plot_window = Process(target=launch_gui,args = (self.queue,params))

##        plot_window.setDaemon(True)
        plot_window.daemon = True
        plot_window.start()


    # =======
    # Methods
    # =======
    def Process(self, data):
        """
        Writes the received data to file as a Level-4 MAT File.
        bb data: data[0]

        """

        fs = data[2]
        current_time = data[1][0]
        try:
            self.queue.put([data[0],fs,current_time])
        except Full:
            self.logger.warning('ScrollingSpecgram: queue full')




# =========
# Unit Test
# =========
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    from xml.dom.minidom import parseString
    import numpy
    from datetime import datetime, timedelta
    import time as timemod
    import os

    # Create the Motorola GPS clock object
    settings = """
    <PostProcessor module="ScrollingSpecgram">
        <station_id>SU</station_id>
        <Duration>10</Duration>
        <station_name>Stanford</station_name>
        <adc_channel_number>111</adc_channel_number>
        <cmin>-20</cmin>
        <cmax>40</cmax>
        <fmax>20</fmax>
        <NFFT>1024</NFFT>
    </PostProcessor>
    """


    spec = ScrollingSpecgram(parseString(settings))
    L = 1   #[seconds]
    fs = 100e3
    t = np.arange(L*fs)/fs
    f0 = 10e3
    pha0 = 0
    time = datetime(year=2008, month=6, day=28, hour=11, minute=59, second=57)
    for i in range(45):
        rawBuffer = 100*np.sin(2*np.pi*(f0 + i*101)*t)
##        pha = 2*np.pi*(1/fs)*np.cumsum(.2*np.sin(2*np.pi*.5*t)) + pha0
##        pha0 = pha[-1]
##        rawBuffer = 100*np.sign(np.sin(2*np.pi*(60*t) + pha))   #60 Hz Hum

        SNR = 30
        sigPower = 10*np.log10(np.sum(np.abs(rawBuffer)**2)/len(rawBuffer))
        noisePower = 10**((sigPower-SNR)/10.0)
        rawBuffer += np.sqrt(noisePower)*np.random.randn(len(rawBuffer))
        rawBuffer = rawBuffer.astype(np.int16)
        data = [rawBuffer, [time, [0, 0, 0], [8]],fs]
        print "Processing for timestamp %s." % data[1][0]
        tt = timemod.clock()
        spec.Process(data)
##        print 'Time to display 1 second: %3.2f' % (timemod.clock()-tt)
        time += timedelta(seconds=1)
        t += L

        timemod.sleep(1)


##    spec.queue.join()