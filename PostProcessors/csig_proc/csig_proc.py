"""
Cython signal processing module
To compile:

>>> python setup_csig_proc.py build_ext --inplace

"""
cimport cython
import numpy as np
cimport numpy as np
import scipy.fftpack as fft

ctypedef np.float64_t DTYPE_t
DTYPE = np.float64

ctypedef np.complex128_t CDTYPE_t
CDTYPE = np.complex128

ctypedef np.int_t DTYPEi_t
DTYPEi = np.int

cdef extern from "math.h":
    double cos(double theta)
    double sin(double theta)
    double acos(double x)
    double asin(double x)
    double sqrt(double x)
    double atan2(double a, double b)
    double tan(double theta)
    double atan(double x)
    double fabs(double x)
    double pow(double x, double y)
    double floor(double x)
    double ceil(double x)
    double fmod(double x,double x)
    double sqrt(double x)
    double exp(double x)

"""
#only works with minGW:
cdef extern from "complex.h":
    double complex cexp(double complex)
    double complex csqrt(double complex)
    double complex cpow(double complex, double complex)
    double complex conj(double complex)
"""

cdef inline int int_max(int a, int b): return a if a >= b else b
cdef inline int int_min(int a, int b): return a if a <= b else b
cdef inline double double_max(double a, double b): return a if a >= b else b
cdef inline double double_min(double a, double b): return a if a <= b else b
cdef inline double pos_round(double x): return floor(x + .5)
cdef inline double neg_round(double x): return ceil(x-.5)
cdef inline double sinc(double x): return 1.0 if fabs(x) < 0.00001 else sin(x*3.14159265358979323846)/(x*3.14159265358979323846)

#------------------------------------------------------------------------

def calcQuadPeak(double y1,double y2,double y3):
    """
    returns index and amplitude of quadratic maxima (x0,y0)
    from values y1,y2,y3 spaced on [x1,x2,x3] = [-1,0,1]
    """
    cdef double x0,y0
    x0 =  .5*(y1-y3)/(y1-2.0*y2 + y3)
    y0 = y2 - .25*(y1-y3)*x0
    return x0,y0


#--------------------------------------------------------------------

@cython.wraparound(False)
@cython.boundscheck(False)
def find_harmonics_helper(np.ndarray[DTYPE_t, ndim=1] t not None, \
                         np.ndarray[DTYPEi_t, ndim=1] k not None, double f0):

    """
    Returns HT and HTH for use with find_harmonics_c
    Manual sinc handling
    """
    cdef Py_ssize_t i, j, Mi

    cdef int N = t.shape[0]
    cdef int M = k.shape[0]

    cdef np.ndarray[DTYPE_t, ndim=2] Ht = np.empty([2*M,N], dtype=DTYPE)
    cdef np.ndarray[DTYPE_t, ndim=2] HTH = np.empty([2*M,2*M], dtype=DTYPE)

    cdef double PI = 3.14159265358979323846
    cdef double _2PIf0 = 2.0*PI*f0
    cdef double tmp
    cdef double dt, x_i_m_j, x_i_p_j, m1, m2, G1, G2, G3, G4

    Mi = M
    for i from 0 <= i < M:
        for j from 0 <= j < N:
            tmp = _2PIf0*k[i]*t[j]
            Ht[i,j] = cos(tmp)
            Ht[i+Mi,j] = sin(tmp)

    i = 1
    j = 0
    dt = t[i] - t[j]

    m1 = 2*N-1.0
    m2 = N-1.0

    for i from 0 <= i < M:
        for j from 0 <= j < M:
            x_i_m_j = (k[i] - k[j])*f0*dt*PI
            x_i_p_j = (k[i] + k[j])*f0*dt*PI


            if i==j:
                G1 = 1.0
                G3 = sin(x_i_m_j*N)
            else:
                G1 = sin(m1*x_i_m_j)/(m1*sin(x_i_m_j))
                G3 = sin(m2*x_i_m_j)/(m2*sin(x_i_m_j))*sin(x_i_m_j*N)

            G2 = sin(m1*x_i_p_j)/(m1*sin(x_i_p_j))
            G4 = sin(m2*x_i_p_j)/(m2*sin(x_i_p_j))*sin(x_i_p_j*N)


            HTH[i,j] = .25*m1*(G1+G2) + .5
            HTH[Mi+i,Mi+j] = .25*m1*(G1-G2)
            HTH[Mi+i,j] = .5*m2*(G3 + G4)
            HTH[j,Mi+i] = .5*m2*(G3 + G4)

    return (Ht,HTH)



@cython.wraparound(False)
@cython.boundscheck(False)
def isolateHum_helper(np.ndarray[DTYPE_t,ndim=1] ab not None,\
                      np.ndarray[DTYPEi_t, ndim=1] k not None,\
                      np.ndarray[DTYPE_t, ndim=1] t not None,\
                      double f0):
    cdef Py_ssize_t i, j, Mi

    cdef int N = t.shape[0]
    cdef int M = k.shape[0]
    cdef double PI = 3.14159265358979323846
    cdef double fctr
    cdef double mag, pha

    cdef np.ndarray[DTYPE_t, ndim=1] y = np.zeros(N, dtype=DTYPE)

    Mi = M
    for i from 0 <= i < M:  #iterate through harmonics
        fctr = 2.0*PI*f0*k[i]
        mag = sqrt(ab[i]*ab[i] + ab[Mi+i]*ab[Mi+i])
        pha = -atan2(ab[Mi+i],ab[i])

        for j from 0 <= j < N:   #go through time
            y[j] = y[j] + mag*cos(fctr*t[j] + pha)

    return y


@cython.wraparound(False)
@cython.boundscheck(False)
def find_harmonics_helper_old(np.ndarray[DTYPE_t, ndim=1] t not None, \
                         np.ndarray[DTYPEi_t, ndim=1] k not None, double f0):

    """
    Returns HT and HTH for use with find_harmonics_c
    """
    cdef Py_ssize_t i, j, Mi

    cdef int N = t.shape[0]
    cdef int M = k.shape[0]

    cdef np.ndarray[DTYPE_t, ndim=2] Ht = np.empty([2*M,N], dtype=DTYPE)
    cdef np.ndarray[DTYPE_t, ndim=2] HTH = np.empty([2*M,2*M], dtype=DTYPE)

    cdef double PI = 3.14159265358979323846
    cdef double _2PIf0 = 2.0*PI*f0
    cdef double tmp
    cdef double dt, x_i_m_j, x_i_p_j, m1, m2, inv_sinc_i_m_j, inv_sinc_i_p_j, G1, G2, G3, G4

    Mi = M
    for i from 0 <= i < M:
        for j from 0 <= j < N:
            tmp = _2PIf0*k[i]*t[j]
            Ht[i,j] = cos(tmp)
            Ht[i+Mi,j] = sin(tmp)

    i = 1
    j = 0
    dt = t[i] - t[j]

    m1 = 2*N-1.0
    m2 = N-1.0

    for i from 0 <= i < M:
        for j from 0 <= j < M:
            x_i_m_j = (k[i] - k[j])*f0*dt
            x_i_p_j = (k[i] + k[j])*f0*dt


            inv_sinc_i_m_j = 1.0/sinc(x_i_m_j)
            inv_sinc_i_p_j = 1.0/sinc(x_i_p_j)


            G1 = sinc(m1*x_i_m_j)*inv_sinc_i_m_j
            G2 = sinc(m1*x_i_p_j)*inv_sinc_i_p_j
            G3 = sinc(m2*x_i_m_j)*inv_sinc_i_m_j*sin(PI*x_i_m_j*N)
            G4 = sinc(m2*x_i_p_j)*inv_sinc_i_p_j*sin(PI*x_i_p_j*N)


            HTH[i,j] = .25*m1*(G1+G2) + .5
            HTH[Mi+i,Mi+j] = .25*m1*(G1-G2)
            HTH[Mi+i,j] = .5*m2*(G3 + G4)
            HTH[j,Mi+i] = .5*m2*(G3 + G4)

    return (Ht,HTH)




#--------------------------------------------------------------------
"""
@cython.wraparound(False)
@cython.boundscheck(False)
def find_harmonics_helper_cmplx(np.ndarray[DTYPEi_t, ndim=1] k not None,
                                np.ndarray[DTYPE_t, ndim=1] t not None,
                                double f0):
    ""
    Help to sig_proc.find_harmonics_ls_cmplx_fc
    ""

    cdef Py_ssize_t i, j, Mi

    cdef int L = t.shape[0]
    cdef int M = k.shape[0]

    cdef np.ndarray[CDTYPE_t, ndim=2] H = np.empty([L,2*M], dtype=CDTYPE)
    cdef np.ndarray[CDTYPE_t, ndim=2] HTH = np.empty([2*M,2*M], dtype=CDTYPE)

    cdef double PI = 3.14159265358979323846
    cdef double complex _2jPIf0 = 2.0*PI*f0*csqrt(-1.0)
    cdef double complex _2jPIf0dt, _2jPIf0dtL
    cdef double complex J = csqrt(-1.0)
    cdef double tmp
    cdef double _2PIf0 = 2.0*PI*f0


    Mi = M
    for i from 0 <= i < L:
        for j from 0 <= j < M:
##            H[i,j] = cexp(_2jPIf0*k[j]*t[i])

            tmp = _2PIf0*k[j]*t[i]
            H[i,j] = cos(tmp) + J*sin(tmp)

            H[i,j+Mi] = conj(H[i,j])



    i = 1
    j = 0
    _2jPIf0dt = _2jPIf0*(t[i]-t[j])
    _2jPIf0dtL = _2jPIf0dt*L


    for i from 0 <= i < M:
        for j from 0 <= j < M:
            if i==j:
                HTH[i,j] = <double complex>L
            else:
                HTH[i,j] = (cexp(_2jPIf0dtL*(-k[i]+k[j])) - 1.0)/(cexp(_2jPIf0dt*(-k[i]+k[j]))-1.0)

            HTH[i,Mi+j] = (cexp(_2jPIf0dtL*(-k[i]-k[j]))-1.0)/(cexp(_2jPIf0dt*(-k[i]-k[j]))-1.0)

            HTH[Mi+i,Mi+j] = conj(HTH[i,j])
            HTH[Mi+i,j] = conj(HTH[i,Mi+j])



    return H, HTH


"""


