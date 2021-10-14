"""
Generates Spectrograms
"""
import os, sys
import os.path
sys.path.extend(['..'])


from datetime import datetime, timedelta
from time import sleep, clock, time
if os.name != 'nt':
    clock=time

##import enthought.traits.api as tr

from shutil import copyfile

#Using either threading or processing module:
#use_processing = True


#if(use_processing):
from multiprocessing import Queue, Process, Pool
#else:
#    from Queue import Queue, Full, Empty
#    from threading import Thread as Process

   
from Queue import Full, Empty

# import Image   # 5.2020 -- removing dependency on Pillow / PIL
import math as ma

# Numpy
import np_extensions as ne

#Hack for Scipy vs > 0.6
import scipy
import scipy.misc
scipy.factorial = scipy.misc.factorial

##from scipy.io import loadmat
from scipy.signal import firwin
from scipy.signal.filter_design import freqz
import scipy.fftpack as fft

# Matplotlib
from matplotlib import use as use_backend
use_backend('agg')  #don't use scrolling spectrogram at same time
from matplotlib.pyplot import figure

##from matplotlib import rcParams
from matplotlib.colorbar import make_axes, Colorbar

from utilities.loadMATdata import *
#note: to call from here, would need to do utilities.restart_counter
from utilities.restart_counter import Restart_counter
from utilities import read_config

from numpy.lib.stride_tricks import as_strided

#CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#print CURRENT_DIR
#sys.path.insert(0, CURRENT_DIR)

from __ver__ import __ver__

__all__ = ['Specgram']

#debug:
##np.seterr(all='raise')

try:
    import wx
    from VLFPanel import VLFPanel

    class GUIPanel(VLFPanel):
        def __init__(self, parent):
            VLFPanel.__init__(self, parent, "Specgram")
            self.widgets = {
                'adc_channel_number':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'0-999'),
                'DirectoryRoot':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'DirectoryRoot1':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'DirectoryRoot2':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'Duration':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Seconds]'),
                'Period':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Seconds]'),
                'psd':wx.Choice(self, wx.ID_ANY, size= self.DROP_BOOL_SIZE,choices = ['1','0']),
                'quality':wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),
                'NFFT':wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),
    ##            'fmin':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[kHz]'),
                'fmax':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[kHz]'),
                'cmin':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[dB]'),
                'cmax':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[dB]'),
                'remove_hum':wx.Choice(self, wx.ID_ANY, size= self.DROP_BOOL_SIZE,choices = ['1','0']),
                'f0':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Hz]'),
                'hum_fc':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Hz]'),
            }
            self.addWidgets()

except:
    print "WARNING: CAN'T IMPORT WX AND/OR VLFPanel"

#maybe expand on later:
##class params(tr.HasTraits):
##    adc_channel_number = tr.CInt(0,desc='DAQ channel number')
##    station_name = tr.CStr('X',desc='Station name')
##    station_id = tr.CStr('XX', desc = 'Receiver call sign')
##    Duration = tr.CInt(1,desc='Duration [seconds] of each spectrogram')
##    Period = tr.CInt(3600,desc='Period [seconds] between start of each spectrogram')
##
##    f0 = tr.CFloat(60.0, desc='Fundamental powerline frequency [50 or 60]')
##    NFFT = tr.CInt(1024, desc='FFT length for spectrogram')
##    fmin = tr.CFloat(0.0, desc='Minimum frequency in spectrogram plot [kHz]')
##    fmax = tr.CFloat(50.0, desc='Maximum frequency in spectrogram plot [kHz]')
##    cmin = tr.CFloat(-30.0, desc='Minimum dB amplitude in spectrogram plot')
##    cmax = tr.CFloat(50.0, desc='Maximum dB amplitude in spectrogram plot [kHz]')
##    psd = tr.Enum(1,0,desc='Specify whether or not to plot psd')
##
##    remove_hum = tr.Enum(0,1,desc='Specify whether or not to remove hum')
##    T_hum = tr.CFloat(0.5, desc='Length of hum removal window [seconds]')
##    hum_fc = tr.CFloat(2000, desc='Maximum frequency in hum removal [Hz]')
##
##    dpi = tr.CFloat(75, desc='Figure dpi')




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

