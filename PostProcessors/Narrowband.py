"""
Demodulates NB channels to track the amplitude and phase
Uses new method developed by Ryan K Said, March 2011
"""

from datetime import datetime, timedelta
import os.path
import os
from time import sleep, clock, time
if os.name != 'nt':
    clock=time
from shutil import copyfile
import sys
sys.path.append(['..'])
#import scipy.io as sio
from xml.dom.minidom import parseString
from ConfigParser import ConfigParser

from scipy.signal import firwin
import scipy.fftpack as fft

#Using either threading or processing module:
use_processing = True

if(use_processing):
    from multiprocessing import Queue, Process
else:
    from Queue import Queue
    from threading import Thread as Process


from Queue import Full, Empty
import numpy as np
##import nbmodule as nb   #wrapped VLF_DAQ (old)

from csig_proc import csig_proc
import MatFileWriter as matf

__all__ = ['Narrowband']
from NarrowbandC import NarrowbandC, dummyLogger

#from main import __ver__
from __ver__ import __ver__

from utilities.restart_counter import Restart_counter


try:
    import wx
    from VLFPanel import VLFPanel

    class GUIPanel(VLFPanel):
        def __init__(self, parent):
            VLFPanel.__init__(self, parent, "Narrowband")
            self.widgets = {
                'adc_channel_number':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'0-999'),
                'DirectoryRoot':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'DirectoryRoot1':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'DirectoryRoot2':wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),
                'Duration':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'[Seconds]'),
                'do_low_res':(wx.Choice(self, wx.ID_ANY, size= self.DROP_BOOL_SIZE,choices = ['0','1']),''),
                'do_sph_chan':(wx.Choice(self, wx.ID_ANY, size= self.DROP_BOOL_SIZE,choices = ['0','1']),''),
                'call_sign_file':(wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),'conf file (./nb.conf)'),
                'call_sign':(wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),"List of call signs (use ',')"),
                'filter_taps':(wx.TextCtrl(self, wx.ID_ANY, size= self.DIR_SIZE),'filter tap file (./filter_taps.txt)'),
##                'filter_length':(wx.TextCtrl(self, wx.ID_ANY, size= self.FLOAT_SIZE),'number of filter taps to use (1000)'),
            }
            self.addWidgets()
except:
    print "WARNING (Narrowband): CAN'T IMPORT WX AND/OR VLFPanel"



class Narrowband(NarrowbandC):
    """
	Demodulates NB channels to track the amplitude and phase
	"""

    # ========================
    # Constructors/Destructors
    # ========================
    def __init__(self, config, logger):
        """
		Constructs the Narrowband object according to the supplied XML
		description.
		"""
        NarrowbandC.__init__(self,config,logger)
        self.name = 'Narrowband'

    def startNBProcess(self,nb_input,config):
        asyncSave = Process(target=_AsyncSaveP,args = (self.queue, nb_input, config, self.logger))
        asyncSave.daemon = True
        asyncSave.start()
        #print 'Narrowband process started on pid: %d' % (asyncSave.pid)
        self.logger.info('Narrowband process started on pid: %d' % (asyncSave.pid))



class Filt:
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

    def copy(self):
        h = Filt(self.n,self.fs,self.h.copy(),self.filt_type,self.window_type)
        return h

    def __len__(self):
        return self.n

    def set_h(self,h):
        self.h = h
        self.n = len(h)

    def clear_H(self):
        self._f = None
        self._H = None
        self._center = None
        self.angle_H = None


    def lowpass(self,f0,win = 'hanning'):
        self.filt_type = 'lowpass'
        self.window_type = str(win)[:10]
##        print 'designing lowpass filter'
        self.h = firwin(self.n,(float(f0)/float(self.fs/2.0)),window = win)
        self.clear_H()

    def highpass(self,f0):
        self.filt_type = 'highpass'

        f0 = f0/(self.fs/2)

        NFFT = int(2.0**nextpow2(self.n))
        f_n = np.linspace(0,NFFT/2,NFFT/2+1)/(NFFT/2)
        H = np.zeros(int(NFFT/2.0+1))

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


    def bandpass(self,f1,f2):
        assert isinstance(f1,(int,float))
        assert isinstance(f2,(int,float))
        assert f2 > f1

        f0 = np.array([(f2+f1)/2.0])
        df = np.array([(f2-f1)],dtype = np.float)
        self.multipass(f0,df)

    def multipass(self,f0,df,a=None):
        """
        the highest amplitude is set to 1,
        all other amplitudes will scale accordingly
        f0: center frequencies
        df: frequency spread around each center
        """

        self.filt_type = 'bandpass'
        f0 = f0/(self.fs/2.0)
        df = df/(self.fs/2.0)

        NFFT = int(2.0**nextpow2(self.n))
        f_n = np.linspace(0,NFFT/2.0,NFFT/2.0+1.0)/(NFFT/2.0)
        H = np.zeros(int(NFFT/2+1))

        for ii in range(len(f0)):
            f_lo = f0[ii]-df[ii]/2.0
            f_hi = f0[ii]+df[ii]/2.0
    ##        H.put(where((f_n>=f_lo) & (f_n<=f_hi)),1)
            H[(f_n>=f_lo) & (f_n<=f_hi)] = 1.0

        #plot(f_n*fs/2,H)
        #show()

        fctr =np.exp(-1.0j*2.0*np.pi*np.linspace(0,NFFT/2.0,NFFT/2.0+1.0)/NFFT*(self.n-1.0)/2.0)
        H = H*fctr
        H = np.hstack((H,np.fliplr([np.conj(H[1:-1])])[0]))#convert to matrix for fliplr
        h = np.real(fft.ifft(H))
        h = h[:self.n]*np.hamming(self.n) #python stops at n-1
        self.window_type = 'hamming'

        #normalize to 1:
        H = fft.fft(h,NFFT)
