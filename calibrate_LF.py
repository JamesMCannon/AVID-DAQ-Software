# LF receiver calibration script
# Austin Sousa, 5/25/2018
from __future__ import division # stop casting to int every time we divide, jesus christ Python
import Tkinter
import tkFileDialog
import matplotlib
matplotlib.use("TkAgg")
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from scipy.io import loadmat, savemat
from scipy.ndimage.filters import gaussian_filter1d
import datetime

from scipy.interpolate import interp1d
import os
import sys

# --------------------------- Helper functions --------------------------------------
def wire_diameter_from_AWG(awg):
    awgvec = np.array([0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40])
    diameters = [8.35E-03,6.54E-03,5.32E+00,4.11E-03,3.26E-03,2.59E-03,2.05E-03,1.63E-03,1.29E-03,1.02E-03,8.12E-04, 
                6.44E-04,5.11E-04,4.05E-04,3.21E-04,2.55E-04,2.02E-04,1.60E-04,1.27E-04,1.01E-04,7.99E-05]
    
    ind = np.argmin(np.abs(awg - awgvec))
    if np.abs(awgvec[ind] - awg) < 0.1:
        return diameters[ind]
    else:
        print "Invalid wire gauge"
        return None
    

def square_antenna_params(awg, side_length, N_turns):
    '''side length: length of square side, in centimeters '''
    # Constants:
    Kb = 1.38e-23
    T  = 273 # Kelvin
    Resistivity = 1.72e-8  # Annealed copper ~ [ohm-meter]
    s2w_ratio = 2.2 # Shield to wire ratio

    cm2m = 1./100.
    c1 = 4.0   # Paschal table 3.1 (square loop)
    c2 = 1.217 # Paschal table 3.1 (square loop)

    area = (cm2m*side_length)**2 # m^2
    wire_length = (cm2m*side_length)*4.*N_turns
    wire_diameter = wire_diameter_from_AWG(awg)
    
    Resistance = Resistivity*wire_length/(np.pi*(wire_diameter/2.)**2)
#     print Resistance
    
    # Inductance, in Henries
    # evans ~ from ev paschal's document
    # Inductance  = (2.0e-7)*(N_turns**2)*c1*np.sqrt(area)*(np.log(c1*np.sqrt(area)/(np.sqrt(N_turns)*wire_diameter)) - c2)

#     Morris, from Morris' spreadsheet -- includes the ratio of wire to shielding.
    Inductance = (2.0e-7)*(N_turns**2)*c1*np.sqrt(area)*(np.log(c1*np.sqrt(area/N_turns)/(wire_diameter*s2w_ratio)) - c2)
    
    
    # Magnetic field sensitivity - A-sqrt(Hz)/meter
    # (Normalized per frequency -- typically we plot in units of /sqrt(hz)/m)
    Sb = np.sqrt(Kb*T*Resistance)/(np.pi*N_turns*area)
    
    # Electric field sensitivity - V - root(Hz)/meter
    Se = Sb*3.0e8  # not in a plasma; E and B are related by speed of light

    # Cutoff frequency ~ Hz
    Fc = Resistance/Inductance/np.pi
#     print Fc
    return Resistance, Inductance, Sb, Se, Fc, area


def isosceles_right_triangle_antenna_params(awg, baseline, N_turns):
    '''Baseline: Length of the antenna along the ground, in centimeters
       (in this case, the hypotenuse of an isosceles right triangle)
       '''

    # Constants:
    Kb = 1.38e-23
    T  = 273 # Kelvin
    Resistivity = 1.72e-8  # Annealed copper ~ [ohm-meter]
    s2w_ratio = 2.2 # Shield to wire ratio
    
    cm2m = 1./100.
    c1 = 4.828   # Paschal table 3.1 (square loop)
    c2 = 1.696 # Paschal table 3.1 (square loop)

    area = (cm2m*baseline/2.)**2 # m^2