class filt():
    def __init__(self,n,fs,h=None,filt_type='',window_type=''):


        if(h is not None):
            assert n==len(h)
        assert isinstance(filt_type,(unicode,str))
        assert isinstance(window_type,(unicode,str))
        assert isinstance(n,(int,float))
        assert isinstance(fs,(int,float))

        self.n = int(n+1e-10)  #number of taps
        self.fs = float(fs)    #sampling frequency
        self.h = h
        self.filt_type = filt_type
        self.window_type = window_type

        self._f = None  #frequency vector of frequency response
        self._H = None  #fft of h
        self._center = None
        self.angle_H = None




    def __len__(self):
        return self.n

    def clear_H(self):
        self._f = None
        self._H = None
        self._center = None
        self.angle_H = None

    def unit_allpass(self):
        self.n = 1
        self.h = np.array([1.0])
        self.filt_type = 'impulse'
        self.window_type='flat'
        self.clear_H()

    def delay(self,samples):
        """
        delays by samples
        """
        self.filt_type = 'delay'

        NFFT = 2.0**nextpow2(self.n)
        f_n = np.linspace(0,NFFT/2,NFFT/2+1)/(NFFT/2)
        H = np.zeros(NFFT/2.0+1) + 1

        fctr =np.exp(-1.0j*2.0*np.pi*np.linspace(0,NFFT/2,NFFT/2+1)/NFFT*((self.n-1)/2+samples))
        H = H*fctr
        H = np.hstack((H,np.fliplr([np.conj(H[1:-1])])[0]))#convert to matrix for fliplr
        h = np.real(fft.ifft(H))
        h = h[0:self.n]*np.hamming(self.n) #python stops at n-1
        self.window_type = 'hamming'

        #normalize to 1:
        H = fft.fft(h,NFFT)
        H = H/np.max(np.abs(H))
        h = np.real(fft.ifft(H))
        hr = h[0:self.n].copy()#insures contiguous array
        self.h = hr
        self.clear_H()



    def lowpass(self,f0,win = 'hanning'):
        self.filt_type = 'lowpass'
        self.window_type = win
        self.h = firwin(self.n,(float(f0)/(self.fs/2)),window = win)
        self.clear_H()

    def highpass(self,f0):
        self.filt_type = 'highpass'

        f0 = f0/(self.fs/2)

        NFFT = 2.0**nextpow2(self.n)
        f_n = np.linspace(0,NFFT/2,NFFT/2+1)/(NFFT/2)
        H = np.zeros(NFFT/2.0+1)

        H.put(np.where(f_n>=f0),1)

        fctr =np.exp(-1.0j*2.0*np.pi*np.linspace(0,NFFT/2,NFFT/2+1)/NFFT*(self.n-1)/2)
        H = H*fctr
        H = np.hstack((H,np.fliplr([np.conj(H[1:-1])])[0]))#convert to matrix for fliplr
        h = np.real(fft.ifft(H))
        h = h[0:self.n]*np.hamming(self.n) #python stops at n-1
        self.window_type = 'hamming'

        #normalize to 1:
        H = fft.fft(h,NFFT)
        H = H/np.max(np.abs(H))
        h = np.real(fft.ifft(H))
        hr = h[0:self.n].copy()#insures contiguous array
        self.h = hr
        self.clear_H()


    def getFreqResponse(self):
        assert self.h is not None

        if self._H is None:
            (w,self._H) = freqz(self.h)

            self._f = w/(2*np.pi)*self.fs

            if(len(self.h)%2==1):#odd
                self._center = (len(self.h)-1)/2.0
            else:
                self._center = len(self.h)/2.0

            self.angle_H =np.angle(self._H)+2*np.pi*self._f/self.fs*self._center    #[rad]


    def plot_h(self,ax):
        """
        pass in Axes object
        """
        self.getFreqResponse()

        t = np.array(range(len(self.h)),np.float)-self._center #[samples]

        ax.plot(t/self.fs*1e6,self.h)
        ax.grid(True)
        ax.set_xlabel('Time [$\mu$sec]')
        ax.set_ylabel('filter taps')
        ax.set_title('Window: ' + self.window_type)

    def plotMag(self,ax):
        """
        pass in Axes object
        """
        if(ax in [0,False,None]):
            return

        self.getFreqResponse()

        ax.plot(self._f,20*np.log10(np.abs(self._H)+1e-10))
        ax.grid(True)
        ax.set_xlabel('Frequency [Hz]')
        ax.set_title('Filter Response: Magnitude.  Window: %s' % str(self.window_type))
        ax.set_ylabel('dB')

    def filter(self,x):
        """
        Linear filtering - run time scales with tap length
        (uses double for loop in c)
        compensates for linear delay, assumes odd length filter with
        delay (n-1)/2
        """
        assert self.h is not None
        assert len(self.h)%2==1, 'length of h must be odd'  #assert odd
        x = np.ascontiguousarray(x)
        y = x.copy()
##        tmp = extensions.firfilter(x,self.h,y)
        tmp = ne.firfilter(x,self.h,y)

        y[:(self.n-1)/2] = 0
        y[len(y)-(self.n-1)/2:]=0
        return y

    def fftfilt(self,x,*n):
        """
        compensates for linear delay, assumes odd length filter with
        delay (n-1)/2

        Filter the signal x with the FIR filter described by the
        coefficients in b using the overlap-add method. If the FFT
        length n is not specified, it and the overlap-add block length
        are selected so as to minimize the computational cost of

        the filtering operation.
        """
        if len(self) < 20:          #use filter instead
            return self.filter(x)

        assert self.h is not None
        assert len(self.h)%2==1, 'length of h must be odd'  #assert odd

        N_x = len(x)
        N_b = len(self.h)

        # Determine the FFT length to use:
        if len(n):

            # Use the specified FFT length (rounded up to the nearest
            # power of 2), provided that it is no less than the filter
            # length:
            n = n[0]
            if n != int(n) or n <= 0:
                raise ValueError('n must be a nonnegative integer')
            if n < N_b:
                n = N_b
            N_fft = 2**nextpow2(n)
        else:

            if N_x > N_b:

                # When the filter length is smaller than the signal,
                # choose the FFT length and block size that minimize the
                # FLOPS cost. Since the cost for a length-N FFT is
                # (N/2)*log2(N) and the filtering operation of each block
                # involves 2 FFT operations and N multiplications, the
                # cost of the overlap-add method for 1 length-N block is
                # N*(1+log2(N)). For the sake of efficiency, only FFT
                # lengths that are powers of 2 are considered:
                N = 2**np.arange(np.ceil(np.log2(N_b)),np.floor(np.log2(N_x)))
                cost = np.ceil(N_x/(N-N_b+1))*N*(np.log2(N)+1)
                N_fft = N[np.argmin(cost)]

            else:

                # When the filter length is at least as long as the signal,
                # filter the signal using a single block:
                N_fft = 2**nextpow2(N_b+N_x-1)

        N_fft = int(N_fft)
##        print N_fft

        # Compute the block length:
        L = int(N_fft - N_b + 1)

        # Compute the transform of the filter:
        H = fft.fft(self.h,N_fft)

        cmplx = False
        if isinstance(x[0],np.complex):
            y = np.zeros(N_x,np.complex)
            cmplx = True
        else:
            y = np.zeros(N_x,np.float)


        offset = (N_b-1)/2  #compensate for filter delay
        i = offset
        while i <= N_x:
            il = min([i+L,N_x])
            k = min([i+N_fft,N_x])
            yt = fft.ifft(fft.fft(x[i:il],N_fft)*H) # Overlap..
            if cmplx:
                y[i-offset:k-offset] += yt[:k-i]        # and add
            else:
                y[i-offset:k-offset] += yt[:k-i].real        # and add
            i += L

        return y