##        H = H/extensions.myMax(np.abs(H))

        element = np.max(np.abs(H))
        index = np.argmax(np.abs(H))

        H = H/element

        h = np.real(fft.ifft(H))
        hr = h[:self.n].copy()#insures contiguous array
        self.h = hr
        self.clear_H()

    def getFreqResponse(self):
        assert self.h is not None

        if self._H is None:
            NFFT = int(2**(nextpow2(len(self.h))+1))
##            print 'NFFT = %d' % NFFT
            self._f = np.arange(NFFT/2,dtype=np.float)/float(NFFT)*self.fs

            self._H = fft.fft(self.h,NFFT)[:NFFT/2]

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

        ax.plot(self._f,20*np.log10(np.abs(self._H)))
        ax.grid(True)
        ax.set_xlabel('Frequency [Hz]')
        ax.set_title('Filter Response: Magnitude.  Window: %s (%d)' % (str(self.window_type),self.n))
        ax.set_ylabel('dB')

    def plotPhase(self,ax):

        self.getFreqResponse()

        ax.plot(self._f,modAngle(self.angle_H,2*np.pi,0))
        ax.grid(True)
        ax.set_xlabel('Frequency [Hz]')
        ax.set_ylabel('Phase [rad]')

    def plotUnwrappedPhase(self,ax):

        self.getFreqResponse()

        ax.plot(self._f,np.unwrap(self.angle_H)*180/np.pi)
        ax.grid(True)
        ax.set_xlabel('Frequency [Hz]')
        ax.set_ylabel('Unwrapped Phase [deg]')

    def plotDelay(self,ax):

        self.getFreqResponse()

        delay =-self.fs/(2*np.pi*(self._f[1]-self._f[0]))*np.diff(np.unwrap(self.angle_H))    #[samples]
        ##        delay -= center
        ax.plot(self._f[1:],delay/self.fs*1e6)
        ax.grid(True)
        # axis([xlim,M/2 - 2,M/2+2])
        ax.set_xlabel('Frequency [Hz]')
        ax.set_ylabel('delay [$\mu$sec]')




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

        assert self.h is not None
        assert len(self.h)%2==1, 'length of h must be odd'  #assert odd

        N_x = len(x)
        N_b = len(self.h)

##        print 'Nx: %d; Nb: %d' % (N_x,N_b)



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
                if len(cost)==0:    #use single block:
                    N_fft = 2**nextpow2(N_b+N_x-1)
                else:
                    N_fft = N[np.argmin(cost)]

            else:

                # When the filter length is at least as long as the signal,
                # filter the signal using a single block:
                N_fft = 2**nextpow2(N_b+N_x-1)

        N_fft = int(N_fft)
##        print N_fft


        # Compute the block length:
        L = int(N_fft - N_b + 1)
        offset = (N_b-1)/2  #compensate for filter delay

        y = np.zeros(N_x,dtype=x[0].dtype)

        # Compute the transform of the filter:
        if not isinstance(x[0],np.complex): #use rfft
            real_fft = True
            assert x[0].dtype == np.float64, 'Need to implement 32 bit'
            H = fft.rfft(self.h,N_fft)
        else:
            real_fft = False
            H = fft.fft(self.h,N_fft)

        i = 0
        while i <= N_x:
            il = min([i+L,N_x])

            if real_fft:
                yt = fft.irfft(csig_proc.mult_rfft(fft.rfft(x[i:il],N_fft),H)) # Overlap..
            else:
                yt = fft.ifft(fft.fft(x[i:il],N_fft)*H) # Overlap..

            i_lo = i - offset
            it_lo = 0
            if i_lo < 0:
                it_lo = -i_lo
                i_lo = 0

            k = min([i+N_fft,N_x + offset])

            y[i_lo:k-offset] += yt[it_lo:k-i]        # and add
            i += L


        return y

    def filt_and_downsample(self,x,Q=1):
        """
        Filter and then downsample (so only need to evaluate filter every Q samples
        """
        if not x.flags['C_CONTIGUOUS']:
            x = np.ascontiguousarray(x)

        assert len(x) % Q == 0, 'ERROR: length of x must be multiple of Q'

        if not isinstance(x[0],np.complex): #use real
            return csig_proc.filter_and_downsample_r(x,self.h,Q)
        else:
            return csig_proc.filter_and_downsample_r(x.real,self.h,Q) + 1.0j*csig_proc.filter_and_downsample_r(x.imag,self.h,Q) #faster!

    def upsample(self,x,Q):

        y = np.zeros(len(x)*Q,dtype=x.dtype)
        y[::Q] = x
        return Q*self.fftfilt(y)

    def upsample_then_interp(self,x,Q1,Q2):
        """
        First upsample by factor Q1, then linearly interpolate by factor Q2
        """
        x = self.upsample(x,Q1)
        return csig_proc.upsample_lin_interp(x,Q2)