#     print area
    wire_length = (cm2m*baseline)*(1. + np.sqrt(2))*N_turns
    wire_diameter = wire_diameter_from_AWG(awg)
#     print wire_length
    Resistance = Resistivity*wire_length/(np.pi*(wire_diameter/2.)**2)
#     print Resistance
    
    # Inductance, in Henries
    # evans ~ from ev paschal's document
#     Inductance  = (2.0e-7)*(N_turns**2)*c1*np.sqrt(area)*(np.log(c1*np.sqrt(area)/(np.sqrt(N_turns)*wire_diameter)) - c2)

#     Morris, from Morris' spreadsheet -- includes the ratio of wire to shielding.
    Inductance = (2.0e-7)*(N_turns**2)*c1*np.sqrt(area)*(np.log(c1*np.sqrt(area/N_turns)/(wire_diameter*s2w_ratio)) - c2)

    # Magnetic field sensitivity - A-sqrt(Hz)/meter
    # (Normalized per frequency -- typically we plot in units of /sqrt(hz)/m)
    Sb = np.sqrt(Kb*T*Resistance)/(np.pi*N_turns*area)
    
    # Electric field sensitivity - V - root(Hz)/meter
    Se = Sb*3.0e8  # not in a plasma; E and B are related by speed of light
    
    # Cutoff frequency ~ Hz
    Fc = Resistance/Inductance/np.pi
    return Resistance, Inductance, Sb, Se, Fc, area

# ----------------- Plotting Scripts --------------------------
def plot_frequency_response(FR_NS, FR_EW):
    # --------------- Latex Plot Beautification --------------------------
    fig_width = 6 
    fig_height = 4
    fig_size =  [fig_width+1,fig_height+1]
    params = {'backend': 'ps',
              'axes.labelsize': 12,
              'font.size': 12,
              'legend.fontsize': 10,
              'xtick.labelsize': 10,
              'ytick.labelsize': 10,
              'text.usetex': False,
              'figure.figsize': fig_size}
    plt.rcParams.update(params)
    # --------------- Latex Plot Beautification --------------------------
    fig, ax = plt.subplots(2,1, sharex=True, sharey=True)
    ax[0].plot(FR_NS[:,0], FR_NS[:,1])
    ax[0].set_title('NS Channel Frequency Response')
    ax[0].set_ylabel('Response\n(mV$_{out}$/pT$_{in}$)')
    ax[0].grid('on', which='both', alpha=0.5)
    
    ax[1].plot(FR_EW[:,0], FR_EW[:,1])
    ax[1].set_title('EW Channel Frequency Response')
    ax[1].set_ylabel('Response\n(mV$_{out}$/pT$_{in}$)')
    ax[1].set_xlabel('Frequency (kHz)')
    ax[1].grid('on', which='both', alpha=0.5)


    # ax[1].set_xlim([0, 500])
    
    fig.tight_layout()
    fig.show()
    # fig.savefig('CalibrationResponse.pdf')
    
    return fig, ax