#--------------------------------------------------------------------

def real_fftfilt_helper64(np.ndarray[DTYPE_t, ndim=1] x not None,\
                        np.ndarray[DTYPE_t, ndim=1] h not None, int N_fft):

    cdef Py_ssize_t i, j, offset, il, k, L
    cdef int N_x = x.shape[0]
    cdef int N_b = h.shape[0]

    L = N_fft - N_b + 1

    cdef np.ndarray[DTYPE_t, ndim=1] y = np.zeros(N_x, dtype=DTYPE)
    cdef np.ndarray[DTYPE_t, ndim=1] H = np.zeros(N_fft, dtype=DTYPE)

    H = fft.rfft(h,N_fft)
    offset = (N_b-1)/2  #compensate for filter delay
    i = offset
    while i <= N_x:
        il = int_min(i+L,N_x)
        k = int_min(i+N_fft,N_x)
##                yt = fft.irfft(mult_rfft(fft.rfft(x[i:il],N_fft),H)) # Overlap..

        # Overlap..
        yt = fft.irfft(mult_rfft(fft.rfft(x[i:il],N_fft),H))

        for j from 0 <= j < k-i:
            y[i-offset + j] = y[i-offset + j] + yt[j]   # and add

        i = i+ L

    return y


#--------------------------------------------------------------------

@cython.wraparound(False)
@cython.boundscheck(False)
def mult_rfft(np.ndarray[DTYPE_t, ndim=1] X not None,\
              np.ndarray[DTYPE_t, ndim=1] Y not None):
    """
    Multiply two outputs from rfft and return result ready for irfft
    rfft returns: [X(0), real(X(1)), imag(X(1)), ... , X(N/2)]
    """
    cdef Py_ssize_t i
    cdef int lenx = X.shape[0]
    cdef double x, y, xx, yy

    cdef np.ndarray[DTYPE_t, ndim=1] Z = np.empty(lenx, dtype=DTYPE)

    i = 0
    Z[i] = X[i]*Y[i]
    i = lenx - 1
    Z[i] = X[i]*Y[i]

    for i from 1 <= i < lenx-1 by 2:
        x = X[i]
        y = Y[i]
        xx = X[i+1]
        yy = Y[i+1]
        Z[i] = x*y - xx*yy
        Z[i+1] = x*yy + xx*y

##    Z[1:-1:2] = X[1:-1:2]*Y[1:-1:2] - X[2::2]*Y[2::2]
##    Z[2::2] = X[1:-1:2]*Y[2::2] + X[2::2]*Y[1:-1:2]

    return Z




#--------------------------------------------------------------------
cdef double _great_circle(double lat1, double lon1, double lat2, double lon2):
    cdef double radius = 6370.0
    cdef double PI = 3.14159265358979323846
    cdef double D2R = PI/180.0
    cdef double a,b,theta,c

    a = (90.0 - lat1)*D2R
    b = (90.0 - lat2)*D2R
    theta = (lon2-lon1)*D2R
    c = acos((cos(a)*cos(b)) + (sin(a)*sin(b)*cos(theta)))
    return radius*c



#--------------------------------------------------------------------
@cython.wraparound(False)
@cython.boundscheck(False)
def strikeOrder(np.ndarray[DTYPE_t, ndim=1] t not None, \
                np.ndarray[DTYPE_t, ndim=1] lat not None, \
                np.ndarray[DTYPE_t, ndim=1] lon not None, \
                double DIST=10.0, double DT0=1.0, double DT=0.5, int max_strokes=15):
    """
    Determine strike order for stroke data
    so = stikeOrder(t,lat,lon,DIST=10.0,DT0=1.0,DT=0.5,max_strokes=15)
    See Cummins 1998 (JGR)
    """
    cdef Py_ssize_t i, j, i_1
    cdef int lenx = t.shape[0]
    cdef double dist, smallest_dist

    cdef np.ndarray[DTYPEi_t, ndim=1] so = np.ones(lenx, dtype=DTYPEi)
    cdef np.ndarray[DTYPEi_t, ndim=1] firstStroke = np.ones(lenx, dtype=DTYPEi) #index of first stroke in flash

    for i from 1 <= i < lenx:
        j = i-1
        smallest_dist = DIST
        while (j >=0) & (t[j] > t[i] - DT):
            if so[j]==1:
                i_1 = j
            elif so[j]==max_strokes:
                j = j - 1
                continue
            else:
                i_1 = firstStroke[j]

            if t[i_1] > t[i]-DT0:

                dist = _great_circle(lat[i],lon[i],lat[i_1],lon[i_1])

                if dist < smallest_dist:
                    smallest_dist = dist
                    so[i] = so[j] + 1
                    firstStroke[i] = i_1

            j = j - 1

    return so

#-----------------------------------------------------------------------------



cdef double _shiftAngleRange(double angle, double theta0):
    cdef double PI = 3.14159265358979323846
    if angle < theta0:
        angle = angle + 2.0*PI
    if angle > theta0 + 2.0*PI:
        angle = angle - 2.0*PI
    return angle

#-----------------------------------------------------------------------------

cdef struct azdist:
    double azimuth  #[deg]
    double distance #[km]

cdef struct constants:
    double PI
    double D2R
    double R2D
    double SPEED_OF_LIGHT
    double Rinv

cdef constants _getConstants():
    cdef constants co
    co.PI = 3.14159265358979323846
    co.D2R = co.PI/180.0
    co.R2D = 180.0/co.PI
    co.SPEED_OF_LIGHT = 299792458.0 #[m/s]
    co.Rinv = 1.0/6352.9 #[km] To match Vaisala code in converting baseline distance to radians
    return co

cdef struct earth:
    #WGS-84
    double major
    double minor
    double f
    double a
    double b

cdef earth _getEarth():
    cdef earth ea
    ea.major = 6378.137    #[km]
    ea.minor = 6356.7523142
    ea.f = 1.0/298.257223563
    ea.a =ea.major
    ea.b = ea.minor
    return ea


cdef double _getGeocentricLat(double lat):
    """
    Input: geodetic ('normal') latitude, in degrees
    Output: geocentric latitude, in degrees
    """
    cdef constants co = _getConstants()
    cdef earth ea = _getEarth()

    cdef double latRad = lat*co.D2R
    cdef double lambda_d = co.PI/2.0 - latRad
    cdef double lambda_c = atan(pow(ea.b,2)/pow(ea.a,2.0)*tan(lambda_d))
    return (co.PI/2.0 - lambda_c)*co.R2D

cdef double _localRadius(double lat, double alt):
    """ calculate local radius, in km
    Input: geodetic ('normal') latitude, in degrees
           alt: altitude, in km
    Output: local radius, in km
    """
    cdef constants co = _getConstants()
    cdef earth ea = _getEarth()
    cdef double phi = _getGeocentricLat(lat)*co.D2R
    return ea.b/sqrt(1+pow(cos(phi),2)*(pow(ea.b,2)/pow(ea.a,2)-1)) + alt


cdef double _getSineCgcLatitude(double lat):
    """ gets the sine of the co-geo-centric latitude
    Meant for compatibility with Vaisala's hyperbolic.cc
    """
    cdef constants co = _getConstants()
    cdef double lat_gc = _getGeocentricLat(lat) #geo-centric latitude
    return sin(co.PI/2-lat_gc*co.D2R)    #sine of geo-centric co-latitude

cdef double _getCosineCgcLatitude(double lat):
    """ gets the cosine of the co-geo-centric latitude
    Meant for compatibility with Vaisala's hyperbolic.cc
    """
    cdef constants co = _getConstants()
    cdef double lat_gc = _getGeocentricLat(lat) #geo-centric latitude
    return cos(co.PI/2-lat_gc*co.D2R)    #sine of geo-centric co-latitude


cdef double _getSineBaseline(azdist az_dist):
    cdef constants co = _getConstants()
    return sin(az_dist.distance*co.Rinv)

cdef double _getCosineBaseline(azdist az_dist):
    cdef constants co = _getConstants()
    return cos(az_dist.distance*co.Rinv)


#----------------------------------------------------------------------------