class NBChannel:
    """
    Usage:

    #Set up object (always)
    nb = NBChannel(f0,keep_buffer = True)

    #Add data (always)
    nb.add_data(data,0)

    #Lock onto phi0, phi1, demodulate MSK (MSK tracking, nb removal)
    nb.demod_and_sync(Q=Q,bb_filt = bb_filt)
    nb.demodulate_msk()

    #Re-do phi0, phi1 sync, demodulate again, read out data (MSK tracking)
    nb.refine_sync()
    nb.demodulate_msk()

    Amp, pha0, pha1 = nb.amp_av, nb.phi0_av, nb.phi1_av
    Pha0_hi, Amp_hi = nb.get_tx_phase(), nb.get_tx_mag()

    #To get sferic channel  (sferic channel):
    nb.process_sferic_channel(n,df)
    Amp_hi = nb.get_sf_mag()

    """

    def __init__(self,f0,T = 1/200.0,Q=None,is_msk = True,keep_buffer = True):
        """

        """


        self.f0_decimal_places= 2 #only accept up to 2 decimal places in f0
        self.f0 = float(f0)
        self.T = T
        self.Q = Q  #downsample factor
        self.Q1= None
        self.Q2 = None
        self.h = None   # downsampling AAF
        self.h_bp= None   #nb filt (used in sph channel, defined in bp_filt)
        self.i_lo = None
        self.i_hi = None
        self.aI_dig = None
        self.aQ_dig = None
        self.aI_anal = None
        self.aQ_anal = None
        self.phi0_av = None
        self.phi1_av = None
        self.amp_av = None
        self.phap = None
        self.pham = None
        self.z = None
        self.keep_buffer = keep_buffer  #if True, keep a running buffer of z to avoid edge effects (only use with narrowband amp/phase tracking)
        self.data_buff = None
        self.buff_len = None
        self.data_len = 0
        self.is_msk= is_msk

        self.fs_nb_hi = 50.0    #hi-res narrowband sampling frequency
        self.hi_res_filter = None
        self.ch= None


        #keep a record of global adjustment to tx frequency, phase (use in self.z)
        self.df= 0.0
        self.dphi= 0.0


    def __len__(self):
        return len(self.data)

    def __mul__(self,other):

        assert self.fs == other.fs
        assert len(self) == len(other)
        z = self.copy()
        z.data *= other.data
        return z

    def copy(self):
        out = NBChannel(self.f0,self.T,self.Q,self.is_msk,keep_buffer = False)
        out.i_hi = self.i_hi
        out.i_lo = self.i_lo
        out.phi0_av = self.phi0_av
        out.phi1_av = self.phi1_av
        out.add_data(self,self.fs)
        out.h = self.h
        return out

    def div(self,other):

        assert self.fs == other.fs
        assert len(self) == len(other)
        z = self.copy()
        z.data /= other.data
        return z

    def make_t(self):
        self.t = np.arange(len(self),dtype=np.float)/self.fs
        self.exp_fctr_p = None
##        print 'making new t of length %d' % len(self)

    def flush_buffer(self):
        self.data_buff= None

    def add_data(self,data,fs,truncate=None):
        """
        Pass in bbdata or NBChannel object
        if truncate is not None: pare data to line across multiple of truncate (=Q)
        """

##        print 'f0: %3.2f kHz; adding data of length %d' % (self.f0/1e3,len(data))

        self.fs = fs

        if self.keep_buffer:
            self.buff_len = int(self.T*4.0*self.fs)
            if self.data_buff is None:
                self.data_buff = np.ones(self.buff_len,dtype = np.complex)*1e-6 #get an error if 0 (divide by amplitude in digital pll)

##        print 'buffer length: %d; fs = %3.2f' % (self.buff_len, fs)

        if isinstance(data,NBChannel):
            self.data = data.data.copy()

        else:   #assume numpy vector
            assert isinstance(data,np.ndarray)
            self.data = data.astype(np.complex)

        if truncate is not None:
            L = len(self.data)
            self.data = self.data[:L-(L%truncate)]

        if self.keep_buffer:
            self.data = np.hstack((self.data_buff,self.data))
            self.data_buff = self.data[-self.buff_len:].copy()

        data_len = len(self.data)
        if data_len != self.data_len:
##            print 'Data length changed: %d to %d' % (self.data_len,data_len)
            self.make_t()
            if self.keep_buffer:
                self.t -= self.buff_len/float(self.fs)

        self.data_len = data_len

    def calc_exp_fctr(self):

        if self.exp_fctr_p is None:
##            print 'generating expp of length %d' % len(self)
            self.exp_fctr_p = np.exp(-2.0j*np.pi*self.t*self.f0)




    def bp_filt(self,df = 200,f0 = None,n = 401):
        """
        Filter +/- df around f0 (default); may specify different f0
        """
        if self.h_bp is None:
            self.h_bp = Filt(n,self.fs)
            if f0 is None:
                f0 = self.f0

            self.h_bp.bandpass(f0-df,f0+df)
        self.filter(self.h_bp)


    def process_sferic_channel(self,n=501,df = 5000):
        self.z = self.copy()
        self.z.bp_filt(df,self.f0,n)
        self.z.downsample()
        self.z.data = np.power(self.z.data,2.0)


    def shift_down_to_DC(self):
        if self.exp_fctr_p is None:
            self.calc_exp_fctr()

        data = self.copy()
##        print self.T
##        print data.data.shape
##        print self.exp_fctr_p.shape
        data.data *= 2.0*self.exp_fctr_p
        data.filt_and_downsample(self.h)


        return data

    def shift_up_to_DC(self):
        if self.exp_fctr_p is None:
            self.calc_exp_fctr()

        data = self.copy()
        data.data *= 2.0*np.power(self.exp_fctr_p,-1.0)
        data.filt_and_downsample(self.h)

        return data

    def filt_and_downsample(self,h):

        self.data = h.filt_and_downsample(self.data,self.Q)
        self.t = self.t[::self.Q]
        self.fs = self.fs/float(self.Q)
        self.exp_fctr_p = None

    def downsample(self):
        self.t = self.t[::self.Q]
        self.data = self.data[::self.Q]
        self.fs = self.fs/float(self.Q)
        self.exp_fctr_p = None

    def square_data(self):
        self.data = np.power(self.data,2.0)

    def remove_DC(self):
        self.data -= np.mean(self.data)

    def filter(self,h):
        self.data = h.fftfilt(self.data)

    def make_AAF(self,filt):
        if self.h is None:
            assert isinstance(filt,Filt)
            self.h = filt
            n = len(self.h)

            #lowest/highest index where downsampled data is reliable
            self.i_lo = int((n-1)/2.0/float(self.Q))
            self.i_hi = int(len(self)/float(self.Q) - self.i_lo)


    def adjust_integration_bounds(self):
##        print 'i_lo, i_hi, samples/period: %d, %d, %d' % (self.i_lo, self.i_hi,2*self.T*self.fs)
        num_samples = int(2*self.T*self.fs)
        while ((self.i_hi- self.i_lo) % num_samples) > 0:
            self.i_hi -= 1