def plot_calibration_number(CA_NS, CA_EW):
        # --------------- Latex Plot Beautification --------------------------
    fig_width = 6 
    fig_height = 4
    fig_size =  [fig_width+1,fig_height+1]
    params = {'backend': 'ps',
              'axes.labelsize': 12,
              'font.size': 12,
              'legend.fontsize': 10,
              'xtick.labelsize': 10,
              'ytick.labelsize': 10,
              'text.usetex': False,
              'figure.figsize': fig_size}
    plt.rcParams.update(params)
    # --------------- Latex Plot Beautification --------------------------
    fig, ax = plt.subplots(2,1, sharex=True, sharey=True)
    ax[0].plot(CA_NS[:,0], CA_NS[:,1])
    ax[0].set_title('NS Calibration Number')
    ax[0].set_ylabel('Calibration Number\n(pT/increment)')
    ax[0].grid('on', which='both', alpha=0.5)
    axb = ax[0].twinx()
    axb.plot(CA_NS[:,0], CA_NS[:,1]*pow(2,16)*1e-6)
    axb.set_ylabel('Saturation level\n($\mu$T)')
    ylims = np.array(ax[0].get_ylim())
    axb.set_ylim(ylims*pow(2,16)*1e-6)
    ax[1].plot(CA_EW[:,0], CA_EW[:,1])
    ax[1].set_title('EW Calibration Number')
    ax[1].set_ylabel('Calibration Number\n(pT/increment)')
    ax[1].set_xlabel('Frequency (kHz)')
    ax[1].grid('on', which='both', alpha=0.5)
    axc = ax[1].twinx()
    axc.plot(CA_EW[:,0], CA_EW[:,1]*pow(2,16)*1e-6)
    axc.set_ylabel('Saturation level\n($\mu$T)')
    # ax[1].set_xlim([0, 500])
    ylims = np.array(ax[1].get_ylim())
    axc.set_ylim(ylims*pow(2,16)*1e-6)
    fig.tight_layout()
    fig.show()
    # fig.savefig('CalibrationNumber.pdf')
    
    return fig, ax


def plot_response_ratio(freq_axis, response_ratio):
    # --------------- Latex Plot Beautification --------------------------
    fig_width = 6 
    fig_height = 2.5
    fig_size =  [fig_width+1,fig_height+1]
    params = {'backend': 'ps',
              'axes.labelsize': 12,
              'font.size': 12,
              'legend.fontsize': 10,
              'xtick.labelsize': 10,
              'ytick.labelsize': 10,
              'text.usetex': False,
              'figure.figsize': fig_size}
    plt.rcParams.update(params)
    # --------------- Latex Plot Beautification --------------------------
    
    fig, ax = plt.subplots(1,1)
    LogRatio = 20*np.log10(np.abs(response_ratio))
    ax.plot(freq_axis, LogRatio)
    ax.set_ylim([-6,6])
    ax.set_ylabel('NS/EW Ratio (dB)')
    ax.set_xlabel('Frequency (kHz)')
    ax.grid('on', which='both', alpha=0.5)
    ax.set_title('Channel Calibration Response Ratio')
    # ax.set_xlim([0,500])
    fig.tight_layout()
    fig.show()
    # fig.savefig('ResponseRatio.pdf')
    return fig, ax



def plot_noise_floor(noise_NS, noise_EW):
    # Atmospheric noise information, taken from figure 2 of "What and Where
    # is the Natural Noise Floor", by John Meloy
    # (Derived from Stanford AWESOME data, online at http://www.vlf.it/naturalnoisefloor/naturalnoisefloor.htm)
    # In units of dB-pT/rt(Hz), against kHz frequency
    atmo_freqs = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1,2,3,4,5,6,7,8,9,10, 15, 20, 30, 40, 50]
    atmo_vals =  [-15, -18, -22, -25, -27, -29, -28, -27, -30, -31, -35, -40, -42, -40, -37, -35, -32, -30, -28, -28, -31, -34, -38, -42]
    
    # --------------- Latex Plot Beautification --------------------------
    fig_width = 6 
    fig_height = 4
    fig_size =  [fig_width+1,fig_height+1]
    params = {'backend': 'ps',
              'axes.labelsize': 12,
              'font.size': 12,
              'legend.fontsize': 10,
              'xtick.labelsize': 10,
              'ytick.labelsize': 10,
              'text.usetex': False,
              'figure.figsize': fig_size}
    plt.rcParams.update(params)
    # --------------- Latex Plot Beautification --------------------------
    
    fig, ax = plt.subplots(2,1, sharex=True, sharey=True)
    ax[0].plot(noise_NS[:,0], 10*np.log10(noise_NS[:,1]), label='System noise')
    ax[0].set_title('NS Channel Noise Response')
    ax[0].set_ylabel('Noise Level\ndB-pT/$\sqrt{Hz}$')
    ax[0].grid('on', which='both', alpha=0.5)
    ax[0].plot(atmo_freqs, atmo_vals, label='Natural VLF noisefloor')
    ax[0].legend()

    ax[1].plot(noise_EW[:,0], 10*np.log10(noise_EW[:,1]),label='System noise')
    ax[1].set_title('EW Channel Noise Response')
    ax[1].set_ylabel('Noise Level\ndB-pT/$\sqrt{Hz}$')
    ax[1].set_xlabel('Frequency (kHz)')
    ax[1].grid('on', which='both', alpha=0.5)
    ax[1].plot(atmo_freqs, atmo_vals, label='Natural VLF noisefloor')
    ax[1].legend()
    ax[1].set_ylim([-80, -20])
    # ax[1].set_xlim([0, 500])
    fig.tight_layout()
    # fig.show()
    # fig.savefig('NoiseResponse.pdf')
    return fig, ax