cdef struct latlon:
    double lat
    double lon

cdef latlon _estPosSphere(double lat0, double lon0, double range, double bearing0):
    """
    Given position, range, and bearing, estimate new position assuming spherical earth
    """

    cdef constants co = _getConstants()
    cdef earth ea = _getEarth()
    cdef double R0 = 6370.0

    cdef latlon out

    if fabs(range) < 0.01:
        out.lat = lat0
        out.lon = lon0
        return out

    #convert to rad:
    cdef double lat = lat0*co.D2R
    cdef double lon = lon0*co.D2R
    cdef double bearing = bearing0*co.D2R

    cdef double colat0 = co.PI/2.0 - lat
    cdef double dOverR = range/R0

    cdef double cthl = cos(dOverR)*cos(colat0) + sin(dOverR)*sin(colat0)*cos(bearing)
    cdef double ltgColat = acos(cthl)

    cdef double clgd = (cos(dOverR)-cos(colat0)*cthl)/(sin(colat0) * sin(ltgColat))

    cdef double modangle = fmod(bearing,2.0*co.PI)    #algorithm change by Ryan Said
    if modangle < 0:
        modangle = modangle + 2*co.PI



    cdef double lngDiff = acos(clgd)

    if (((modangle <= co.PI) & (range >= 0.0)) | ((modangle > co.PI) & (range < 0.0))): #algorithm change by Ryan Said
        lngDiff = -1.0*lngDiff




    out.lat = (co.PI/2 - ltgColat)*co.R2D
    out.lon = (lon - lngDiff)*co.R2D


    return out


def estPosSphere(double lat, double lon, double range, double bearing):
    """
    calculate estimated position (scalar)
    """
    cdef latlon coord = _estPosSphere(lat,lon,range,bearing)
    return coord.lat, coord.lon

@cython.wraparound(False)
@cython.boundscheck(False)
def estPosSphereRangeVec(double lat, double lon, \
                    np.ndarray[DTYPE_t,ndim=1] range not None,\
                    double bearing):
    """
    calculate estimated position for a vector of ranges
    """
    cdef Py_ssize_t i
    cdef int n = range.shape[0]

    cdef np.ndarray[DTYPE_t, ndim=1] lat2 = np.zeros(n, dtype=DTYPE)
    cdef np.ndarray[DTYPE_t, ndim=1] lon2 = np.zeros(n, dtype=DTYPE)

    cdef latlon coord

    for i from 0 <= i < n:
        coord = _estPosSphere(lat,lon,range[i],bearing)
        lat2[i] = coord.lat
        lon2[i] = coord.lon

    return lat2,lon2

#-----------------------------------------------------------------------------

cdef azdist _azDist(double Lat1, double Lon1, double Lat2, double Lon2):
    """
    Calculate azimuth and distance from (lat1,lon1) to (lat2, lon2)
    Quick calculation for scalars only
    """

    cdef azdist az_dist
    cdef constants co = _getConstants()
    cdef earth ea = _getEarth()

    cdef double asq, bsq, e1, e2, c, elev1, elev2

    cdef double PI = co.PI
    cdef double D2R = co.D2R

    cdef double N1, x1, y1, z1, N2, x2, y2, z2
    cdef double dx, dy, dz, chord
    cdef double num, denom, angle, V, N, M, R, dist
    cdef double lat1, lon1, lat2, lon2

    asq = pow(ea.major,2.0)
    bsq = pow(ea.minor,2.0)

    e1 = (asq - bsq)/asq
    e2 =(asq-bsq)/bsq
    c = asq/ea.minor

    elev1 = 0.0
    elev2 = 0.0

    lat1 = Lat1*D2R
    lon1 = Lon1*D2R
    lat2 = Lat2*D2R
    lon2 = Lon2*D2R

    N1 = elev1 + c/sqrt(1+e2*cos(lat1)*cos(lat1))
    x1 = N1*cos(lat1)*cos(lon1)
    y1 = N1*cos(lat1)*sin(lon1)
    z1 = N1*sin(lat1)*(1-e1)

    N2 = elev2 + c/sqrt(1+e2*cos(lat2)*cos(lat2))
    x2 = N2*cos(lat2)*cos(lon2)
    y2 = N2*cos(lat2)*sin(lon2)
    z2 = N2*sin(lat2)*(1-e1)

    dx = x1-x2
    dy = y1-y2
    dz = z1-z2

    chord = sqrt(dx*dx + dy*dy + dz*dz)

    num = dx*sin(lon1) - dy*cos(lon1)
    denom = dx*sin(lat1)*cos(lon1) + dy*sin(lat1)*sin(lon1) - dz*cos(lat1)

    angle = atan2(num,denom)

    angle = _shiftAngleRange(angle,0.0)

    V = sqrt(1+e2*pow(cos((lat1 + lat2)/2.0),2))
    N = c/V
    M = N/V**2
    R = M*N/(M*sin(angle)**2 + N*pow(cos(angle),2.0))

    dist = 2*R*asin(chord/(2*R))

    az_dist.azimuth = angle*180.0/PI    #[deg]
    az_dist.distance = dist
    return az_dist


#----------------------------------------------------------------------------
@cython.wraparound(False)
@cython.boundscheck(False)
##def calc_xi2(np.ndarray[DTYPE_t, ndim=1] llt not None, #lat, lon, t0_ms triplet
def calc_xi2(double lat0,double lon0,double t0_ms,\
             np.ndarray[DTYPE_t, ndim=1] lat_s not None,np.ndarray[DTYPE_t, ndim=1] lon_s not None,
             np.ndarray[DTYPE_t, ndim=1] t_s not None,np.ndarray[DTYPE_t, ndim=1] sigma_t not None, int use_time,
             np.ndarray[DTYPE_t, ndim=1] theta_s not None,np.ndarray[DTYPE_t, ndim=1] sigma_theta not None, int use_az):

    """
    strike location and time in question: (lat,lon),t0 (scalar)
    station location, time: (lat_s,lon_s),t_s in [deg],[s]; should be a list
    NOTE: t0 is in ms, to make same order of magnitude as lat0,lon0
    Includes timing and/or angle (pass in empty t_s or theta_s to exclude one or the other)
    """

    cdef Py_ssize_t ii

    cdef int num_s = lat_s.shape[0]    #Number of sensors

##    cdef double lat0 = llt[0]
##    cdef double lon1 = llt[1]
##    cdef double t0_ms = llt[2]

    cdef double t0 = t0_ms/1e3  #[seconds]
    cdef double C_KM_S = 299792458.0/1e3   #[km/seconds]
    cdef double PI = 3.14159265358979323846
    cdef double delta_theta

    cdef azdist ad

    cdef double xi2 = 0.0

    for ii from 0 <= ii < num_s:

        ad = _azDist(lat_s[ii],lon_s[ii],lat0,lon0)

        if use_time > 0:
            xi2 = xi2 + pow(t0 + ad.distance/C_KM_S - t_s[ii],2.0)/pow(sigma_t[ii],2.0)

        if use_az > 0:
            delta_theta = ad.azimuth-theta_s[ii]
            delta_theta = acos(fabs(cos(delta_theta*PI/180.0)))*180.0/PI
            xi2 = xi2 + pow(delta_theta,2.0)/pow(sigma_theta[ii],2.0)


    return xi2



@cython.wraparound(False)
@cython.boundscheck(False)
##def calc_xi2(np.ndarray[DTYPE_t, ndim=1] llt not None, #lat, lon, t0_ms triplet
def calc_xi2a(double lat0,double lon0,\
             np.ndarray[DTYPE_t, ndim=1] lat_s not None,np.ndarray[DTYPE_t, ndim=1] lon_s not None,
             np.ndarray[DTYPE_t, ndim=1] t_s not None,np.ndarray[DTYPE_t, ndim=1] sigma_t not None, int use_time,
             np.ndarray[DTYPE_t, ndim=1] theta_s not None,np.ndarray[DTYPE_t, ndim=1] sigma_theta not None, int use_az):

    """
    2-d version--don't pass in t0 (calculate on the fly)
    strike location and time in question: (lat,lon),t0 (scalar)
    station location, time: (lat_s,lon_s),t_s in [deg],[s]; should be a list
    NOTE: t0 is in ms, to make same order of magnitude as lat0,lon0
    Includes timing and/or angle (pass in empty t_s or theta_s to exclude one or the other)
    """
    DEF MAX_NUM_SENSORS = 10
    cdef Py_ssize_t ii

    cdef int num_s = lat_s.shape[0]    #Number of sensors