##        print 'i_lo, i_hi, samples/period: %d, %d, %d' % (self.i_lo, self.i_hi,2*self.T*self.fs)

    def get_carrier_clock_offsets(self):
        t_0 = -self.phi0_av/(2*np.pi*self.f0)
        t_1 = -self.phi1_av*2*self.T/np.pi
        return (t_0,t_1)

    def copy_phase_and_bits(self,other):
        """
        helper function to assign phase and bit sequence from self to self.z
        """
        other.phi0_av = self.phi0_av
        other.phi1_av = self.phi1_av
        other.aI_dig = self.aI_dig
        other.aQ_dig = self.aQ_dig

        other.aI_anal = self.aI_anal
        other.aQ_anal = self.aQ_anal


    def get_aI_aQ(self):
        """
        Get time-domain aI(t) and aQ(t) signals
        """

        (t_0,t_1) = self.get_carrier_clock_offsets()

        i_I = (self.t - np.mod(t_1 + 1*self.T,2*self.T))/(2*self.T) + 1

        a_I = self.aI_dig[i_I.astype(np.int)]

        i_Q = (self.t - np.mod(t_1 + 0*self.T,2*self.T))/(2*self.T) + 1
        a_Q = self.aQ_dig[i_Q.astype(np.int)]

        return a_I,a_Q

    def get_aI_aQ_analog(self):
        """
        Get time-domain analog aI(t) and aQ(t) signals
        """

        (t_0,t_1) = self.get_carrier_clock_offsets()

        i_I = (self.t - np.mod(t_1 + 1*self.T,2*self.T))/(2*self.T) + 1

        a_I = self.aI_anal[i_I.astype(np.int)]

        i_Q = (self.t - np.mod(t_1 + 0*self.T,2*self.T))/(2*self.T) + 1
        a_Q = self.aQ_anal[i_Q.astype(np.int)]


        return a_I,a_Q

    def refine_sync(self):
        """
        After demod bits, refine choice of phi0,1 by masking out pos, neg freq

        Note that at this point, self.z has been destructively modified by removing phi_0_ave (first estimate)

        """
        if not self.is_msk:
            return

        aI,aQ = self.z.get_aI_aQ_analog()
        pos_mask = np.abs(aI-aQ)/2.0
        neg_mask = 1.0-pos_mask

        self.dphi= 0
        self.z.dphi = 0

        self.digital_pll(1.0,pos_mask, neg_mask)


    def digital_pll(self,z_mod = 1.0, pos_mask = None, neg_mask = None):
        if not self.is_msk:
            #just a tone:
            ZT = np.sum(self.z.data[self.z.i_lo:self.z.i_hi])
            self.phi0_av= np.angle(ZT)
            self.phi1_av= 0.0   #just in case it's read
            self.pham= self.phi0_av
            self.phap= self.phi0_av
            self.copy_phase_and_bits(self.z)
            self.z.dphi = self.phi0_av
            return

        z2 = np.power(self.z.data*self.z.get_pha_adjustment()*z_mod,2.0)


        absz2 = np.abs(z2)+1e-15    #avoid any NAN's    #Note: divide by OVERALL (combining both +/-) amplitude, to de-emphasize sferics; gives frequency with lower amplitude equal playing field

        if pos_mask is None:
            pos_mask = np.ones(len(self.z.data))

        if neg_mask is None:
            neg_mask = np.ones(len(self.z.data))

        ejp = np.sum(z2[self.z.i_lo:self.z.i_hi]*self.z.exp_fctr_p[self.z.i_lo:self.z.i_hi]/absz2[self.z.i_lo:self.z.i_hi]*pos_mask[self.z.i_lo:self.z.i_hi])
        ejm = np.sum(z2[self.z.i_lo:self.z.i_hi]*np.power(self.z.exp_fctr_p[self.z.i_lo:self.z.i_hi],-1.0)/absz2[self.z.i_lo:self.z.i_hi]*neg_mask[self.z.i_lo:self.z.i_hi])
        phip = modAngle(np.angle(ejp),2*np.pi,np.pi)
        phim = modAngle(np.angle(ejm),2*np.pi,np.pi)


        #unwrap phip, phim:
        if self.phap is None:
            self.phap = phip
        while phip-self.phap > np.pi:   #jumped "up"
            phip -= 2*np.pi
        while self.phap - phip > np.pi: #jumped "down"
            phip += 2*np.pi
        self.phap = phip

        if self.pham is None:
            self.pham = phim
        while phim-self.pham > np.pi:   #jumped "up"
            phim -= 2*np.pi
        while self.pham - phim > np.pi: #jumped "down"
            phim += 2*np.pi
        self.pham = phim

        self.phi0_av = modAngle((self.phap + self.pham)/4.0,2*np.pi,0)  #carrier phase
        self.phi1_av = modAngle((self.phap - self.pham)/4.0,2*np.pi,0)  #clock phase

        self.copy_phase_and_bits(self.z)
        self.z.dphi = self.phi0_av


    def get_pha_adjustment(self):
        """
        Phase adjustment for macro df, dphi
        """
        return np.exp(-2.0j*np.pi*self.df*self.t - 1.0j*self.dphi)

    def demod_and_sync(self,Q=100,bb_filt = None):
        """
        Demodulate broadband data to self.z
        Find carrier and clock phase offsets
        self.phi0_av and self.phi1_av


        n: # of filter taps
        Q: subsample factor
        fc_buff: Hz beyond 1/4T for AAF, or filter file location

        """

        #for intermediate upsampling:
        FCTR = 10
        assert Q % FCTR == 0
        self.Q = Q

        if self.Q1 is None:
            self.Q1 = int(self.Q/FCTR)
            self.Q2 = FCTR
            self.h_med = Filt(401,self.fs/float(FCTR))
            self.h_med.lowpass(self.fs/float(2*self.Q))

        assert isinstance(bb_filt,Filt)

        self.make_AAF(bb_filt)
        self.z = self.shift_down_to_DC()

        self.z.f0 = 1.0/(2.0*self.T)    #twice the sideband frequency (for z^2)
        if self.z.exp_fctr_p is None:
            self.z.calc_exp_fctr()
        self.z.f0 = self.f0


        self.digital_pll()


        self.amp_av = np.mean(np.abs(self.z.data[self.z.i_lo:self.z.i_hi]))



    def demodulate_msk(self):
        """
        Demodulate bits from baseband self.z signal
        Generates digital aI_dig and aQ_dig bit sequences
        """

        if not self.is_msk:
            return

        amp_av = self.amp_av   #need to carry over? only used in int_x, int_y normalization

        #carrier and clock timing offsets
        (t_0,t_1) = self.get_carrier_clock_offsets()

        #in-phase and quadrature baseband modulators
        x = np.cos(2*np.pi*(self.z.t-t_1)/(4*self.T))
        y = np.sin(2*np.pi*(self.z.t-t_1)/(4*self.T))

        #adjust carrier frequency/phase, and normalize by amlitude:
        norm_z = self.z.data*self.z.get_pha_adjustment()/np.abs(self.z.data)

        dt = self.z.t[1] - self.z.t[0]
        int_x = np.cumsum(np.real(norm_z)*x)*dt/self.T
        int_y = np.cumsum(-np.imag(norm_z)*y)*dt/self.T