class removeHum():

    def __init__(self,logger,Tamp=.6,Tskip=.05,Tint=.4, dB_thr=3,f0 = 60,fc = 4000,
                 plot_axes = (None,None,None), max_harm = 500,
                 ):
        """
        plot_axes:
        a 3-element tuple or list:
        1st element: harmonics from stft (None for no plot)
        2nd element: f0(t) (None for no plot)
        3rd element: hum (None for no plot)
        """
        assert isinstance(plot_axes,(tuple,list)), 'plot_axes needs to be a tuple or list'

        self.Tamp = Tamp
        self.Tskip =Tskip
        self.Tint = Tint
        self.dB_thr = dB_thr
        self.f0 = f0
        self.fc = fc
        self.plot_axes = plot_axes
        self.max_harm = max_harm
        self.logger = logger


    def __call__(self,x,fs):

        """ removes powerline harmonics """
        #downsample to run faster:

        Q = int(max(np.floor(fs/2.0/(self.fc*1.3)),1))
##        print Q
        if Q > 1:
            nfilt = 351
            h = filt(nfilt,fs)
            f0 = self.fc*1.1
            h.lowpass(f0,win = ('kaiser',2.5))
            y = h.fftfilt(x)
    ##        h.plotFreqResponse(752)
    ##        print Q, fs/Q
            y = y[::Q]
            #print 'downsample time: ', clock()-t1
##            print 'New fs for isolate hum: %3.2f' % (fs/Q)
        else:
            y = x


        y = self._isolateHum(y,fs/Q)


        #upsample
        if Q > 1:
            h = filt(nfilt,fs)
            h.lowpass(f0,win= ('kaiser',2.5))
    ##        h.plotFreqResponse(753)
            hum = np.zeros(len(x))
            hum[::Q] = y
            hum = Q*h.fftfilt(hum)
        else:
            hum = y

        self.hum = hum  #for computing snr improvement in thesis

        if(hum.size==x.size):
            return x - hum
    ##        return x-hum,var_x,var_y,var_z  #for test_removeHumGrid
        elif(hum.size>x.size):
            return x - hum[:x.size]
    ##        return x - hum[:x.size],var_x,var_y,var_z #for test_removeHumGrid
        else:   #length of hum less than lenght of x
            tmp = x.copy()
            tmp[:hum.size] = tmp[:hum.size]-hum
            return tmp
    ##        return tmp,var_x,var_y,var_z #for test_removeHumGrid


    def _track_freq_STFT(self,x,fs):


        harm = np.arange(1,min(13,self.max_harm),1.0)
        max_freq = harm[-1]*self.f0

##        print 'starting fs: %3.1f' % fs

        #downsample to run faster:
        Q = int(max(np.floor(fs/2.0/(max_freq*1.8)),1))
##        print Q,fs,max_freq
        if Q > 1:
            nfilt = 151
            h = filt(51,fs) 
            f0 = max_freq*1.3
            h.lowpass(f0,win = ('kaiser',5))
            y = h.filter(np.ascontiguousarray(x))
    ##        h.plotFreqResponse(751)
            y = y[::Q]
            fs /= Q
        else:
            y = x.copy()

##        print 'max_freq; ending fs: %3.1f, %3.1f' % (max_freq,fs)

        #integration time, rounded to upper power of 2:
        NFFT = 2**(nextpow2(self.Tamp*fs)+1)
        #interval to calculate f0:

        skip = np.round(self.Tskip*fs)

        win_len = int((self.Tamp - 0.0/self.f0)*fs)
        window = gausswin(win_len,2.5)
        noverlap = win_len-skip

        stft = STFT(self.logger,y,fs,NFFT,noverlap,window)
        sample_df = stft.get_df()
##        print self.Tamp*fs, NFFT, stft.t
        tone_adjust = -20.0*np.log10(stft.win.sum()/2.0)

        df = 2.0

        imin = np.asarray((harm*(self.f0-df)*NFFT/fs).round(),dtype=np.int)
        imax = np.asarray((harm*(self.f0+df)*NFFT/fs).round(),dtype=np.int)

        Fpeak = np.zeros(len(harm))
        Bpeak = np.zeros(len(harm))

        f_0 = np.zeros(len(stft.t))
        for aa in range(0,len(stft.t),1):
            BdB = 20.0*np.log10(np.abs(stft.z[aa,:])+1e-10) + tone_adjust
            for ii in range(len(harm)):
                ipeak = np.where(BdB[imin[ii]:imax[ii]]==np.max(BdB[imin[ii]:imax[ii]]))[0][0]+imin[ii]
                x0,Bpeak[ii] = calcQuadPeak(BdB[ipeak-1],BdB[ipeak],BdB[ipeak+1])
                Bpeak[ii] = 10**(Bpeak[ii]/20)  #don't use dB for weighting!! (may be negative) -- convert back to linear units
                Fpeak[ii] = stft.f[ipeak] +sample_df*x0
                #if deviate too much, throw out:
                if ma.fabs(sample_df*x0) > df*harm[ii]:  #make sure peak is in the interior
                    Bpeak[ii] = -1000   #[small dB  value]
                    Fpeak[ii] = stft.f[ipeak]   #return to initally constrained peak

            Fapprox = Fpeak/harm
            maxPeak = np.max(Bpeak)
            itmp = np.where(Bpeak>maxPeak-self.dB_thr)[0]

            if len(find_nan(f_0))>0:
                #print 'Found NaN, setting f_0[aa] to %2.1f' % self.f0
                self.logger.error('Found NaN, setting f_0[aa] to %2.1f' % self.f0)