##    cdef double lat0 = llt[0]
##    cdef double lon1 = llt[1]
##    cdef double t0_ms = llt[2]

    cdef double t0 = 0  #[seconds]
    cdef double C_KM_S = 299792458.0/1e3   #[km/seconds]
    cdef double PI = 3.14159265358979323846
    cdef double delta_theta

    cdef azdist ad
    cdef int jj
    cdef double xi2 = 0.0

    cdef double distances[MAX_NUM_SENSORS]
    cdef double azimuths[MAX_NUM_SENSORS]


    for jj from 0 <= jj < num_s:
        ii = jj
        ad = _azDist(lat_s[ii],lon_s[ii],lat0,lon0)
        distances[jj] = ad.distance #[km]
        azimuths[jj] = ad.azimuth
        t0 = t0 + t_s[ii]- distances[jj]/C_KM_S

    t0 = t0/(<float>num_s)  #average event time

    for ii from 0 <= ii < num_s:
        jj = ii
        if use_time > 0:
            xi2 = xi2 + pow(t0 + distances[jj]/C_KM_S - t_s[ii],2.0)/pow(sigma_t[ii],2.0)

        if use_az > 0:
            delta_theta = azimuths[jj]-theta_s[ii]
            delta_theta = acos(fabs(cos(delta_theta*PI/180.0)))*180.0/PI
            xi2 = xi2 + pow(delta_theta,2.0)/pow(sigma_theta[ii],2.0)


    return xi2

#-----------------------------------------------------------------------------

def azDist_chord(double Lat1, double Lon1, double Lat2, double Lon2):
    cdef azdist tmp = _azDist(Lat1,Lon1,Lat2,Lon2)
    return (tmp.azimuth,tmp.distance)


#------------------------------------------------------------------------


@cython.wraparound(False)
@cython.boundscheck(False)
def timeTriangSphere(double lat0, double lon0, double t0,
                    double lat1, double lon1, double t1,
                    double lat2, double lon2, double t2,double _v):

    """
    v in m/sec
    See globe.timeTriangSphere for algorithm, which is derived from
    'On Loran-C Time Difference to Co-ordinate Converters' by Williams, P. and Last, D., University of Wales, Bangor, UK
    """
    cdef double v = _v/1000.0    #convert to km/s

    cdef double PI = 3.14159265358979323846
    cdef R = 6370.0 #[km]
    cdef D2R = PI/180.0
    cdef R2D = 180.0/PI

    cdef double tm = t0
    cdef double tx = t1
    cdef double ty = t2


    cdef double a11,a12,a13,a21,a22,a23,a31,a32,a33
    #inverse:
    cdef double ai11,ai12,ai13,ai21,ai22,ai23,ai31,ai32,ai33

    #primary calculations (offload to helper)
    a11 = R*cos(lat0*D2R)*cos(lon0*D2R)
    a12 = R*cos(lat0*D2R)*sin(lon0*D2R)
    a13 = R*sin(lat0*D2R)

    a21 = R*cos(lat1*D2R)*cos(lon1*D2R)
    a22 = R*cos(lat1*D2R)*sin(lon1*D2R)
    a23 = R*sin(lat1*D2R)

    a31 = R*cos(lat2*D2R)*cos(lon2*D2R)
    a32 = R*cos(lat2*D2R)*sin(lon2*D2R)
    a33 = R*sin(lat2*D2R)

    #calculate inverse
    cdef double det = a11*(a22*a33 - a23*a32) - a12*(a21*a33-a23*a31) + a13*(a21*a32 - a22*a31)
    ai11 = (a22*a33 - a23*a32)/det
    ai12 = (a13*a32 - a12*a33)/det
    ai13 = (a12*a23 - a13*a22)/det
    ai21 = (a23*a31 - a21*a33)/det
    ai22 = (a11*a33 - a13*a31)/det
    ai23 = (a13*a21 - a11*a23)/det
    ai31 = (a21*a32 - a22*a31)/det
    ai32 = (a12*a31 - a11*a32)/det
    ai33 = (a11*a22 - a12*a21)/det


    cdef azdist admx = _azDist(lat0,lon0,lat1,lon1)
    cdef azdist admy = _azDist(lat0,lon0,lat2,lon2)
    cdef azdist adxy = _azDist(lat1,lon1,lat2,lon2)


    cdef double Px = v/R*(tx-tm)
    cdef double Py = v/R*(ty-tm)

    cdef double theta_mx = admx.distance/R
    cdef double theta_my = admy.distance/R

    cdef double ax = (cos(Px) - cos(theta_mx))/sin(theta_mx)
    cdef double ay = (cos(Py) - cos(theta_my))/sin(theta_my)

    cdef double K = acos((cos(adxy.distance/R)-cos(admx.distance/R)*cos(admy.distance/R))/sin(admx.distance/R)/sin(admy.distance/R))

    cdef double u1, u2, u3
    u1 = ax*cos(K) - ay
    u2 = ax*sin(K)
    u3 = ay*sin(Px)/sin(theta_mx) - ax*sin(Py)/sin(theta_my)


    cdef double cos_betax_1 = (u3*u1 + u2*sqrt(u1*u1 + u2*u2 - u3*u3))/(u1*u1 + u2*u2)
    cdef double cos_betax_2 = (u3*u1 - u2*sqrt(u1*u1 + u2*u2 - u3*u3))/(u1*u1 + u2*u2)

    cdef double theta_ms_1 = atan2((cos(Px)-cos(theta_mx)),(sin(Px)+sin(theta_mx)*cos_betax_1)) #IMPORTANT: use atan2!!
    cdef double theta_ms_2 = atan2((cos(Px)-cos(theta_mx)),(sin(Px)+sin(theta_mx)*cos_betax_2))

    cdef double theta_xs_1 = Px + theta_ms_1
    cdef double theta_xs_2 = Px + theta_ms_2

    cdef double theta_ys_1 = Py + theta_ms_1
    cdef double theta_ys_2 = Py + theta_ms_2

    cdef double bA1, bA2, bA3
    cdef double bB1, bB2, bB3
    bA1 = R*R*cos(theta_ms_1)
    bA2 = R*R*cos(theta_xs_1)
    bA3 = R*R*cos(theta_ys_1)

    bB1 = R*R*cos(theta_ms_2)
    bB2 = R*R*cos(theta_xs_2)
    bB3 = R*R*cos(theta_ys_2)


    #coordinate 1:
    cdef double x1,y1,z1

    #take Ainv*B1
    x1 = ai11*bA1 + ai12*bA2 + ai13*bA3
    y1 = ai21*bA1 + ai22*bA2 + ai23*bA3
    z1 = ai31*bA1 + ai32*bA2 + ai33*bA3

    cdef double latA,lonA,tA
    latA = asin(z1/R)*R2D
    lonA = atan2(y1,x1)*R2D
    tA = t0 - theta_ms_1*R/v  #could have used t1 or t2

    #coordinate 2:
    cdef double x2,y2,z2

    #take Ainv*B2
    x2 = ai11*bB1 + ai12*bB2 + ai13*bB3
    y2 = ai21*bB1 + ai22*bB2 + ai23*bB3
    z2 = ai31*bB1 + ai32*bB2 + ai33*bB3

    cdef double latB,lonB,tB
    latB = asin(z2/R)*R2D
    lonB = atan2(y2,x2)*R2D
    tB = t0 - theta_ms_2*R/v  #could have used t1 or t2


    return [latA,latB],[lonA,lonB],[tA,tB]


#------------------------------------------------------------------------


@cython.wraparound(False)
@cython.boundscheck(False)
def filter_and_downsample_r(np.ndarray[DTYPE_t, ndim=1] x not None, \
                          np.ndarray[DTYPE_t, ndim=1] h not None, \
                          int Q):
    """
    Filters data x by h and returns a Q-downsampled result
    Accepts real vectors only
    """

    cdef Py_ssize_t i, j, it, b, j_lo, j_hi

    cdef int nx = x.shape[0]
    cdef int nh = h.shape[0]

    cdef int ny = nx/Q
    cdef double a

    cdef np.ndarray[DTYPE_t, ndim=1] y = np.zeros(ny, dtype=DTYPE)

    b = (nh-1)/2

    for i from 0 <= i < nx by Q:

        j_lo = 0
        j_hi = nh
        if i < b:
            j_lo = b - i
        if nx - i < b:
            j_hi = b + nx - i

        a = 0
        for j from j_lo <= j < j_hi:
            a = a + h[nh-1-j]*x[i+j-b]

        y[i/Q] = a

    return y

@cython.wraparound(False)
@cython.boundscheck(False)
def filter_and_downsample_c(np.ndarray[CDTYPE_t, ndim=1] x not None, \
                          np.ndarray[DTYPE_t, ndim=1] h not None, \
                          int Q):
    """
    Filters data x by h and returns a Q-downsampled result
    Accepts complex vectors only
    """

    cdef Py_ssize_t i, j, it, b, j_lo, j_hi

    cdef int nx = x.shape[0]
    cdef int nh = h.shape[0]

    cdef int ny = nx/Q
    cdef double complex a

    cdef np.ndarray[CDTYPE_t, ndim=1] y = np.zeros(ny, dtype=CDTYPE)

    b = (nh-1)/2

    for i from 0 <= i < nx by Q:

        j_lo = 0
        j_hi = nh
        if i < b:
            j_lo = b - i
        if nx - i < b:
            j_hi = b + nx - i

        a = 0
        for j from j_lo <= j < j_hi:
            a = a + h[nh-1-j]*x[i+j-b]

        y[i/Q] = a

    return y

#------------------------------------