##        print "clock offset: %2.5f ms, carrier offset: %2.5f ms" % (t_1*1e3,t_0*1e3)

        period = 2.0*self.T
        x_lims = np.arange(np.mod(t_1 + period/2.0,period),self.z.t[-1],period)
        y_lims = np.arange(np.mod(t_1,period),self.z.t[-1],period)

        i_x_lims = x_lims*self.z.fs
        i_y_lims = y_lims*self.z.fs
        #new
        i_x_lims = np.hstack((0,i_x_lims.astype(np.int),len(self.z)-1,len(self.z)-1))
        i_y_lims = np.hstack((0,i_y_lims.astype(np.int),len(self.z)-1,len(self.z)-1))

##        print 'length of i_x_lims: %d; first start: %3.3f, period: %3.3f, last t: %3.3f ' % (len(i_x_lims),np.mod(t_1 + period/2.0,period), period, self.z.t[-1])

        aI = np.diff(int_x[i_x_lims])
        aQ = np.diff(int_y[i_y_lims])

##        print aQ[:5], int_y[i_y_lims[:5]], i_y_lims[:5]

        self.aI_dig = np.ones(len(aI))
        self.aI_dig[aI < 0] = -1.0

        self.aQ_dig = np.ones(len(aQ))
        self.aQ_dig[aQ < 0] = -1.0

        #try:
        self.aI_anal= aI
        self.aQ_anal= aQ

        self.copy_phase_and_bits(self.z)


    def get_trellis(self):


        (t_0,t_1) = self.get_carrier_clock_offsets()

        #subtract phase trellis from phase:
        aI,aQ = self.z.get_aI_aQ()

        bk = np.ones(len(self.z))
        bk[np.abs(aI-aQ)<.5] = -1.0
        phik = np.zeros(len(self.z))
        phik[aI<0] = np.pi

        trellis = bk*(np.pi*(self.z.t-0.0)/(2*self.T) + self.phi1_av) + phik
        return trellis


    def apply_hi_res_filter(self,x):
        """
        Generate and apply lowpass filter used for 'high-resolution' (usually 50 Hz) data
        Then downsample and return vector ready for return to caller
        """

        Q = int(self.z.fs/float(self.fs_nb_hi))

        if self.hi_res_filter is None:
##            print 'fs: %3.2f Hz; fs_nb: %3.2f Hz; Q = %d' % (self.z.fs,self.fs_nb_hi,Q)
            n = 2*Q
            if n % 2 == 0:
                n += 1;

            fc = .4*self.fs_nb_hi
##            print 'hi-res filter length: %d (%2.3f ms), fc = %2.3f Hz' % (n,(1000*n/float(self.z.fs)),fc)
            self.hi_res_filter = Filt(n,fs=self.z.fs)
            self.hi_res_filter.lowpass(fc)


        if self.keep_buffer:
            offset = int(self.buff_len/self.Q/2.0)  #=2*self.T*self.z.fs
            hi_index = -int(self.buff_len/self.Q/2.0)

        else:
            offset = 0
            hi_index = len(x)


        return self.hi_res_filter.fftfilt(x)[offset:hi_index:Q]



    def get_tx_phase_hi(self):
        """
        Recover transmitter phase by subtracting reconstructed phase trellis from
        self.z
        integrates every sample bit
        """
        if self.is_msk:
            trellis = self.get_trellis()
        else:
            trellis = 0.0

        phase_tx = self.z.data*self.z.get_pha_adjustment()/np.abs(self.z.data)*np.exp(-1.0j*trellis)  #divide by amplitude t reduce effect from sferics
        pha_hi = modAngle(np.angle(self.apply_hi_res_filter(phase_tx)),2*np.pi,0)

        pha_hi += self.z.dphi
        return  pha_hi

    def get_tx_mag(self):
        """
        Use more graceful method of lowpass filtering and then sampling
        """
        mag_z_hi = self.apply_hi_res_filter(np.abs(self.z.data))
        return mag_z_hi

    def get_sf_mag(self):
        """
        Return RMS of 5-15 kHz
        """
        return np.sqrt(np.abs(self.apply_hi_res_filter(np.abs(self.z.data)))) #outer absolute in case of aliasing causing neg values



def nextpow2(i):
    """ returns the power, not the number """
    N = 1   #number
    n = 0   #power
    while N < i:
        n = n + 1.0
        N = N * 2.0
    return n


def modAngle(x,period,theta0):
    return np.mod(x + period/2.0 - theta0,period) - period/2.0 + theta0

##class AsyncSave(Thread):
def _AsyncSaveP(queue,nb_input,config,logger):

    restart_counter = None
    if Restart_counter is not None:
        restart_counter = Restart_counter()

    wait_time = 10
    Q = 100
    fs_sph = 100


    #nb_input = [FilterTaps,FilterLength,TransFreq, sampleFrequency, calibrationFactor,
    #            is_msk, do_low_res, call_sign,do_sph_channel,baud_rate]

    #Create Filter:
    do_sph_channel = nb_input[8]
    do_low_res = nb_input[6] #[1 yes, 0 no]
    num_nb_channels = len(nb_input[2])

    filt_taps = nb_input[0]