# ----------- Main --------------
def calibrate_2ch(file1, file2):
    


    # ----------- Load data from matlab file dicts -----------
    Fs = file1['Fs']
    is_LF = (Fs > 100000)
    data1 = np.array(file1['data'])
    data2 = np.array(file2['data'])
    tvec = np.linspace(0, len(data1)-1,len(data1))/Fs

    caltone_length = 1.0 # seconds
    noise_length = 1.0 # seconds
    
    # ---------- Find caltone region ---------------
    # (you can comment this out and enter it manually if it's not working right)
    # caltone_start_sec = 5
    # noise_start_sec = 30

    # We're just downsampling by ~1000, smoothing it with a Gaussian filter, and finding the peak.
    if is_LF:
        print('LF data detected')
    else:
        print('VLF data detected')
    caltone_start_sec = raw_input('Caltone start time, in seconds [none to autodetect]:') or None

    if caltone_start_sec is None:
        if is_LF:
            ds_factor = 1000
        else:
            ds_factor = 100
        ds1 = data1[::ds_factor]
        ds2 = gaussian_filter1d(np.abs(ds1), sigma=ds_factor, axis=-1)
        max_ind = np.argmax(ds2)
        caltone_center_ind = max_ind*ds_factor
        caltone_start_sec = caltone_center_ind/Fs
    else:
        caltone_start_sec = int(caltone_start_sec)

    noise_start_sec = raw_input('Noise start time, in seconds [none to autodetect]:') or None

    if noise_start_sec is None:
        if max_ind < len(ds1)/2:
            noise_center_ind = int(len(ds1) + max_ind)/2*ds_factor
        else:
            noise_center_ind = (max_ind/2)*ds_factor
        noise_start_sec = noise_center_ind/Fs
    else:
        noise_start_sec = int(noise_start_sec)
    print "Caltone at %g sec"%caltone_start_sec
    print "Noise floor at %g sec"%noise_start_sec

    cal1 = data1[int(caltone_start_sec*Fs):int((caltone_start_sec*Fs) + caltone_length*Fs)]
    cal2 = data2[int(caltone_start_sec*Fs):int((caltone_start_sec*Fs) + caltone_length*Fs)]

    noise1 = data1[int(noise_start_sec*Fs):int((noise_start_sec*Fs) + noise_length*Fs)]
    noise2 = data2[int(noise_start_sec*Fs):int((noise_start_sec*Fs) + noise_length*Fs)]

    # print len(cal1), len(cal2)
    # print len(noise1), len(noise2)

    # Remove DC offsets:
    cal1 = cal1 - np.mean(cal1)
    cal2 = cal2 - np.mean(cal2)
    noise1 = noise1 - np.mean(noise1)
    noise2 = noise2 - np.mean(noise2)
    
    # ---------- Antenna parameters -------------------
    # Get the antenna properties:

    
    geom = raw_input('Antenna geometry? (square or tri) [default: tri]: ') or 'tri'
    ant_AWG = int(raw_input('Antenna AWG [default 16]: ') or 16)
    ant_baseline = float(raw_input('Antenna baseline (cm) [default 260]:') or 260) # cm
    Na = int(raw_input('Antenna number of turns [default 13]: ') or 13)
    # geom = 'square'
    # ant_AWG = 18
    # ant_baseline = 81 # cm
    # Na = 17 # number of turns

    # Ra, La, Sba, Sea, Fca, Aa = isosceles_right_triangle_antenna_params(ant_AWG, ant_baseline, Na)
    if 'sq' in geom:
        Ra, La, Sba, Sea, Fca, Aa = square_antenna_params(ant_AWG, ant_baseline, Na)
    if 'tri' in geom:
        Ra, La, Sba, Sea, Fca, Aa = isosceles_right_triangle_antenna_params(ant_AWG, ant_baseline, Na)