@cython.wraparound(False)
@cython.boundscheck(False)
def upsample_lin_interp(np.ndarray[DTYPE_t,ndim=1] x not None, int Q):
    """
    Upsample x by Q using linear interpolation
    """
    cdef Py_ssize_t i, j

    cdef int nx = x.shape[0]

    cdef int ny = nx*Q

    cdef np.ndarray[DTYPE_t, ndim=1] y = np.zeros(ny, dtype=DTYPE)

    for i from 0 <= i < nx - 1:
        for j from 0 <= j < Q:
            y[i*Q+j]= (<double> j)/(<double> Q)*(x[i+1]-x[i]) + x[i]

    #extend last value flat:
    for j from 0 <= j < Q:
        y[i*Q+j]= x[i]

    return y

#-------------------------------------

@cython.wraparound(False)
@cython.boundscheck(False)
def average_msk_mag_helper(np.ndarray[DTYPE_t,ndim=1] mag_z not None, \
                           np.ndarray[DTYPEi_t,ndim=1] indices_P not None, \
                           int buff, int bit_width):
    """
    Helper function to bbdata.NBChannel.get_reconstructed_mag2
    """

    cdef Py_ssize_t jj, ii, lo, hi

    cdef int L = mag_z.shape[0]

    cdef np.ndarray[DTYPEi_t, ndim=1] category = np.zeros(L, dtype=DTYPEi)
    cdef np.ndarray[DTYPE_t, ndim=1] magV0 = np.zeros(L, dtype=DTYPE)

    cdef double _sum, tot

    for jj from 0 <= jj < L:
        lo = int_max(0,jj-bit_width)
        hi = int_min(L-1,jj + bit_width)
        category[jj] = indices_P[lo]*2*2 + indices_P[jj]*2 + indices_P[hi]

    for jj from buff <= jj < L-buff:
        if magV0[jj] < 1e-6:    #not updated yet
            cat = category[jj]
            _sum = 0.0
            ii = jj
            tot = 0.0
            while ii < L-buff:
                if category[ii]==cat:
                   _sum = _sum + mag_z[ii]
                   tot =  tot + 1.0
                ii += bit_width
            mag = _sum/tot
            ii = jj
            while ii < L-buff:
                if category[ii]==cat:
                    magV0[ii] = mag
                ii = ii + bit_width


    return category,magV0


@cython.wraparound(False)
@cython.boundscheck(False)
def average_msk_mag_helper_window(np.ndarray[DTYPE_t,ndim=1] mag_z not None, \
                           np.ndarray[DTYPEi_t,ndim=1] indices_P not None, \
                           int buff, int bit_width, double decay_len):
    """
    Helper function to bbdata.NBChannel.get_reconstructed*
    Windows the extent of the average
    """

    cdef Py_ssize_t jj, ii, lo, hi

    cdef int L = mag_z.shape[0]

    cdef np.ndarray[DTYPEi_t, ndim=1] category = np.zeros(L, dtype=DTYPEi)
    cdef np.ndarray[DTYPE_t, ndim=1] magV0 = np.zeros(L, dtype=DTYPE)

    cdef double _sum, tot, weight, TOL

    TOL = 1e-1 #=exp(-2.3)

    for jj from 0 <= jj < L:
        lo = int_max(0,jj-bit_width)
        hi = int_min(L-1,jj + bit_width)
        category[jj] = indices_P[lo]*2*2 + indices_P[jj]*2 + indices_P[hi]

    #just copy over:
    for jj from 0 <= jj < buff:
        magV0[jj] = mag_z[jj]

    for jj from L-buff <= jj < L:
        magV0[jj] = mag_z[jj]

    cdef int cat

    for jj from buff <= jj < L-buff:

        cat = category[jj]

        _sum = mag_z[jj]
        tot = 1.0

        ii = jj - bit_width
        while ii > buff:
            if category[ii]==cat:
                weight = exp(-fabs(ii-jj)/decay_len)
                if weight < TOL:
                    break
                _sum = _sum + weight*mag_z[ii]
                tot =  tot + weight
            ii = ii - bit_width


        ii = jj + bit_width
        while ii < L-buff:
            if category[ii]==cat:
                weight = exp(-fabs(ii-jj)/decay_len)
                if weight < TOL:
                    break
                _sum = _sum + weight*mag_z[ii]
                tot =  tot + weight
            ii = ii + bit_width

        mag = _sum/tot

        magV0[jj] = mag


    return category,magV0



@cython.wraparound(False)
@cython.boundscheck(False)
def reconstruct_msk_signal_helper(np.ndarray[DTYPE_t,ndim=1] magV not None,\
                                  np.ndarray[DTYPE_t,ndim=1] aI not None, \
                                  np.ndarray[DTYPE_t,ndim=1] aQ not None,\
                                  np.ndarray[DTYPE_t,ndim=1] t not None,\
                                  double T, double phi1, double phi0, double f0):
    """
    Helper function to bbdata.NBChannel.isolate_nb_channel()
    """

    cdef Py_ssize_t i

    cdef int nx = t.shape[0]

    cdef np.ndarray[DTYPE_t, ndim=1] y = np.zeros(nx, dtype=DTYPE)

    cdef double pi = 3.14159265358979323846

    cdef double pi_2T = pi/(2.0*T)
    cdef double _2pif0 = 2.0*pi*f0

    cdef double pha1, pha0

    for i from 0 <= i < nx:
        pha1 = pi_2T*t[i] + phi1
        pha0 = _2pif0*t[i] + phi0
        y[i] = magV[i]*(aI[i]*cos(pha1)*cos(pha0) + aQ[i]*sin(pha1)*sin(pha0))

    return y

#---------------------------------------------
@cython.wraparound(False)
@cython.boundscheck(False)
def sort_data_into_grid(np.ndarray[DTYPE_t,ndim=1] x not None,\
                          np.ndarray[DTYPE_t,ndim=1] y not None, \
                          int M, int N, double x_min, double dx, double y_min, double dy):

    cdef Py_ssize_t i, i_x, i_y
    cdef int nx = x.shape[0]    #assume ny==nx

    cdef np.ndarray[DTYPEi_t, ndim=2] array = np.zeros([M,N], dtype=DTYPEi)
    for i from 0 <= i < nx:
        i_x = <Py_ssize_t> int((x[i]-x_min)/dx)
        i_y = <Py_ssize_t> int((y[i]-y_min)/dy)

        array[i_x,i_y] = array[i_x,i_y] + 1


    return array

#------------------------------------------------

@cython.wraparound(False)
@cython.boundscheck(False)
#eg call:
#csig_proc.remove_periodic_elements(peak_times,peak_amps,1.0/PARAMS['REM_F%d' % tmpi],.01,.2)
def remove_periodic_elements(np.ndarray[DTYPE_t,ndim=1] t not None,\
                             np.ndarray[DTYPE_t,ndim=1] A not None, \
                             double min_A, double T, double ttol, double atol, int COUNT_CRIT):
    """
    Helper function to bbdata.bbdata.detectSferics
    Removes periodic sferic detection elements
    """

    cdef Py_ssize_t i, j, i_t, i_A
    cdef int nt = t.shape[0]    #assume ny==nx
    cdef double dt
    cdef int count
    cdef np.ndarray[DTYPEi_t, ndim=1] keepIndices = np.ones(nt, dtype=DTYPEi)

    cdef int MAX_SEARCH_WIN = COUNT_CRIT + 2   #number of periods to search on either side

    for i from 0 <= i < nt:
        if A[i] < min_A:
            keepIndices[i] = 0
            continue

        count = 0
        for j from i > j >= 0:  #go from i to 0
            dt = fabs(t[i]-t[j])/T  #number of periods
            if dt > MAX_SEARCH_WIN:
                break

            #check integer relation:
            if fabs(dt - pos_round(dt))<ttol:
                #check amplitude relation:
                if fabs(A[i]-A[j])/fabs(A[i])<atol:
                    count = count + 1
##                    print "%d,%d,%2.4f,%2.4f" % (0,count,fabs(dt - pos_round(dt)), fabs(A[i]-A[j])/fabs(A[i]))

            if count >= COUNT_CRIT:   #found enough
                break

        for j from i < j < nt:  #go from i to 0
            dt = fabs(t[i]-t[j])/T  #number of periods
            if dt > MAX_SEARCH_WIN:
                break

            #check integer relation:
            if fabs(dt - pos_round(dt))<ttol:
                #check amplitude relation:
                if fabs(A[i]-A[j])/fabs(A[i])<atol:
                    count = count + 1
##                    print "%d,%d,%2.4f,%2.4f" % (1,count,fabs(dt - pos_round(dt)), fabs(A[i]-A[j])/fabs(A[i]))

            if count >= COUNT_CRIT:   #found enough
                break

        if count >= COUNT_CRIT:
            keepIndices[i] = 0

    return keepIndices

#------------------------