##    filt_len = nb_input[1]
    sample_freq = nb_input[3]   #for NB channel; not used

    bb_filt = None


    R2D = 180.0/np.pi



    cal_fctr = nb_input[4]

    #logger = dummyLogger('NB')
    #logger = logger

    nb_channels = []

    ampMat = []
    phaseMat =[]
    ampMat_low = []
    phaseMat_low =[]
    clockMat = []




    for jj in xrange(num_nb_channels):
        tx_freq = nb_input[2][jj]
        is_msk = nb_input[5][jj]
        baud_rate = nb_input[9][jj]
        call_sign = nb_input[7][jj]

        nb_channels.append(NBChannel(tx_freq,T = 1.0/baud_rate, is_msk = is_msk,keep_buffer = True))

        if not is_msk:
            baud_rate = 0.0

        amp_config = (1,is_msk, 'C', filt_taps, tx_freq,call_sign,baud_rate)
        ampMat.append(matf.MatFileWriter(config, logger, amp_config))

        phase_config = (0,is_msk,'D',filt_taps, tx_freq,call_sign,baud_rate)
        phaseMat.append(matf.MatFileWriter(config, logger, phase_config))


        if do_low_res == 1:

            amp_low_config = (1,is_msk, 'A',filt_taps,tx_freq,call_sign,baud_rate)
            ampMat_low.append(matf.MatFileWriter(config, logger, amp_low_config))

            phase_low_config = (0,is_msk,'B',filt_taps, tx_freq,call_sign,baud_rate)
            phaseMat_low.append(matf.MatFileWriter(config, logger, phase_low_config))

            if is_msk:
                clock_phase_config = (0,is_msk,'F',filt_taps, tx_freq,call_sign,baud_rate)
                clockMat.append(matf.MatFileWriter(config, logger, clock_phase_config))
            else:
                clockMat.append(None)   #to keep length correct


    if do_low_res:
        assert len(ampMat) == len(clockMat)
        assert len(ampMat) == len(phaseMat_low)

    if do_sph_channel:
        call_sign_sph, f0_sph, n_sph ,Q_sph, df_sph = 'SPH', 10e3, 401,2, 5000

        sph_channel = NBChannel(f0_sph,Q=Q_sph,keep_buffer = True)
        sph_channel.fs_nb_hi = fs_sph
        sph_config = (1,0,'C',np.array([0.0]),0,call_sign_sph,0.0)
        sphMat = matf.MatFileWriter(config,logger,sph_config)


    last_queue_size = 0
    prev_time = None

    block_num = -1

    elapsed_time = 0

    while True:

        try:
            data = queue.get(timeout=wait_time)     # Pull this second's timestamp from the GPS clock
            block_num += 1
            #print 'Got queue element %d' % block_num
        except Empty:
            if restart_counter is None:
                logger.warning('Waiting for %d seconds, quitting Narrowband AsyncSave process ' % wait_time)
                break

            elif restart_counter.check():
                continue

            else:
                logger.warning('Restart counter did not check out (should be: %s; new value: %s), quitting Narrowband AsyncSave process'\
                               %(restart_counter.current_value(),restart_counter.peek()))
                break

        except Exception, exc:
            logger.exception('Unexpected error when reading from Narrowband Queue.')

        #Verify datastream is contiguous
        if prev_time is not None:
            td = data[1][0] - prev_time
            td = td.days*86400+td.seconds + td.microseconds*1e-6
            if int(round(td)) is not 1:
                logger.warning('Resetting filter, timedelta = %f' % td)
                for jj in range(num_nb_channels):
                    nb_channels[jj].flush_buffer()

        prev_time = data[1][0]


        fs = float(data[2])

        if bb_filt is None: #define now that we have fs
            bb_filt = Filt(len(filt_taps),fs,h=filt_taps,filt_type='custom')

        tsave = 0

        ttt = clock()
##        try:

        for jj in xrange(num_nb_channels):
##            print 'jj: %d' % jj
            nb_channels[jj].add_data(data[0]*cal_fctr,fs = fs)
            nb_channels[jj].demod_and_sync(Q=Q,bb_filt = bb_filt)
            nb_channels[jj].demodulate_msk()
            nb_channels[jj].refine_sync()

            amp = nb_channels[jj].get_tx_mag()
            phase = nb_channels[jj].get_tx_phase_hi()*R2D   #[deg]

            #print "Grabbing for timestamp %s." % data[1][0]
            samplingRate = amp.size
##            print data[1],nb_input[7][jj]
            ampMat[jj].Process([amp.astype(np.float32), data[1] ,samplingRate],dtype='float32')

            phaseMat[jj].Process([phase.astype(np.float32), data[1] ,samplingRate],dtype='float32')


            if do_low_res == 1:
                amp_low = np.atleast_1d(nb_channels[jj].amp_av)
                phase_low =  np.atleast_1d(nb_channels[jj].phi0_av)*R2D
                samplingRate = amp_low.size
                ampMat_low[jj].Process([amp_low.astype(np.float32), data[1] ,samplingRate],dtype='float32')
                ttemp = clock()
                phaseMat_low[jj].Process([phase_low.astype(np.float32), data[1] ,samplingRate],dtype='float32')
                tsave += (clock()-ttemp)