#     print Ra, La, Sba, Sea, Fca, Aa
    print "This antenna has R = %2.4g Ohms, L = %2.4g mH"%(Ra, La*1000)


    # ----------- Caltone parameters ----------------
    # Caltone parameters:
    m = pow(2.0,10) - 1;

    # FrequencySpacing = (10.24e6/4)/m # LF version 1.0
    # FrequencySpacing = (10.00e6/4)/m # LF version 1.1 and on

    Rcal = 10000  # Rcal - calibration injection resistance
    Rd = 1        # Dummy loop resistance, ohms
    Ld = .001     # Dummy loop inductance, henries
    Lp = 12e-6    # Inductance of transformer primary, henries
    Rm = 1        # Resistance of matching electronics

    Vpp_meas = 2.0; # (V) peak-to-peak voltage of the caltone testpoints
    inp_divider = 100/(100+2100); # (Unitless) Divider from testpoint to system input
    Vcal = (Vpp_meas / 2)*inp_divider*np.sqrt(2*(m+1))/m;

    # CALCULATE EQUIVALENT CALTONE MAGNETIC FIELD, IN pT, VALID FOR f>>fc
    conversion = La/(Rcal*Na*Aa)*1e12 # converts volts to pT
    Bcal_Nominal = Vcal*conversion     # equivalent magnetic field of the each caltone frequency component
    
    # ---------- Caltone PSD ------------------
    print "Calculating tone PSD..."

    # Try it for all possible caltones (some cards use 10.24MHz, some use 10.0MHz.)
    # We validate the caltone by finding a smooth gradient between peaks, with substantial amplitude

    if is_LF:
        # LF cards -- There's at least two versions, depending on what chip is on the preamp cards
        potential_spacings =  [10.00e6/4/m, 10.24e6/4/m]
    else:
        # VLF cards -- I think they're all like this (~250.244 Hz)
        potential_spacings = [10.24e5/4/m]

    for spacing in potential_spacings:
        FrequencySpacing1 = spacing
        NFFT1 = int(round(1000/FrequencySpacing1*Fs*caltone_length))
        caltonefft1 = np.fft.fft(cal1,NFFT1)
        peak_inds = np.arange(1000, NFFT1/2 + 1001, 1000, dtype=int)
        # Square sum ~ 10 bins on either side of the center frequency:
        peakvals1 = np.sqrt(np.array([np.sum(pow(np.abs(caltonefft1[p-10:p+10]),2)) for p in peak_inds]))

        if ((np.max(np.diff(peakvals1)) < 10e6) & (np.max(peakvals1) > 1000)):
            print "Found caltone 1 with spacing %1.2e Hz"%(spacing*4*m)
            break

    for spacing in potential_spacings:
        FrequencySpacing2 = spacing
        NFFT2 = int(round(1000/FrequencySpacing2*Fs*caltone_length))
        caltonefft2 = np.fft.fft(cal2,NFFT2)
        peak_inds = np.arange(1000, NFFT2/2 + 1001, 1000, dtype=int)
        
        # Square sum ~ 10 bins on either side of the center frequency:
        peakvals2 = np.sqrt(np.array([np.sum(pow(np.abs(caltonefft2[p-10:p+10]),2)) for p in peak_inds]))

        if ((np.max(np.diff(peakvals2)) < 10e6) & (np.max(peakvals2) > 1000)):
            print "Found caltone 2 with spacing %1.2e Hz"%(spacing*4*m)
            break

    # ----------- Noise floor PSD --------------
    # Power spectral density estimates for noisefloor, using Pwelch:
    print "Calculating noise PSD..."
    nperseg = int(len(noise1)/200)
    noverlap = nperseg/2

    window = signal.get_window('hamming', nperseg)
    noisefreqs, noise_spectrum_1 = signal.welch(noise1, nperseg = nperseg, window = window, noverlap = noverlap, fs = int(Fs))
    noisefreqs, noise_spectrum_2 = signal.welch(noise2, nperseg = nperseg, window = window, noverlap = noverlap, fs = int(Fs))
    
    
    # ----------- Calculate response -----------
    print "Calculating response curves..."
    Omega = 2*np.pi*FrequencySpacing1*np.arange(1, len(peak_inds)+1,1)*1.0
    Za = Ra + 1j*Omega*La   # Impedance of antenna
    Zd = Rd + 1j*Omega*Ld   # Impedance of dummy loop
    Zp = Lp*Rm/(Lp + Rm)    # Impedance of transformer primary
    Bcal = Vcal*(Za+Zp)/(1j*Omega*Na*Aa)/(2*Rcal+Zd*Zp/(Zd+Zp))*1E12
    CorrectionFactor = Bcal/Bcal_Nominal


    freq_vec = np.linspace(0,Fs/2./1000., 501)
    response1_raw = peakvals1/pow(2,16)*10*1000/Bcal/len(cal1)*2  # Allegedly: mV(output)/pT(input)
    response2_raw = peakvals2/pow(2,16)*10*1000/Bcal/len(cal2)*2

    response1 = interp1d(Omega/2./np.pi/1000., response1_raw, bounds_error=False, fill_value ='extrapolate')(freq_vec)
    response2 = interp1d(Omega/2./np.pi/1000., response2_raw, bounds_error=False, fill_value ='extrapolate')(freq_vec)

    responseRatio = np.abs(response1/np.abs(response2))

    noiseresponse1 = interp1d(noisefreqs, noise_spectrum_1, bounds_error=False, fill_value= 'extrapolate')(freq_vec*1000.)
    noiseresponse2 = interp1d(noisefreqs, noise_spectrum_2, bounds_error=False, fill_value= 'extrapolate')(freq_vec*1000.)

    peakvals1_int = interp1d(peak_inds*FrequencySpacing1, peakvals1, bounds_error=False, fill_value ='extrapolate')(freq_vec*1000.)
    peakvals2_int = interp1d(peak_inds*FrequencySpacing2, peakvals2, bounds_error=False, fill_value ='extrapolate')(freq_vec*1000.)

    Bcal_int = interp1d(Omega, Bcal, bounds_error=False, fill_value='extrapolate')(freq_vec*1000.*2.*np.pi)

    noiseresponse1 = noiseresponse1*pow(Bcal_int/peakvals1_int*Fs,2)
    noiseresponse2 = noiseresponse2*pow(Bcal_int/peakvals2_int*Fs,2)

    # ------- Create output variables ------------
    FrequencyResponseNS = np.stack([freq_vec, response1]).T
    FrequencyResponseEW = np.stack([freq_vec, response2]).T

    CalibrationNumberNS = np.stack([freq_vec, 1./(response1)*1000*10/pow(2,16)]).T
    CalibrationNumberEW = np.stack([freq_vec, 1./(response2)*1000*10/pow(2,16)]).T

    NoiseResponseNS = np.stack([freq_vec, noiseresponse1]).T
    NoiseResponseEW = np.stack([freq_vec, noiseresponse2]).T

    print "Saving CalibrationVariables.mat"
    outdict = dict()
    outdict['FrequencyResponseNS'] = FrequencyResponseNS
    outdict['FrequencyResponseEW'] = FrequencyResponseEW
    outdict['CalibrationNumberNS'] = CalibrationNumberNS
    outdict['CalibrationNumberEW'] = CalibrationNumberEW
    outdict['NoiseResponseNS'] = NoiseResponseNS
    outdict['NoiseResponseEW'] = NoiseResponseEW
    outdict['ResponseRatio'] = responseRatio
    outdict['AntennaParams'] = np.array('Type: %s, AWG: %d, Baseline: %g cm, Turns: %d'%(geom, ant_AWG, ant_baseline, Na))

    return outdict
    