@cython.wraparound(False)
@cython.boundscheck(False)
#eg:
#keepIndices = csig_proc.check_peak_snr(dataFilt[0],indices,PARAMS['MIN_AMP_DIFF'])
def check_peak_snr(np.ndarray[DTYPE_t,ndim=1] amp not None,\
                   np.ndarray[DTYPEi_t,ndim=1] peakIndices not None, \
                   double min_A_diff):
    """
    Helper function to bbdata.bbdata.detectSferics
    Checks height of peak relative to trough on left side
    """
    cdef Py_ssize_t i, j, i_amp, i_p
    cdef int nA = amp.shape[0]
    cdef int nI = peakIndices.shape[0]
    cdef double peakAmp, prevAmp
    cdef int count
    cdef np.ndarray[DTYPEi_t, ndim=1] keepIndices = np.ones(nI, dtype=DTYPEi)

    for i from 0 <= i < nI:
        peakAmp = amp[peakIndices[i]]
        prevAmp = peakAmp
        i_amp = peakIndices[i]
        for j from i_amp >= j >= 0:
            if amp[j]>prevAmp:  #found trough: amp[j+1]
                if amp[j+1]+min_A_diff>peakAmp:
                    keepIndices[i] = 0
                break
            prevAmp=amp[j]

    return keepIndices

#-----------------------
@cython.wraparound(False)
@cython.boundscheck(False)
#eg:
#keepIndices = csig_proc.find_sferic_onset(t,a,AMP_FCTR,TIME_DELAY,MIN_AMP)
def find_sferic_onset(np.ndarray[DTYPE_t,ndim=1] t not None,
                      np.ndarray[DTYPE_t,ndim=1] a not None,
                      double AMP_FCTR, double TIME_DELAY,double MIN_AMP):
    """
    Given strike times [in seconds] t, and magnitudes a of the measured sferic
    Find the onset of each sferic (an additional filter that could have been applied at
    the receiver; maybe in a future version ...)
    AMP_FCTR: subsequent strike must be > this factor of the last one to be considered new
    (usually AMP_FACTR > 1.0)
    TIME_DELAY: [seconds] subsequnt strike must be more than this to be considered new

    Maybe pass through twice (expect ~ 5% cut after second pass)
    """

    cdef Py_ssize_t i, j
    cdef int nt = t.shape[0]
    cdef np.ndarray[DTYPEi_t, ndim=1] keepIndices = np.ones(nt, dtype=DTYPEi) #set all to True by default

    for i from 1 <= i < nt-1:
        if a[i] < MIN_AMP:
            keepIndices[i] = 0
            continue

        if (a[i] <= a[i-1]*AMP_FCTR) & (t[i] <= t[i-1] + TIME_DELAY):
            keepIndices[i] = 0
            continue

        if (a[i]*AMP_FCTR < a[i+1]) & (t[i] + TIME_DELAY > t[i+1]):
            keepIndices[i] = 0
            continue

        if t[i] <= t[i-1]:
            keepIndices[i] = 0
            continue

    return keepIndices


#------------------------

@cython.wraparound(False)
@cython.boundscheck(False)
#eg:
#keepIndices = csig_proc.remove_radar_echoes(peak_times,peak_amps,Tmin,Tmax,ampRatTol)
def remove_radar_echoes(np.ndarray[DTYPE_t,ndim=1] t not None,
                        np.ndarray[DTYPE_t,ndim=1] A not None,\
                   double Tmin, double Tmax, double atol, double ttol, int min_counts, double min_amp):
    """
    Helper function to bbdata.bbdata.detectSferics
    Checks for radar echos with periodicity between Tmin, Tmax
    """
    cdef Py_ssize_t i, j, k
    cdef int nA = A.shape[0]
    cdef double dt, dt0, lastT0, lastA0
    cdef int count
    cdef int found = 0
    cdef np.ndarray[DTYPEi_t, ndim=1] keepIndices = np.ones(nA, dtype=DTYPEi)

    for i from 0 <= i < nA:
        if found == 1:
            break
        if t[i] > Tmax:
            break

        if A[i] < min_amp:
            continue

        for j from i < j < nA:

            dt = t[j] - t[i]
            if dt < Tmin:
                continue
            if dt > Tmax:
                break
            if fabs(A[i]-A[j])/fabs(A[i])>atol: #need amplitude about the same to have a candidate
                continue
            if found == 1:
                break


            dt0 = dt    #master dt
            lastT0 = t[j]   #last echo time
            lastA0 = A[j]
            count = 2   #start with original and first match
            for k from j < k < nA:
                dt = t[k] - lastT0
                if (dt-dt0)/dt0 > ttol:  #didn't find another one, beyond search radius
                    break

                if (fabs(dt-dt0)/dt0 > ttol):
                    continue
                if  fabs(A[k]-lastA0)/lastA0>atol:
                    continue

                #found a third, fourth, etc  spike
                count = count + 1
                lastT0 = t[k]
                lastA0 = A[k]


            if count >= min_counts:
                found = 1
                keepIndices[i] = 0
                keepIndices[j] = 0
                lastT0 = t[j]   #last echo time
                lastA0 = A[j]

                for k from j < k < nA:
                    dt = t[k] - lastT0

                    if (dt-dt0)/dt0 > ttol:  #didn't find another one, beyond search radius
                        break

                    if (fabs(dt-dt0)/dt0 > ttol):
                        continue
                    if  fabs(A[k]-lastA0)/lastA0>atol:
                        continue

                    #found a third, fourth, etc  spike
                    keepIndices[k] = 0
                    lastT0 = t[k]
                    lastA0 = A[k]



    return keepIndices


#-----------------------------------------------------



cdef struct gcSolution:
    double lat
    double lon
    double dist0
    double dist1

cdef struct gcSolutionPair:
    double iangle
    gcSolution s1
    gcSolution s2

cdef gcSolutionPair _gcIntersection(double lat0,double lon0, double az0,\
                                    double lat1,double lon1, double az1):
    """
    Given stations 0,1 with measured arrival azimuth(s) az, find gc Intersection points
    Taken from Troy's Thesis, Section A.1
    Inputs/Outputs in degrees
    """

    cdef double PI = 3.14159265358979323846
    cdef double DEG_TO_RAD = PI/180.0
    lat0 = lat0*DEG_TO_RAD
    lon0 = lon0*DEG_TO_RAD
    az0 = az0*DEG_TO_RAD
    lat1 = lat1*DEG_TO_RAD
    lon1 = lon1*DEG_TO_RAD
    az1 = az1*DEG_TO_RAD

    cdef double dlon, dlat, avlat, avaz, daz
    dlon = lon1-lon0
    dlat = lat1-lat0
    avlat = .5*(lat1 + lat0)
    avaz = .5*(az1 + az0)
    daz = az1 - az0

    #not sure what significance of these angles are yet, but better to isolate:
    cdef double g0, g1, g2, g3, g4, g5, fctr1   #note: fctr1 = tan(.5*delta_d)
    g0 = atan(sin(.5*dlat)/cos(avlat)/tan(.5*dlon))
    g1 = atan(cos(.5*dlat)/sin(avlat)/tan(.5*dlon))
    fctr1 = tan(.5*dlat)*sin(g1)/sin(g0)
    g2 = atan(fctr1*sin(PI- avaz - g0)/sin(PI - .5*daz - g1))
    g3 = atan(fctr1*cos(PI- avaz - g0)/cos(PI - .5*daz - g1))
    g4 =       atan(sin(.5*(g2 + g3 - PI/2.0 + lat0))/sin(.5*(g2 + g3 + PI/2.0 - lat0))/tan(.5*az0))
    g5 =       atan(cos(.5*(g2 + g3 - PI/2.0 + lat0))/cos(.5*(g2 + g3 + PI/2.0 - lat0))/tan(.5*az0))


    cdef double lat, lon, iangle, theta2, mu0, deltad, dist0, dist1
    lat = -2.0*atan(tan(.5*(g2 + g3 - PI/2.0 + lat0))*sin(g5)/sin(g4)) + PI/2.0
    lon = g4 + g5 + lon0

    deltad = 2.0*atan(fctr1)
    theta2 = 2.0*PI - az1 - (g0 + g1)
    mu0 = az0 - (g1-g0)
    iangle = acos(-cos(mu0)*cos(theta2) + sin(mu0)*sin(theta2)*cos(deltad)) #intersection angle
    dist0 = fabs(g2+g3)
    dist1 = fabs(g2-g3)

    cdef double radius = 6370.0
    lat = lat * 180.0/PI
    lon = lon * 180.0/PI
    iangle = iangle * 180.0/PI
    dist0 = dist0*radius
    dist1 = dist1*radius



    if lat > 90.0:  #not sure why this works (Oct 24, 2010)
        lat = 180.0-lat
        lon = lon - 180.0


    if lon > 180.0:
        lon = lon - 360.0

    if lon < -180.0:
        lon = lon + 360.0

    cdef gcSolution s1
    s1.lat = lat
    s1.lon = lon
    s1.dist0 = dist0
    s1.dist1 = dist1

    cdef gcSolution s2
    s2.lat = -1.0*lat
    s2.lon = lon + 180.0
    s2.dist0 =  PI*radius-dist0
    s2.dist1 = PI*radius-dist1

    cdef gcSolutionPair p
    p.iangle = iangle
    p.s1 = s1
    p.s2 = s2

    return p



#----------------------------------------------------------------
#helper functions to triangulation.MultiTriang:

def get_projected_time_range(double t_arrive, double alpha,
                             double V_TH, double distP, double distN,double max_prop_distance):
    """
    max_prop_distance: max range of sensor, in km
    """
    cdef double startN, startP, endN, endP
    cdef double MAX_PROP_TIME = max_prop_distance/3e5  #[seconds] travel time to farthest discharge

    startN = t_arrive - (1.0+alpha)*distN/V_TH
    startP = t_arrive - (1.0+alpha)*distP/V_TH

    if alpha >= 1.0:    #can't have discharge after arrival time!
        alpha = 1.0

    endN = t_arrive - (1.0-alpha)*distN/V_TH
    endP = t_arrive - (1.0-alpha)*distP/V_TH

    cdef double start, end
    start = double_min(startN,startP)
    end = double_max(endN,endP)

    if start-t_arrive < -MAX_PROP_TIME:
        start = t_arrive - MAX_PROP_TIME

    return (start,end)



def get_ATD_diff_from_gcIntersection(double lat0,double lon0,double az0, double t0,
                                     double lat1,double lon1,double az1,double t1,
                                     double V, double dq, double min_ref_distance):
    """
    Used in triangulation.MultiTriang.
    """
    cdef double PI = 3.14159265358979323846
    cdef gcSolutionPair p = _gcIntersection(lat0,lon0,az0,lat1,lon1,az1)

    #differential solutions:
    cdef gcSolutionPair p_q0 = _gcIntersection(lat0,lon0,az0+dq,lat1,lon1,az1)
    cdef gcSolutionPair p_q1 = _gcIntersection(lat0,lon0,az0,lat1,lon1,az1+dq)

    cdef double siniangle = sin(p.iangle*PI/180.0)

    cdef double tdiff1, tdiff2
    tdiff1 = fabs((t1 - t0) - (p.s1.dist1-p.s1.dist0)*1e3/V)
    tdiff2 = fabs((t1 - t0) - (p.s2.dist1-p.s2.dist0)*1e3/V)

    cdef int choice = 1

    #first set based on min tdiff:
    if tdiff2 < tdiff1:
        choice = 2

    #then reset depending on distances:
    if p.s1.dist0 > min_ref_distance:  #will be thrown out if used, might as well try other one
        choice = 2

    if p.s2.dist0 > min_ref_distance:  #will be thrown out if used, might as well try other one
        choice = 1

    cdef double mintdiff, latS,lonS,dist0,dist1, ATDc , ATDc_0, ATDc_1  #solution lat,lon, with distances and calculated ATD
    if choice == 1:
        mintdiff = tdiff1
        ATDc =   (   p.s1.dist1-   p.s1.dist0)*1e3/V
        ATDc_0 = (p_q0.s1.dist1-p_q0.s1.dist0)*1e3/V
        ATDc_1 = (p_q1.s1.dist1-p_q1.s1.dist0)*1e3/V
        latS = p.s1.lat
        lonS = p.s1.lon
        dist0 = p.s1.dist0
        dist1 = p.s1.dist1
    else:
        mintdiff = tdiff2
        ATDc =   (   p.s2.dist1-   p.s2.dist0)*1e3/V
        ATDc_0 = (p_q0.s2.dist1-p_q0.s2.dist0)*1e3/V
        ATDc_1 = (p_q1.s2.dist1-p_q1.s2.dist0)*1e3/V
        latS = p.s2.lat
        lonS = p.s2.lon
        dist0 = p.s2.dist0
        dist1 = p.s2.dist1

    return (mintdiff,siniangle,ATDc,ATDc_0,ATDc_1,latS,lonS,dist0,dist1)



#--------------------------------------------
#repeated functions form sig_proc
#--------------------------------------------
@cython.wraparound(False)
@cython.boundscheck(False)
def returnPoly(double x, np.ndarray[DTYPE_t,ndim=1] a not None):
    """
    Given x-values x, and polynomial a, return polynomial values
    a assumed in format y = a[0] + a[1]*x + a[2]*x^2 + a[3]*x^3 + ...
    x a scalar
    """
    cdef Py_ssize_t i
    cdef int n = a.shape[0]

    cdef double y = 0.0

    for i from 0 <= i < n:
        y = y + a[i]*pow(x,<double> i)

    return y


@cython.wraparound(False)
@cython.boundscheck(False)
def returnTaylor(double x, double x0, np.ndarray[DTYPE_t,ndim=1] a not None):
    """
    Given x-values x, center value x0, and polynomial a, return polynomial values
    a assumed in format y = a[0] + a[1]*(x-x0) + a[2]*(x-x0)^2 + a[3]*(x-x0)^3 + ...
    """
    cdef Py_ssize_t i
    cdef int n = a.shape[0]

    cdef double y = 0.0

    for i from 0 <= i < n:
        y = y + a[i]*pow(x-x0,<double> i)

    return y

def atten_norm_fctr(double p, double A, double C, double d0, double d):
    """
    I_peak = (SS)*atten_norm_fctr
    """
    cdef double I = 100.0
    cdef double R0 = 6370.0

    #old:
##    return C*sqrt(sin(d/R0)/(d/R0))*pow(d/I,p/2.0)*exp((d-I)/A)

    #new:
    if d < d0:
        return C*pow(d/I,p)

    if d >= d0:
        return C*pow(d0/I,p-0.5)*sqrt(d/I)*exp((d-d0)/A)*sqrt(sin(d/R0)/sin(d0/R0)/(d/d0))


#------------------------------------------------------
# Scripts to filter geo-location data set
# Use > 3 sensor data as reference, require 3-sensor data to be within a certain time/dist tolerance

cdef double _dist_approx(double lat0,double lon0,double lat1,double lon1):
    """
    Write helper function to calculate approximate distance.  Needs to be very fast.
    """
    cdef double D2R = 3.14159265358979323846/180.0

    return 6370.0*sqrt(pow((lat1-lat0)*D2R,2.0)+2.0*cos(lat0*D2R)*cos(lat1*D2R)*(1-cos((lon1-lon0)*D2R)))

def dist_approx(double lat0,double lon0,double lat1,double lon1):
    """ Make readable by Python for testing """
    return _dist_approx(lat0,lon0,lat1,lon1)


def cluster_geo_loc_solutions(np.ndarray[DTYPE_t,ndim=1] lat not None,\
                              np.ndarray[DTYPE_t,ndim=1] lon not None,\
                              np.ndarray[DTYPE_t,ndim=1] t not None,\
                              np.ndarray[DTYPE_t,ndim=1] latR not None,\
                              np.ndarray[DTYPE_t,ndim=1] lonR not None,\
                              np.ndarray[DTYPE_t,ndim=1] tR not None,\
                              double dTb, double dTf, double dD, int auto):
    """
    Use reference dataset latR,lonR,tR to cluster dataset lat, lon, t
    Using time tolerance dT, distance tolerance dD.  If auto is 1, assume reference and test datasets are the same (correlate to self).
    """
    cdef Py_ssize_t i, j, jmin, jmax
    cdef int n = t.shape[0]
    cdef int nR = tR.shape[0]

    cdef np.ndarray[DTYPEi_t, ndim=1] keepIndices = np.zeros(n, dtype=DTYPEi)

    jmin = 0
    jmax = 0

    for i from 0 <= i < n:
        if jmin == nR - 2:
            break

        while (jmin < nR-1) & (t[i]-tR[jmin] > dTb):  #cython appears to evaluate BOTH, so just truncate at one before the end
            jmin = jmin + 1

        while (jmax < nR-1) & (tR[jmax]-t[i] < dTf):    #cython appears to evaluate BOTH, so just truncate at one before the end
            jmax = jmax + 1

        for j from jmin <= j < jmax:
            if _dist_approx(lat[i],lon[i],latR[j],lonR[j]) < dD:
                if auto==1:
                    if i!=j:
                        keepIndices[i] = 1
                        break
                else:
                    keepIndices[i] = 1
                    break

    return keepIndices

#======================================

#match sets helper