##                print nb_channels[jj].is_msk
                if nb_channels[jj].is_msk:
##                    print 'saving clock phase'
                    phase_clock =  np.atleast_1d(nb_channels[jj].phi1_av)*R2D
                    clockMat[jj].Process([phase_clock.astype(np.float32), data[1] ,samplingRate],dtype='float32')


        if do_sph_channel:
            sph_channel.add_data(data[0]*cal_fctr, fs = fs)
            sph_channel.process_sferic_channel(n_sph,df_sph)
            sph = sph_channel.get_sf_mag()
            sphMat.Process([sph.astype(np.float32),data[1],sph.size],dtype='float32')

##        except:
##            logger.warning('Unable to process/save result, quitting this nbP process')
##            break

        data[0] = np.array([])
        elapsed_time_temp = clock()-ttt
##        print 'Time to process %d channels + SPH: %3.1f ms' % (num_nb_channels,elapsed_time_temp*1e3)
##        print 'Time saving just hi-resolution PHase: %3.1f ms' % (tsave*1e3)
        if elapsed_time_temp > elapsed_time+.5:
            elapsed_time = elapsed_time_temp
            if elapsed_time > 1.0:
                logger.warning('Time for last second of nbP processing: %3.2f (qsize=%d)' % (elapsed_time,queue.qsize()))
        if elapsed_time_temp < elapsed_time-2.0:  #shaved off two seconds; reset
            elapsed_time = elapsed_time_temp
##        print 'Time per nb channel: %2.4f (%d channels)' % ((clock()-ttt)/num_nb_channels,num_nb_channels)

    #print "RealMixed[0] = %f" % amp[0]

    for jj in range(num_nb_channels):
        tmp =  nb_channels.pop()
        del tmp


# =========
# Unit Test
#=========
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    from xml.dom.minidom import parseString
    import numpy
    from datetime import datetime, timedelta
    import time as timemod
    import os
    import logging
    import scipy.io as sio


    # Create log
    logging.basicConfig()
    logger = logging.getLogger("Unit Test")
    logger.setLevel(logging.DEBUG)




    # Create the Motorola GPS clock object
    settings = """
    <PostProcessor module="Narrowband">
        <DirectoryRoot>../../../Temp/Data</DirectoryRoot>
        <DirectoryRoot1>../../../Temp/Data2</DirectoryRoot1>
        <station_id>PH</station_id>
        <station_name>Philmont</station_name>
        <adc_card>0</adc_card>
        <adc_channel_number>002</adc_channel_number>
		<Duration>5</Duration>
        <call_sign_file>../../resources/nb.conf</call_sign_file>
        <call_sign>NAA,NPM,NML,NLK,TONE,JJI,NWC,HWU</call_sign>
		<do_low_res>1</do_low_res>
        <do_sph_chan>1</do_sph_chan>
        <filter_taps>../../resources/filter_taps.txt</filter_taps>
        <filter_length>0</filter_length>
    </PostProcessor>
    """

    config = parseString(settings)
    #config.getElementsByTagName("Fc").setAttribute("Fc", 200)
    #config.getElementsByTagName("Fc")[0].firstChild.nodeValue = 1
    #print config.toxml()

    nbproc = Narrowband(parseString(settings),logger)

    # Read matlab file
##    mat_data = sio.loadmat(r"Z:\awesome\broadband\palmer\2009\09_23\PA090923000000_000.mat")#("./Data/DAQ_Data/TestNAA.mat")#("./LatestNS.mat")#
    mat_data = sio.loadmat(r"U:\awesome\broadband\taylor\2008\07_21\TA080721000500_002.mat")
    ##print mat_data['adc_type'].data
    ##print "%d" %mat_data['Fs']
    ##print mat_data['data'].transpose()

    L = 1   #[seconds]
    fs = float(mat_data['Fs'][0])
    #print fs
    t = np.arange(int(L*fs),dtype=np.float)/fs

    time = datetime(year=mat_data['start_year'], month=mat_data['start_month'], day=mat_data['start_day'], hour=mat_data['start_hour'], minute=mat_data['start_minute'], second=mat_data['start_second'])


    for i in xrange(10):

##        rawBuffer = np.array(mat_data['data'].take(np.arange(t.size)+i*t.size), dtype='float64')
        rawBuffer = mat_data['data'][i*t.size:(i+1)*t.size].transpose()[0]

        #add a tone to test
##        print rawBuffer.shape
        rawBuffer = rawBuffer.astype(np.float)
##        print 'before:', rawBuffer[:10]
        tone = 1000.0*np.cos(2.0*np.pi*10e3*t + .45)
##        print tone.shape
        rawBuffer += tone
##        print 'after:', rawBuffer[:10]

        #print rawBuffer
        data = [rawBuffer, [time, [0, 0, 0], [8]],fs]

        if(i >= 0):
            print "Processing for timestamp %s." % data[1][0]
            nbproc.Process(data)
            timemod.sleep(.1)
        time += timedelta(seconds=1)
        t += L

    timemod.sleep(10)
##    spec.queue.join()