if __name__ == '__main__':
    ''' LF antenna calibration script:
    Usage: python calibrate_LF.py <datafile containing a blip of calibration tones>
    
    This script will:  
        - Ask you for antenna information (AWG, baseline, number of turns)
        - Find the caltone within the datafile
        - Find a quiet region within the datafile
        - Calculate the frequency response, noise floor, and ratio between the channels
        - Output some plots
        - Output CalibrationVariables.mat, so your spectrograms will be scaled appropriately!
    '''

    print("Please open the Matlab file containing the calibration tone:")

    root = Tkinter.Tk()
    root.withdraw()
    file_name = tkFileDialog.askopenfilename()

    # # Some setup to use the WX file dialogs:
    # app = wx.App(redirect=False)
    # frame = wx.Frame(None, -1, 'win.py')
    # frame.SetDimensions(0,0,200,50)

    # # Create open file dialog
    # openFileDialog = wx.FileDialog(frame, "Open", "", "", "Matlab files (*.mat)|*.mat", 
    #         wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

    # outDirDialog = wx.DirDialog(frame,"Open","",
    #         wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)

    # openFileDialog.ShowModal()
    # file_name = openFileDialog.GetPath()
    # Load the input files:
    # file_path = '.'
    # file_name = sys.argv[1]
    fn1 = file_name[0:-8] + '_000.mat'
    fn2 = file_name[0:-8] + '_001.mat'

    print('file 1: %s'%fn1)
    print('file 2: %s'%fn2)
    file1 = loadmat(fn1, squeeze_me = True)
    file2 = loadmat(fn2, squeeze_me = True)

    # Run the calibration function
    caldict = calibrate_2ch(file1, file2)

    print('Please select an output directory:')
    outpath = tkFileDialog.askdirectory()

    # outDirDialog.ShowModal()
    # outpath = outDirDialog.GetPath()

    # Plot it!
    fig, ax = plot_frequency_response(caldict['FrequencyResponseNS'], caldict['FrequencyResponseEW'])
    fig.savefig(os.path.join(outpath, 'CalibrationResponse.pdf'))

    fig, ax = plot_noise_floor(caldict['NoiseResponseNS'],caldict['NoiseResponseEW'])
    fig.savefig(os.path.join(outpath, 'NoiseResponse.pdf'))

    fig, ax = plot_calibration_number(caldict['CalibrationNumberNS'], caldict['CalibrationNumberEW'])
    fig.savefig(os.path.join(outpath, 'CalibrationNumber.pdf'))

    fig, ax = plot_response_ratio(caldict['FrequencyResponseNS'][:,0], caldict['ResponseRatio'])
    fig.savefig(os.path.join(outpath, 'ResponseRatio.pdf'))

    notes = raw_input('Any additional metadata (site name, calibration description, etc): ')

    caldict['notes'] = notes
    caldict['date_created'] = datetime.datetime.utcnow().isoformat()
    # Save it:
    savemat(os.path.join(outpath,'CalibrationVariables'),caldict, format='4')

    raw_input('press return key to exit')