@cython.wraparound(False)
@cython.boundscheck(False)
def match_sets_helper(np.ndarray[DTYPE_t,ndim=1] t not None,\
                      np.ndarray[DTYPE_t,ndim=1] lat not None,\
                      np.ndarray[DTYPE_t,ndim=1] lon not None,\
                      np.ndarray[DTYPE_t,ndim=1] tR not None,\
                      np.ndarray[DTYPE_t,ndim=1] latR not None,\
                      np.ndarray[DTYPE_t,ndim=1] lonR not None,\
                      double time_tol, double dist_tol, int one_to_one):
    """
    Use reference dataset latR,lonR,tR to match to dataset lat, lon, t
    Using time tolerance time_tol, distance tolerance dist_tol.  If one_to_one is 1, consumed matched events
    Note: unlike Python version don't need to match time first--comes out naturally with jmin, jmax
    """
    cdef Py_ssize_t i, j, jmin, jmax, idist, i_min_dist, i_min_dct, index
    cdef int n = t.shape[0]
    cdef int nR = tR.shape[0]

    cdef np.ndarray[DTYPEi_t, ndim=1] matchIndices = np.zeros(n, dtype=DTYPEi)

    cdef np.ndarray[DTYPE_t, ndim=1] dist_errors = np.ones(n, dtype=DTYPE)
    cdef np.ndarray[DTYPE_t, ndim=1] az_errors = np.zeros(n, dtype=DTYPE)
    cdef np.ndarray[DTYPE_t, ndim=1] time_errors = np.ones(n, dtype=DTYPE)  #default to time_tol if out of range

    cdef np.ndarray[DTYPEi_t, ndim=1] otherMatchIndices = np.zeros(nR, dtype=DTYPEi)

    cdef double C = 299792.4580 #km/s
    jmin = 0
    jmax = 0

    cdef azdist azDist

    if one_to_one==0:
        #still weight by time difference, but only add 10km/s penalty:
        C = 10.0    #km/s


    cdef double time_diff, min_dist, min_dct, dist, dct

    for i from 0 <= i < n:
        if jmin == nR - 1:  #ran of out indices to match to
            break

        while (jmin < nR) & (t[i]-tR[jmin] > time_tol):
            jmin = jmin + 1

        while (jmax < nR) & (tR[jmax]-t[i] < time_tol):
            jmax = jmax + 1

        #default to dist_tol time_tol in case out of range
        dist_errors[i] = dist_tol
        time_errors[i] = time_tol

        min_dist = 1e10
        min_dct = 1e10
        idist = -1
        for j from jmin <= j < jmax:
            idist += 1
            time_diff = t[i] - tR[j]
            if (otherMatchIndices[j]==0) | (one_to_one==0):
                dist = _dist_approx(lat[i],lon[i],latR[j],lonR[j])
                if dist < min_dist:
                    min_dist = dist
                    i_min_dist = idist
                if dist < dist_tol:
                    dct = dist + C*fabs(time_diff)  #add penalty for time difference
                    if dct < min_dct:
                        min_dct = dct
                        i_min_dct = idist

        if min_dist < dist_tol:
            index = i_min_dct
            j = jmin + index
            otherMatchIndices[j] = 1
            matchIndices[i] = 1

            azDist = _azDist(latR[j],lonR[j],lat[i],lon[i])
            az_errors[i] = azDist.azimuth
            dist_errors[i] = azDist.distance
            time_errors[i] = t[i] - tR[j]

    return matchIndices, otherMatchIndices, az_errors, dist_errors, time_errors



#------------------------------

#Sun angle

cdef struct sun_pos:
    double theta0
    double delta
    double RA

cdef struct sun_angle:
    double h
    double az

cdef sun_pos _calc_sun_pos(double JD):
    """
    Give Julian day, calculate theta0, delta, RA of sun
    """

    cdef double PI = 3.141592653589793238462643383
    cdef double DEG_TO_RAD = PI/180.0
    cdef double RAD_TO_DEG = 180.0/PI

    cdef double T, M, L0, DL, L, eps, X, Y, Z, R, delta, RA, theta0

    #Number of Julian Centuries since 2000/01/01 at 12UT:
    T = (JD - 2451545.0)/36525.0

    #Solar Coordinates:
    #Mean anomaly:
    M = 357.52910 + 35999.05030*T - .0001559*T*T - 0.00000048*T*T*T    #[deg]
    #Mean longitude:
    L0 = 280.46645 + 36000.76983*T + 0.0003032*T*T   #[deg]
    DL = (1.914600 - 0.004817*T - 0.000014*T*T)*sin(DEG_TO_RAD*M) + (0.019993 - 0.000101*T)*sin(DEG_TO_RAD*2*M) + 0.000290*sin(DEG_TO_RAD*3*M)

    #True longitude:
    L = L0 + DL    #[deg]

    #Convert ecliptic longitude L to right ascension RA and declination delta:
    eps = 23.43999   #[deg] obliquity of ecliptic
    X = cos(DEG_TO_RAD*L)
    Y = cos(DEG_TO_RAD*eps)*sin(DEG_TO_RAD*L)
    Z = sin(DEG_TO_RAD*eps)*sin(DEG_TO_RAD*L)
    R = sqrt(1.0-Z*Z)

    delta = RAD_TO_DEG*atan2(Z,R)  #[deg] declination -- latitude position of sun --
    RA = 7.63943726841098*atan2(Y,X+R) #[hours] right ascension
    RA = RA*360.0/24.0  #[deg] right ascension

    #Compute Sidereal time at Greenwich (only depends on time)
    theta0 = 280.46061837 + 360.98564736629*(JD-2451545.0) + 0.000387933*T*T - T*T*T/38710000.0   #[deg]
    theta0 = fmod(theta0,360.0)

    cdef sun_pos SP
    SP.theta0 = theta0
    SP.delta = delta
    SP.RA = RA

    return SP

cdef sun_angle _calc_sun_angle(sun_pos SP,double lat, double lon):
    """
    Given sun_pos SP, lat, lon, calculate elevation, azimuth of sun
    """

    cdef double PI = 3.141592653589793238462643383
    cdef double DEG_TO_RAD = PI/180.0
    cdef double RAD_TO_DEG = 180.0/PI

    cdef double delta, theta, tau, beta

    delta = SP.delta*DEG_TO_RAD   #[rad]
    theta = (SP.theta0 + lon)*DEG_TO_RAD   #rad
    tau = theta - SP.RA*DEG_TO_RAD #rad
    beta = lat*DEG_TO_RAD    #rad

    cdef sun_angle SA
    SA.h =   asin(sin(beta)*sin(delta) + cos(beta)*cos(delta)*cos(tau))*RAD_TO_DEG   #deg
    SA.az = atan2(-sin(tau),(cos(beta)*tan(delta) - sin(beta)*cos(tau)))*RAD_TO_DEG #deg

    return SA


def sunAngle(double JD, double lat, double lon):
    """
    calculate sun angle (callable form python)
    """
    cdef sun_pos SP  = _calc_sun_pos(JD)
    cdef sun_angle SA = _calc_sun_angle(SP,lat,lon)
    return SA.h, SA.az

@cython.wraparound(False)
@cython.boundscheck(False)
def sunAngleVec(double JD,\
                np.ndarray[DTYPE_t,ndim=1] lat not None,\
                np.ndarray[DTYPE_t,ndim=1] lon not None):
    """
    Calculate sun angle for multiple lat/lon pairs
    """
    cdef Py_ssize_t i
    cdef int n = lat.shape[0]

    cdef np.ndarray[DTYPE_t, ndim=1] h = np.zeros(n, dtype=DTYPE)
    cdef np.ndarray[DTYPE_t, ndim=1] az = np.zeros(n, dtype=DTYPE)

    cdef sun_pos SP  = _calc_sun_pos(JD)
    cdef sun_angle SA

    for i from 0 <= i < n:
        SA = _calc_sun_angle(SP,lat[i],lon[i])
        h[i] = SA.h
        az[i] = SA.az

    return h, az

def calcPercentDay(double dist, double bearing, double lat, double lon, double ALT, double JD):
    """
    Given distance, bearing from lat, lon, ionophsere altitude ALT, and Julian Day JD,
    calculate percent daytime (all scalar)
    """

    cdef constants co = _getConstants()
    cdef double R0 = 6370.0

    cdef int NPTS = 5
    if dist > 50.0:
        NPTS = 10
    if dist > 100.0:
        NPTS = 30
    if dist > 1000.0:
        NPTS = 100

    cdef double DD = dist/float(NPTS)   #km increments

    cdef sun_pos SP  = _calc_sun_pos(JD)
    cdef sun_angle SA
    cdef double h_corr  #corrected elevation for ionospheric altitude
    cdef int tot_sun = 0

    cdef int i
    cdef latlon coord
    cdef double this_dist = 0.0
    for i from 0 <= i < NPTS:
        coord = _estPosSphere(lat,lon,this_dist,bearing)
        SA = _calc_sun_angle(SP,coord.lat,coord.lon)
        h_corr = SA.h*co.D2R + acos(R0/(R0+ALT))

        if h_corr > 0:
            tot_sun = tot_sun + 1

        if i == 0:
            dn_first = tot_sun

        this_dist = this_dist + DD

    percentDay = float(tot_sun)/float(NPTS)

    return (percentDay,dn_first)


#---------------------------------------------------------------------------



def fit_circle(double x1,double y1,double x2,double y2,double x3,double y3):
    """
    syntax: (x0,y0,a,phi1,phi2,phi3) = fit_circle(x1,y1,x2,y2,x3,y3)
    Given three points, fit a circle
    Find radius and phase of three points
    """

    cdef double c12, c13
    c12 = (y1-y2)/(x1-x2)
    c13 = (y1-y3)/(x1-x3)

    cdef double d12, d13
    d12 = .5*(y1*y1 - y2*y2)/(x1-x2)
    d13 = .5*(y1*y1 - y3*y3)/(x1-x3)

    cdef double e12, e13
    e12 = .5*(x1*x1 - x2*x2)/(x1-x2)
    e13 = .5*(x1*x1 - x3*x3)/(x1-x3)

    cdef double x0, y0, a
    y0 = (d12 - d13 + e12 - e13)/(c12 - c13)
    x0 = -y0*c12 + d12 + e12
    a = sqrt((x1-x0)*(x1-x0) + (y1-y0)*(y1-y0))

    cdef double phi1, phi2, phi3
    phi1 = atan2((y1-y0)/a,(x1-x0)/a)
    phi2 = atan2((y2-y0)/a,(x2-x0)/a)
    phi3 = atan2((y3-y0)/a,(x3-x0)/a)

    cdef double dphi = asin(sin(phi3-phi1))

    return x0,y0,a,phi1,phi2,phi3,dphi
