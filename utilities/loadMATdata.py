import numpy as np
from struct import pack, unpack
import os

# Constants
types = {"float64": [0,'d'], "float32": [10,'f'], "int32": [20,'i'], "int16": [30,'h'], "uint16": [40,'H'], "uint8": [50,'B']}

class loadMATdata:
    """
    Newer class.  Use this instead of mat4LoadVar for newer code

    """

    def __init__(self,filename=None,uintToString = True,byteOrder = '<'):
        self.filename = filename
        self.uintToString = uintToString    #if True, convert uint8 vector to string (MOPT==50)
        if filename is not None:
            assert os.path.isfile(self.filename), '%s does not exist' % self.filename
        self.byteOrder = byteOrder
        self.varnames = None
        self.sizes = None
        self.MOPTs = None
        self.imagf = None

    def retrieve_var_names(self):
        if self.varnames is not None:   #already generated
            return
        self.fid = open(self.filename,'rb')
        self.varnames = []
        self.sizes = []
        self.MOPTs = []
        self.imagf = []
        while len(self.fid.read(1))>0:
            self.fid.seek(-1,1)
            (MOPT,mrows,ncols,varname,imagf) = self.read_var_header()
            self.varnames.append(varname)
            self.sizes.append(mrows*ncols)
            self.MOPTs.append(MOPT)
            self.imagf.append(imagf)
            self.skip_var(MOPT,mrows,ncols,imagf)
        self.fid.close()

    def get_var_names(self,return_imag=False):
        self.retrieve_var_names()
        if return_imag:
            return self.varnames,self.sizes,self.MOPTs,self.imagf
        else:
            return self.varnames,self.sizes,self.MOPTs

    def get_var_size(self,varname):
        self.retrieve_var_names()
        if varname not in self.varnames:
            return None
        return self.sizes[self.varnames.index(varname)]

    def get_var_MOPT(self,varname):
        self.retrieve_var_names()
        if varname not in self.varnames:
            return None
        return self.MOPTs[self.varnames.index(varname)]


    def loadData(self,varnames,sizes,offsets):
        if not isinstance(varnames,list):
            varnames = [varnames]
        if not isinstance(sizes,list):
            sizes = [sizes]
        if not isinstance(offsets,list):
            offsets = [offsets]

        outStruct = {}
        self.fid = open(self.filename,'rb')
        while len(self.fid.read(1))>0:
            self.fid.seek(-1,1)
            (MOPT,mrows,ncols,varname,imagf) = self.read_var_header()
            if varname in varnames:
                index = varnames.index(varname)
                outStruct[varname]= self.read_var(MOPT,mrows,ncols,imagf,sizes[index],offsets[index])
            else:
                self.skip_var(MOPT,mrows,ncols,imagf)

        self.fid.close()
        return outStruct


    def loadAllData(self,exclude_list = []):
        """
        loads all data, except variable names in exclude_list
        """
        outStruct = {}
        self.fid = open(self.filename,'rb')
        while len(self.fid.read(1))>0:
            self.fid.seek(-1,1)
            (MOPT,mrows,ncols,varname,imagf) = self.read_var_header()
            if varname in exclude_list:
                self.skip_var(MOPT,mrows,ncols,imagf)
            else:
                outStruct[varname]= self.read_var(MOPT,mrows,ncols,imagf,-1,0)

        self.fid.close()
        return outStruct


    def read_var_header(self):
        #MOPT: <architecture><0><precision><0 (full) or 1 (text) matrix>
        (MOPT,mrows,ncols,imagf,namelen) = unpack('<iiiii',self.fid.read(4*5))
        varname = self.fid.read(namelen)[:-1]
        return (MOPT,mrows,ncols,varname,imagf)


    def get_np_type_format(self,MOPT):
        if MOPT==0:
            precision = np.float64
            bytesPerEntry = 8
        elif MOPT==10:
            precision = np.float32
            bytesPerEntry = 4
        elif MOPT==20:
            precision = np.int32;
            bytesPerEntry = 4
        elif MOPT==30:
            precision = np.int16;
            bytesPerEntry = 2
        elif MOPT==40:
            precision  = np.uint16;
            bytesPerEntry = 2
        elif MOPT==50:
            precision = np.uint8;
            bytesPerEntry = 1
        elif MOPT==1:   #matrix of characters
            precision = np.float64;
            bytesPerEntry = 8
        elif MOPT==11:   #matrix of characters
            precision = np.float32;
            bytesPerEntry = 4
        elif MOPT==51:   # Matrix of characters
        	precision = np.uint8;
        	bytesPerEntry = 1
        else:
            raise TypeError('unrecognized format: %d' % MOPT)
        return (precision, bytesPerEntry)


    def get_unpack_type_format(self,MOPT):
        if MOPT==0:
            precision = 'd'
            bytes = 8
        elif MOPT==10:
            precision = 'f'
            bytes = 4
        elif MOPT==20:
            precision = 'i'
            bytes = 4
        elif MOPT==30:
            precision = 'h'
            bytes = 2
        elif MOPT==40:
            precision  = 'H'
            bytes = 2
        elif MOPT==50:
            precision = 'B'
            bytes = 1
        elif MOPT==1:   #matrix of characters
            raise TypeError('MOPT = 1 not supported')
        else:
            raise TypeError('unrecognized format: %d' % MOPT)
        return (precision, bytes)

    def read_var(self,MOPT,mrows,ncols,imagf,size=-1, offset = 0):
        """
        size: number of elements from data field to read in
        Set to -1 to read in whole variable
        """

        ORDER = 'FORTRAN'   #for MATLAB compatibility

        size = int(size)
        offset = int(offset)

        origSize = mrows*ncols
        if origSize == 0:
            return None

        if origSize == 1:    #scalar -- read value
            (precision,bytes) = self.get_unpack_type_format(MOPT)
            value = unpack(self.byteOrder + precision,self.fid.read(bytes))[0]
            if imagf==1:
                value +=  unpack(self.byteOrder + precision,self.fid.read(bytes))[0]*1.0j
            if MOPT==50:
                return chr(value)
            else:
                return value
        else:
            (precision, bytesPerEntry) = self.get_np_type_format(MOPT)

        #2-d matrix: read in whole thing
        if (mrows>1) and (ncols>1):
            value = np.reshape(np.fromfile(self.fid,precision,mrows*ncols),(mrows,ncols),'FORTRAN').newbyteorder(self.byteOrder)
            if imagf == 1:
                value = value + np.reshape(np.fromfile(self.fid,precision,mrows*ncols),(mrows,ncols),'FORTRAN').newbyteorder(self.byteOrder)*1.0j
            return value

        #1-d vector:
        if offset > origSize:
            fctr = 1
            if imagf==1:
                fctr = 2
            self.fid.seek(origSize*bytesPerEntry*fctr,1)   #advance to next variable header
            return np.array([],dtype=precision) #return empty list

        if (size<0) or (origSize < offset + size):  #read until the end
            size = origSize - offset



        self.fid.seek(offset*bytesPerEntry,1)
        a = np.fromfile(self.fid,precision,size).newbyteorder(self.byteOrder)
        self.fid.seek((origSize - (offset + size))*bytesPerEntry,1)

        if imagf==1:
            self.fid.seek(offset*bytesPerEntry,1)
            a = a + np.fromfile(self.fid,precision,size).newbyteorder(self.byteOrder)*1.0j
            self.fid.seek((origSize - (offset + size))*bytesPerEntry,1)

        if MOPT in [1,11]:
            #cast to character:
            a = np.array(a,np.uint8)


        if (MOPT==50) and self.uintToString:
            a = a.tostring()



        return a

    def skip_var(self,MOPT,mrows,ncols,imagf):
        (precision, bytesPerEntry) = self.get_np_type_format(MOPT)
        fctr = 1
        if imagf==1:
            fctr=2
        self.fid.seek(mrows*ncols*bytesPerEntry*fctr,1)


if __name__ == '__main__':
    filename = 'testmat.mat'
    lm = loadMATdata(filename)
    print lm.get_var_names(True)

    s = lm.loadAllData()
    print s['string']
    print s['mat_complex']

    s = lm.loadData(['a_float','vec_int','vec_float','vec_complex','mat_complex'],
                [-1,2,2,2,-1],[0,1,1,1,1])

    print s['a_float']
    print s['vec_int']
    print s['vec_float']
    print s['vec_complex']
    print s['mat_complex']