##                print Fapprox,Bpeak, itmp
##                raise 'found NaN'
                f_0[aa] = self.f0
            else:
                f_0[aa] = np.sum(Fapprox[itmp]*Bpeak[itmp]*harm[itmp])/np.sum(Bpeak[itmp]*harm[itmp])

        if self.plot_axes[0] is not None:
            ax = self.plot_axes[0]
            F,tone_height = stft.avg_tone_height()
            ax.plot(F,20*np.log10(tone_height))

            ax.plot(Fpeak[itmp],20*np.log10(Bpeak[itmp]),'ro')
            ax.grid(True)
            ax.set_xlabel('Frequency [Hz]')
            ax.set_title('Magnitude [dB] vs Frequency')

        if self.plot_axes[1] is not None:
            ax = self.plot_axes[1]
            ax.plot(stft.t,f_0,label = 'stft')
            ax.set_title('Fundamental Powerline Frequency')
            DF = .3
            v = [stft.t[0],stft.t[-1],self.f0-DF,self.f0+DF]
            ax.axis(v)
            ax.grid(True)
            ax.set_xlabel('Time [sec]');
            ax.set_ylabel('f0 [Hz]')
            ax.legend()



        return (stft.t,f_0)


    def _isolateHum(self,x,fs):
        """
        Isolates hum from ~ [Tint/2] to [(the duration of x) - Tint/2]
        Tamp determines each FFT length (which determines f0)
        Tskip determines how often f0 is updated
        """

        DF_MAX = 5  #Hz -- maximum deviation from center HUM frequency

        (T,f_0) = self._track_freq_STFT(x,fs)

        self.t_f0 = T
        self.f_0 = f_0


        f_0 = f_0.clip(self.f0-DF_MAX,self.f0+DF_MAX) #ADDED 1/10/09

        #index into time vector corresponding to x (need f_0, T to get f_0x)
        t = np.linspace(0,len(x)-1,len(x))/fs

        dt1 = t[1]-t[0]
        dt2 = T[1]-T[0]

        i2 = (t[0]-T[0])/dt2 + np.arange(0,len(x),1.0)*dt1/dt2
        i2 = np.clip(i2,0,len(T)-1)
        f_0x = linInterpValue(f_0,i2)



        #integration length to extract powerline harmonic terms:
        M = np.round(self.Tint*self.f0/2)-1

        index = np.linspace(-M,M,2*M+1)*fs #[s^-1]

        #Choose window:
        win = np.hanning(len(index))
        y = f_0x.copy()    # no need for a new vector


        min_f0 = np.min(f_0x)
        ii_lower = int(np.round((M+1)*fs/min_f0))+1
        ii_upper = len(x)-int(np.round((M+1)*fs/min_f0))-1

        #convert to C:
        ne.delta_filt(x.copy(),index,win,y,ii_lower,ii_upper)


        y[:ii_lower] = 0
        y[ii_upper:] = 0

        return y




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


    def __init__(self,logger,x,fs,NFFT=1024,noverlap=512,win=None):
        """
        hamming window applied by default; may specify win
        fields: (t,f,z)
        """
        self.iscomplex = False
        if isinstance(x[0],np.complex):
            self.iscomplex = True

        axis = None
        end = 'pad'
        endvalue = 0
        if win is None:
            win = np.hamming(NFFT)
        framelen = len(win)
        self.segment_axis(x,framelen,noverlap,axis,end,endvalue)


        #keep everything but data:
        self.framelen = framelen
        self.noverlap = noverlap
        self.NFFT = int(NFFT)
        self.win = win
        self.fs =fs
        self.t = (np.linspace(0,self.z.shape[0]-1,self.z.shape[0])*(framelen-noverlap) + (framelen-1)/2)/fs
        self.f = np.arange(float(NFFT))*fs/NFFT
        #do one column at a time so as not to stress the memory usage or hog cpu cycles:
        if len(self.z[0])==NFFT:
            for ii in range(self.z.shape[0]):
                self.z[ii] = fft.fft(self.z[ii]*win,self.NFFT)
        else:
            self.z = fft.fft(self.z*win,self.NFFT)

        #make sure no 0's in fft (so no 0 in log10 calls):
        self.z += 1e-10

        self.mag_cal = None

        self.logger = logger

    def read_out_params(self):
        return (self.fs, self.NFFT,self.noverlap, self.win)

    def __str__(self):
        return 'Time: %2.2f-%2.2f; Freq: %2.2f-%2.2f' % (self.t.min(),self.t.max(),self.f.min(),self.f.max())

    def get_df(self):
        return self.f[1] - self.f[0]

    def psd_dB(self,double_sided=False):
        """
        (F,PSD_dB) = psd_dB(...)
        Calculates single-sided PSD (units of dB/Hz)
        Gives Watts/Hz: (or, rather, dB-Watts/Hz; to recover Watts of noise floor,
        calculate 10**(noise_floor_in_dB/10)*(fs/2)
        """
        if(double_sided):
            upper_f_index = self.NFFT/2+1

            z = np.sqrt(np.abs(self.z)**2/np.sum(self.win**2)/self.fs)
            z[:,1:self.NFFT/2] *= np.sqrt(2.0)  #Don't multiply DC or nyquist by 2 (or sqrt(2) for psd)
            z[:,self.NFFT/2+1:] *= np.sqrt(2.0)
            z = 10*np.log10(np.mean(z**2,0));  #Take average (welch's method) (units: dB-pT/rt-Hz)

            f = self.f.copy()
            f[self.NFFT/2:] -= self.fs
            return (np.fft.fftshift(f),np.fft.fftshift(z))
        else:
            upper_f_index = self.NFFT/2+1

            z = np.sqrt(np.abs(self.z[:,:upper_f_index])**2/np.sum(self.win**2)/self.fs)
            z[:,1:self.NFFT/2] *= np.sqrt(2.0)  #Don't multiply DC or nyquist by 2 (or sqrt(2) for psd)
            z = 10*np.log10(np.mean(z**2,0)+1e-10);  #Take average (welch's method) (units: dB-pT/rt-Hz)

            return (self.f[:upper_f_index],z)

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

    def specgram(self,axes,clim=None,cmap = None,tlim = None,flim=None,cal_f_mag=None):
        """
        if tlim [sec] is not None, will limit t range
        if flim [kHz] is not None, will limit f range
        """

        upper_f_index = self.NFFT/2+1

        z = np.abs(self.z[:,:upper_f_index])/self.win.sum()

        z[:,1:self.NFFT/2] *= 2.0

        if os.path.isfile('ZERO_Z_IN_SPEC.DEBUG'):
            z =z*0.0 + 1.0

        freqs = self.f[:upper_f_index]  #Hz

        #if add spectral calibration--do here
        if cal_f_mag is not None:

            #Linear interpolate magnitude on frequencies freqs:
            L_mag = len(cal_f_mag[1])
            if self.mag_cal is None:
                self.mag_cal = np.ones(len(freqs))
                for ii in xrange(len(freqs)):
                    if freqs[ii] < cal_f_mag[0][0]*1e3:
                        index_f = 0
                    elif freqs[ii] >= cal_f_mag[0][-1]*1e3:
                        index_f = L_mag-1
                    else:
                        index_f = self.linInterpInv(cal_f_mag[0]*1e3,freqs[ii])[0]

                    self.mag_cal[ii] = linInterpValue(cal_f_mag[1],index_f)

        if self.mag_cal is not None:
            #multiple each row of z by interpolated linear magnitude
            for ii in xrange(len(z)):
                z[ii] = z[ii]*self.mag_cal

##        print 'Len mag_cal, first two elements: %d, %2.3f, %2.3f' % (len(self.mag_cal),self.mag_cal[0],self.mag_cal[1])
##        print 'Max/min mag_cal: %2.3f, %2.3f' % (np.max(self.mag_cal), np.min(self.mag_cal))
##        print 'Max/min/mean z: %2.3f, %2.3f, %2.3f' % (np.max(z), np.min(z), np.mean(z))


        #----------------------------------
        z = 20*np.log10(np.flipud(np.transpose(z)) + 1e-10)
        (extent,z) = self.get_tf_extent(z,freqs,tlim,flim)

        if os.path.isfile('ZERO_Z_IN_SPEC.DEBUG'):
            if self.mag_cal is not None:
                #print 'Median z: %3.2f; cal_f_mag: %3.2f; mag_cal: %3.2f' % (np.median(z,0)[0], np.median(cal_f_mag[1]), np.median(self.mag_cal))
                self.logger.info('Median z: %3.2f; cal_f_mag: %3.2f; mag_cal: %3.2f' % (np.median(z,0)[0], np.median(cal_f_mag[1]), np.median(self.mag_cal)))

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
        tmin = 0
        tmax = np.amax(self.t)
        fmin = freqs[0]/1e3
        fmax = freqs[-1]/1e3

        if tlim is not None:    #restrict time range
            ii_lo,slope = self.linInterpInv(self.t,tlim[0])
            ii_hi,slope = self.linInterpInv(self.t,tlim[1])
            if len(ii_lo)==0:
                ii_lo = 0
            else:
                ii_lo = int(ii_lo[0])
            if len(ii_hi)==0:
                ii_hi = len(self.t)-1
            else:
                ii_hi = int(ii_hi[0])

            z = z[:,ii_lo:ii_hi+1]
            tmin,tmax = self.t[ii_lo],self.t[ii_hi]

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
        if overlap<0 or length<=0:
            raise ValueError, "overlap must be nonnegative and length must be positive"

        if l<length or (l-length)%(length-overlap):
            if l>length:
                roundup = length + (1+(l-length)//(length-overlap))*(length-overlap)
                rounddown = length + ((l-length)//(length-overlap))*(length-overlap)
            else:
                roundup = length
                rounddown = 0
            assert rounddown<l<roundup
            assert roundup==rounddown+(length-overlap) or (roundup==length and rounddown==0)

            roundup = int(roundup)
            rounddown = int(rounddown)
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
        n = int(1+(l-length)//(length-overlap))
        s = a.strides[axis]
        newshape = a.shape[:axis]+(n,length)+a.shape[axis+1:]
        newstrides = a.strides[:axis]+(int((length-overlap)*s),s) + a.strides[axis+1:]

        try:
            
            self.z = np.ndarray.__new__(np.ndarray,strides=newstrides,shape=newshape,buffer=a,dtype=a.dtype).astype(np.complex)
        except TypeError:
            a = a.copy()
            # Shape doesn't change but strides does
            newstrides = a.strides[:axis]+(int((length-overlap)*s),s) + a.strides[axis+1:]
            self.z = np.ndarray.__new__(np.ndarray,strides=newstrides,shape=newshape,buffer=a,dtype=a.dtype).astype(np.complex)

        except:
            #self.logger.exception("Some exception happened.")
            #print "
            raise
            
            
class Specgram:
    """
    Generates spectrograms
    """

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config, logger):
        """

        """
        # Initialize data members
        self.filename = None
        self.fileStart = None
        self.startTime = None
        self.last_time = None
        self.logger = logger


        self.already_saved = True

        # Read channel header information
        overwrite_names = []
        self.directoryRoots = []
        no_dir_default = 'X3@X-+#@!3blablabla'
        for ii in ['','0','1','2','3','4','5','6','7','8','9']:
            write_dir = read_config.GetStrElemVal(config, "DirectoryRoot%s" % ii,no_dir_default)
            if write_dir != no_dir_default:
                (adir,overwrite) = self.parseDirectory(write_dir)
                if not os.path.isdir(adir):
                    os.makedirs(adir)

                self.directoryRoots.append(adir)
                overwrite_names.append(overwrite)



        self.adc_channel_number = read_config.GetIntElemVal(config, "adc_channel_number")
        self.station_name 		= read_config.GetStrElemVal(config, "station_name",'X')
        self.station_id         = read_config.GetStrElemVal(config, "station_id",'XX')
        self.synoptic_duration  = read_config.GetIntElemVal(config, "Duration",1)
        self.file_duration      = read_config.GetIntElemVal(config, "Period",3600)

        #Hum removal:
        f0                      = read_config.GetDblElemVal(config, "f0",60.0) #[Hz]
        NFFT                    = read_config.GetIntElemVal(config, "NFFT",1024)
        fmin                    = read_config.GetDblElemVal(config, "fmin",0.0)
        fmax                    = read_config.GetDblElemVal(config, "fmax",50.0)   #[kHz]
        cmin                    = read_config.GetDblElemVal(config, "cmin",-30.0)
        cmax                    = read_config.GetDblElemVal(config, "cmax",50.0)
        plot_psd                = read_config.GetIntElemVal(config, "psd",0)

        remove_hum              = read_config.GetIntElemVal(config, "remove_hum",1)
        Tamp                    = read_config.GetDblElemVal(config, "T_hum",0.5)
        fc                      = read_config.GetDblElemVal(config, "hum_fc",2000) #[Hz]

        quality_jpg             = read_config.GetIntElemVal(config, "quality",75)

        self.x = None
        self.start_index = None
        self.num_samples = None

        self.queue = Queue(10) # Queue(3)  # APS 5.2018. Attempting to fix "Queue full" errors after ~2 days of running 
                
        self.asyncSave = Process(target=AsyncSave, args=(self.queue, self.adc_channel_number, NFFT, fmin, fmax, cmin, cmax, plot_psd, f0, remove_hum, Tamp, fc, overwrite_names, quality_jpg, self.logger))


##        asyncSave.setDaemon(True)
        self.asyncSave.daemon = True

        self.asyncSave.start()
        #print 'Spectrogram process for Channel %d started on pid: %d' % (self.adc_channel_number,asyncSave.pid)
        self.logger.debug('Spectrogram process for Channel %d started on pid: %d' % (self.adc_channel_number,self.asyncSave.pid))


    # =======
    # Methods
    # =======
    def Process(self, data):
        """
        Runs Spectrogram routine

        data = [[chNData], [dt,[lat,lon,alt],[quality]], sampleRate]
        """

        # Check contiguous
        cur_time = data[1][0]
        
        self.fs = data[2]
        
        if self.x is None:
            self.x = np.ones(self.synoptic_duration*self.fs,data[0].dtype)

            self.num_samples = self.fs
            self.start_index = 0

        if self.TimeToStartNewFile(data[1][0]):
            self.save_specgram()
            self.already_saved = False
            self.fileStart = data[1][0]

            self.filenames = []
            
            for adir in self.directoryRoots:
                self.filenames.append("%s/%s%s_%03d.jpg" % (adir, self.station_id, self.fileStart.strftime("%y%m%d%H%M%S"),self.adc_channel_number))


        #NOTE: On first acquisition period, synoptic recording may extend beyond normal cutoff time
        if(cur_time-self.fileStart < timedelta(seconds=self.synoptic_duration)):

            #verify data stream contiguous:
            if self.last_time is not None:
                td = cur_time - self.last_time
                td = td.days*86400 + td.seconds + td.microseconds*1e-6
                
                #self.logger.info(int(round(td)))
                
                if int(round(td)) is not 1:
                    # better solution is to detect non-contiguous portion and add blank data
                    
                    self.logger.warning("Detected data non-contiguous. Closing current file")
                    self.save_specgram()
                    self.already_saved = False
                    self.last_time = cur_time
                    return 0
                    
            #still building up data:
##            print self.start_index,self.start_index+self.num_samples,len(data[0])
            try:
                self.x[self.start_index:self.start_index + self.num_samples] = data[0]
##                print 'min/max/len when added: %d, %d, %d' % (np.min(data[0]),np.max(data[0]),len(data[0]))
            except Exception, inst:
##                print self.start_index,self.start_index+self.num_samples,len(data[0])
                #self.logger.error("Specgram: unexpected length of data: %d versus %d, starting at %d" % (len(data[0]),self.num_samples,self.start_index))
                self.logger.exception("Specgram: unexpected length of data: %d versus %d, starting at %d" % (len(data[0]),self.num_samples,self.start_index))
                raise inst
            self.start_index += self.num_samples
        else:   #if duration is less than period:
            self.save_specgram()

        self.last_time = cur_time                               
            
        return 0

    def Stop(self):
        self.logger.debug("Stopping Spectrogram process.")
        self.queue.put(["Stop"])
        self.asyncSave.join()
        self.logger.status("Stopped spectrogram process.")
        
        
    # ==============
    # Helper Methods
    # ==============
    def TimeToStartNewFile(self, timestamp):
        if self.fileStart is None:
            return True
        beginningOfDay = datetime(year=timestamp.year, month=timestamp.month, day=timestamp.day)
        if ((timestamp-beginningOfDay).seconds % self.file_duration) == 0:
            return True
        if (timestamp - self.fileStart) >= timedelta(seconds=self.file_duration):
            return True
        return False


    def parseDirectory(self,dir_string):
        index_comma = dir_string.rfind(',')
        if index_comma==-1: #just a directory
            return(dir_string,None)
        else:
            return (dir_string[:index_comma],dir_string[index_comma+1:])

    def save_specgram(self):
    
        self.logger.debug("Saving Spectrogram.")
    
        if self.already_saved is True:
            return False

        self.x[self.start_index:] = 1e-6
        #Put the data in the queue
        try:
##            print self.x.dtype
            self.queue.put([self.x.copy(), self.fs, self.fileStart, self.filenames, self.adc_channel_number, self.station_name], block=False)

##            dumpname = '%s%d' % (self.fileStart.strftime('specdump%Y%m%d%H%M%S'),self.adc_channel_number)
##            self.x.dump(dumpname)
##            self.queue.put([dumpname,self.fs,self.fileStart,self.filenames,self.adc_channel_number, self.station_name],block=False)

        except Full:
            self.logger.warning('Specgram: Queue full.')
        except Exception, exc:
        
            #self.logger.error('Specgram: Unexpected error encountered when posting data to queue: %s' % exc)
            self.logger.exception('Specgram: Unexpected error encountered when posting data to queue.')
            self.logger.warning('RAM may be limiting factor; try reducing Specgram duration')
            
##        self.time_offset = timedelta(0,0)
        self.already_saved = True
        self.start_index = 0
        
        
        return True

##class AsyncSave(Thread):
def AsyncSave(queue,ch_number,NFFT,fmin,fmax,cmin,cmax,plot_psd,f0,remove_hum,Tamp,fc,overwrite_names,quality_jpg, logger):
    """
    Note: at development time (10/17/09), TkAgg backend will not serialize properly if AsyncSave is a class (not sure why)
    Therefore, AsyncSave was made into a function
    """

    restart_counter = None
    if Restart_counter is not None:
        restart_counter = Restart_counter()

    wait_time = 10

    specgram_title = 'Stanford ELF/VLF/LF'
    
    title_file = 'specgram_title.txt'
    
    if os.path.isfile(title_file):
        fid = open(title_file,'r')
        specgram_title = fid.read(-1)
        fid.close()

    #load calibration if exists
    cal_f_mag = None
    cal_filename = 'CalibrationVariables.mat'
    
    if os.path.isfile(cal_filename):
        try:
            CH = None
            if ch_number==0:
                CH = 'NS'
            elif ch_number==1:
                CH = 'EW'

            if CH is not None:
                varname = 'CalibrationNumber%s' % CH
                cal_f_mag = []
                mat = loadMATdata(cal_filename)
                s = mat.loadData([varname],[-1],[0])
                cal_f_mag.append(np.real(s[varname][:,0]))    #kHz
                cal_f_mag.append(np.abs(s[varname][:,1]))    #linear mag

                #saturate mag response:
                medm = np.median(cal_f_mag[1])
                minm = medm*10**(-10.0/20.0)
                maxm = medm*10**(10.0/20.0)
                cal_f_mag[1][cal_f_mag[1]<minm] = minm
                cal_f_mag[1][cal_f_mag[1]>maxm] = maxm

                #print 'Successfully loaded calibration data for Channel %s' % CH
                logger.info('Successfully loaded calibration data for Channel %s' % CH)
        except:
            cal_f_mag = None
            #print 'Could not properly load cal data'
            logger.exception( 'Could not properly load cal data')


    if os.name=='posix':
        os.nice(2)  #decrease process priority

    plot_psd = plot_psd>0
    
    remove_mean = True

##    print 'Figure set up'
    #logger.debug("Figure setup complete.")

    remove_hum = remove_hum>0
    Tskip=Tamp/2.0
    Tint=Tamp
    dB_thr=3

    last_queue_size = 0
    firstLoop = True
    psd_line = None
    im = None

    #l,b,w,h
    if plot_psd:
        #fig = figure(ch_number+1,figsize=(10,6), dpi=100)
        fig = figure(ch_number+1,figsize=(12.8,7.2), dpi=100) # going HD 1280x720
        ax = fig.add_axes([.055,.075,.50,.85]) #Main plot
        cax = fig.add_axes([.570,.075,.025,.85]) #colarbar
        pax = fig.add_axes([.675,.075,.30,.85]) #PSD
        pax.hold(True)
        fontsize = 12
    else:
        #fig = figure(ch_number+1,figsize=(11,4.5), dpi=100)
        fig = figure(ch_number+1,figsize=(12.8,7.2), dpi=100) # going HD 1280x720
        ax = fig.add_axes([.055,.075,.85,.85]) 
        cax = fig.add_axes([.930,.075,.025,.85])
        fontsize = 12

    fig.set_facecolor('w')
    fig.set_edgecolor('w')

    block_num = -1
    
    logger.info("Figure setup complete.")
    
    sleep(30)

    while True:

        try:
            data = queue.get(timeout=wait_time)     # Pull this second's timestamp from the GPS clock
            block_num += 1
##            print 'Got queue element %d' % block_num
        
            """
            data = [self.x.copy(), self.fs, self.fileStart, self.filenames, self.adc_channel_number, self.station_name]
            """

        except Empty:
            
            # If no data comes through in *wait_time*, something is wrong in the data collection process. pass??
            
            """
            if restart_counter is None:
                logger.error('Waiting for %d seconds, quitting Specgram AsyncSave process ' % wait_time)
                sleep(wait_time)
                break

            elif restart_counter.check():
                pass

            else:
                #print 'Restart counter did not check out (should be: %s; new value: %s), quitting Specgram AsyncSave process' %(restart_counter.current_value(),restart_counter.peek())
                logger.error('Restart counter did not check out (should be: %s; new value: %s), quitting Specgram AsyncSave process' %(restart_counter.current_value(),restart_counter.peek()))
                break
            """
            #logger.warning('Waiting for %d seconds, quitting Specgram AsyncSave process ' % wait_time)
            continue
            
        except Exception:
            #print 'Unexpected error when reading from Specgram Queue: %s' % exc
            logger.exception('Unexpected error when reading from Specgram Queue.')
            #print 'RAM may be limiting factor; try reducing Specgram duration'
            #logger.warning('RAM may be limiting factor; try reducing Specgram duration')
            continue

##        bbdata = np.load(data[0]).astype(np.float64)
##        os.remove(data[0])

        if len(data) == 1:
            # This is a command
            if data[0] == "Stop":
                logger.info("Exiting Spectrogram save.")
                return

        # wait some time to stagger channel processing
        sleep((data[4]%5)*2)
        
        tt = clock()
       

        data[0] = data[0].astype(np.float64)
##        print 'raw: ', data[0][:5]

        #lowpass filter:
        do_decimate = False
        
        fs = float(data[1])
        
        if (fmax*1e3 > fs/4.0*.9):
            dec_fctr = 1
        elif (fmax*1e3 <= fs/4.0*.9) and (fmax*1e3 > fs/8.0*.9):  #decimate by 2
            do_decimate = True
            dec_fctr = 2
            fc_dec = fs/4.0*.95
        elif (fmax*1e3 <= fs/8.0*.9) and (fmax*1e3 > fs/16.0*.9):  #decimate by 4
            do_decimate = True
            dec_fctr = 4
            fc_dec = fs/8.0*.95
        else: #decimate by 8
            do_decimate = True
            dec_fctr = 8
            fc_dec = fs/16.0*.95

        if do_decimate:
            h_dec = filt(351,fs)
            h_dec.lowpass(fc_dec)
            data[0] = h_dec.fftfilt(data[0])[::dec_fctr]

##            print dec_fctr,fc_dec,fs
            logger.debug('dec_fctr: %s, fc_dec: %s, fs: %s' % (dec_fctr,fc_dec,fs))
##        print 'Data: ', data[0][:5]

##        if os.path.isfile('DEBUG.specgram')
##        print 'min/max/len in async save: %4.3f, %4.3f, %d' % (np.max(data[0]),np.min(data[0]),len(data[0]))

        logger.debug('min/max/len in async save: %4.3f, %4.3f, %d' % (np.max(data[0]),np.min(data[0]),len(data[0])))

        #remove mean:
        if remove_mean:
            data[0]-=np.mean(data[0])
            
        #remove hum
        if remove_hum:
            try:
                rh = removeHum(logger,Tamp,Tskip,Tint,dB_thr,f0,fc,plot_axes=(None,None,None))
                data[0] = rh(data[0],fs/dec_fctr)
                del(rh)
            except:
                #print 'Something went wrong with hum removal'
                logger.exception('Something went wrong with hum removal')

        stft = STFT(logger, data[0], fs/dec_fctr, NFFT=NFFT/dec_fctr, noverlap=NFFT/dec_fctr/2)

        im = stft.specgram(ax, clim =[cmin,cmax], flim=[fmin,fmax], cal_f_mag=cal_f_mag)

        if firstLoop:
            Colorbar(cax, im)
            if cal_f_mag is not None:
                cax.set_title('dB-pT',size=fontsize)
            else:
                cax.set_title('dB (raw)',size=fontsize)
            cax.set_xlabel('\n\nv. %s' % __ver__, size=8)
            
            for tic in cax.yaxis.get_major_ticks():
                tic.label1.set_fontsize(fontsize)

            ax.set_ylabel('Frequency [kHz] ($\Delta$f = %3.2f Hz)' % stft.get_df(),size=fontsize)
            ax.set_title('%s; Channel %d (%s)' % (data[5],data[4],specgram_title),size=fontsize)
            
            for tic in ax.xaxis.get_major_ticks():
                tic.label1.set_fontsize(fontsize)
            for tic in ax.yaxis.get_major_ticks():
                tic.label1.set_fontsize(fontsize)

        ax.set_xlabel('Seconds after %s [UT]' % data[2],size=fontsize)

        if plot_psd:

            (F,PSD_dB) = stft.psd_dB()

            if firstLoop:
                psd_line = pax.plot(F/1e3,PSD_dB,'b',scalex=False,scaley=False)
                
                # set graph axis and labels
                pax.set_xlabel('Frequency [kHz]', size=fontsize)
                pax.set_ylabel('PSD [dB-raw/rt-Hz)',size=fontsize)
                
                for tic in pax.xaxis.get_major_ticks():
                    tic.label1.set_fontsize(fontsize)
                    
                for tic in pax.yaxis.get_major_ticks():
                    tic.label1.set_fontsize(fontsize)

                pax.set_ylim(-90,40)
                #pax.set_ylim(cmin,cmax) # set PSD range to match colorbar range
                
                pax.set_xlim(0,np.ceil(F[-1]/1e3))
            else:
                psd_line[0].set_data(F/1e3,PSD_dB)

        try:
            filenames = data[3]
            fig.canvas.draw()

            #Retrieve overwrite names and delete files if necessary:
            for i,afile in enumerate(filenames):
                if overwrite_names[i] is not None:
                   (head,tail) = os.path.split(afile)
                   filenames[i] = os.path.join(head,overwrite_names[i])
                   if os.path.isfile(filenames[i]):
                       os.remove(filenames[i])

            #Save figure to disk and copy to other locations
            # 5.6.2020 -- using matplotlib's save function -- seems identical, 
            # and means one less library to deal with (pillow / PIL)
            fig.canvas.print_figure(filenames[0],dpi=100, quality=quality_jpg)

            # image_size = fig.canvas.get_width_height()
            # imageRgb = fig.canvas.tostring_rgb()
            # pilImage = Image.frombytes("RGB",image_size,imageRgb)
            # pilImage.save(filenames[0],quality=quality_jpg)
            logger.info("Wrote: %s" % filenames[0])
            
            for i,afile in enumerate(filenames):
                if i > 0:
                    copyfile(filenames[0],filenames[i]) #copy from first filename

        except Exception, err:
            #print 'Something went wrong with figure saving: %s' % err
            logger.exception('Something went wrong while saving figure.')


        ax.images.remove(im)
        del(im)
        del(stft)
        data[0] = np.array([])
        firstLoop = False
        
##        print 'Processed queue element %d' % block_num
##        self.queue.task_done()

##        print 'Async save time: %3.2f seconds' % (clock()-tt)
        logger.debug('Block #%d in %3.2f s' % (block_num, clock()-tt))

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
    import logging
    logger = logging.getLogger('')

    # Create the Motorola GPS clock object
    settings = """
    <PostProcessor module="Specgram">
        <DirectoryRoot>../../Data,latestNS.png</DirectoryRoot>
        <DirectoryRoot1>.,latestNS.png</DirectoryRoot1>
        <station_id>SU</station_id>
        <Duration>60</Duration>
        <station_name>Stanford</station_name>
        <adc_channel_number>111</adc_channel_number>
        <Period>60</Period>
        <cmin>-20</cmin>
        <cmax>40</cmax>
        <fmax>20</fmax>
        <NFFT>8192</NFFT>
        <psd>1</psd>
        <remove_hum>1</remove_hum>
        <T_hum>.3</T_hum>
        <dpi>50</dpi>
    </PostProcessor>
    """


    spec = Specgram(parseString(settings),logger)
    L = 1   #[seconds]
    fs = 100e3
    t = np.arange(L*fs)/fs
    f0 = 10e3
    pha0 = 0
    time = datetime(year=2008, month=6, day=28, hour=11, minute=59, second=57)
    for i in range(123):
##        rawBuffer = 100*np.sin(2*np.pi*(f0 + i*100)*t)
        pha = 2*np.pi*(1/fs)*np.cumsum(.2*np.sin(2*np.pi*.5*t)) + pha0
        pha0 = pha[-1]
        rawBuffer = 100*np.sign(np.sin(2*np.pi*(60*t) + pha))   #60 Hz Hum

        SNR = 30
        sigPower = 10*np.log10(np.sum(np.abs(rawBuffer)**2)/len(rawBuffer))
        noisePower = 10**((sigPower-SNR)/10.0)
        rawBuffer += np.sqrt(noisePower)*np.random.randn(len(rawBuffer))
        data = [rawBuffer, [time, [0, 0, 0], [8]],fs]
##        print "Processing for timestamp %s." % data[1][0]
        spec.Process(data)
        time += timedelta(seconds=1)
        t += L

    timemod.sleep(20)
##    spec.queue.join()