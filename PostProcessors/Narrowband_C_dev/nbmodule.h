#ifndef _EXPERIMENT_H
#define _EXPERIMENT_H

#if defined(_WIN32)
	#include "C:/Anaconda2/include/Python.h"
	#include "C:/Anaconda2/Lib/site-packages/numpy/core/include/numpy/ndarrayobject.h"
#elif defined(__MACH__)
	//Using EPD v5.1.1 Pyton Package on OS X:
	#include "/Library/Frameworks/Python.framework/Versions/Current/Headers/Python.h"
	#include "/Library/Frameworks/Python.framework/Versions/Current/lib/python2.5/site-packages/numpy/core/include/numpy/ndarrayobject.h"
#else
  //#include "/usr/include/python2.5/Python.h"
  //#include "/usr/lib/python2.5/site-packages/numpy/core/include/numpy/ndarrayobject.h"
	#include <Python.h>
	//#include <numpy/ndarrayobject.h>
	#include "/usr/local/lib/python2.5/site-packages/numpy/core/include/numpy/ndarrayobject.h"
	
#endif



//#include <stdlib.h>
//#include <assert.h>
//#include <cstring>
//#include <stdio.h>
//#include <math.h>
#include <iostream>
using namespace std;
//#include "Globals.h" //commented by NFL

#include "MIXER.h"
#include "FIR.h"
#include "MSK.h"
#include "PHASE.h"
#include "AMP.h"
//#include "revfs10.h"
//#include "csl.h"



// -----------------CONSTANTS
//#define FINAL_OUTPUT_LENGTH 		50
//#define DEMOD_EXTRA_OUTPUT_LENGTH 	1010

// who knows what this value should be...have to test processing time on DSP
//#define DEMOD_TIME_INTERVAL      	(float)10e-6 //10 ms resolution for 100kHz.

#define DEMOD_TIME_INTERVAL	(double)1e-5
#define DEMOD_MIXER_LENGTHS  	25000
#define DEMOD_BUFFER_LENGTH  	100000 //buffers 1 sec. of 100 kHz data

#define DEMOD_DECIMATE_FACTOR 		100		//100kHz -> 1kHz   this happens in the FilterNB
#define FILTERED_LENGTH      		1000	//buffers 1 sec. of 1 kHz data
#define LOW_RES_DECIMATE  1000
//#define DEMOD_EXTRA_OUTPUT_LENGTH  1010

//#define MAX_FILTER_LENGTH         	10000  //max number of filter taps.
//#define MAX_FILENAME_LENGTH    		64


// Transmitters for Buoy!
#define NLK 24800
#define NAA 24000
#define NAU 40750
#define NPM 21400
#define NWC 19800
#define JJI 22200
#define NLM 25200


typedef struct NB_EXPERIMENT 
{
  	double* 	FilterTaps;
  	int 	Filter_Length;		//Number of Filter Taps to use
  	int 	transmitterFreq; 	//[Hz]
  	MIXER* 	theMixer;
  	FIR* 	realFIR;
  	FIR* 	imagFIR;
	MSK* 	theMSK;
  	AMP* 	theAmp;
  	PHASE* 	thePhase;
	AMP* 	theAmp_low;  //Low resolution
  	PHASE* 	thePhase_low;//Low resolution
  	

	//int DemodBufLen;
	int is_MSK;
	int do_low_res;
	double calibrationFactor;
	int sampleFrequency;
	//float* DemodTimeInt;

	// Storage buffers for filter.
	double* RealMixedDown;		// Holds real part of the mixed down data 
	double* ImagMixedDown;		// Holds imaginary part of mixed down data
 	double* RealFiltered;		// Holds mixed/filtered received data (real)
	double* ImagFiltered;		// Holds mixed/filtered received data (imag)
  	double* TrellisTXT;		// Holds generated trellis (wrapped)
  	double* TrellisRCV;		// Holds received trellis (wrapped)
	float* PhaseData;		// Holds phase data
  	float* AmplitudeData;		// Holds amplitude data

 } NB_EXPERIMENT;


// Function Declarations
NB_EXPERIMENT* CreateExperimentNB(double* NBFilterTaps, int FilterLen, int transmitterFreq, int sampleFrequency, double calibrationFactor, int is_MSK, int do_low_res);


//changed from void to PyObject to return final data
PyObject* processNarrowBand(		NB_EXPERIMENT *NBexp, 
							double* rawData, int data_length,
							double* RealMixedDown, 
							double *ImagMixedDown,
    						double* RealFiltered, 
    						double* ImagFiltered, 
    						double* TrellisTXT,
    						double* TrellisRCV, 
    						double* PhaseData,
    						double* AmplitudeData);


void DestroyExperimentNB(NB_EXPERIMENT *NBexp);

//Python calls

PyObject* CreateNBFilter(PyObject *self, PyObject *args);
PyObject* ProcessNB(PyObject *self, PyObject *args);
PyObject* ResetNBFilter(PyObject *self, PyObject *args);

PyObject* ProcessSPH(PyObject *self, PyObject *args);	//RKS


void DestroyNBFilter(void *ptr);

static PyMethodDef nbmoduleMethods[] = {
    {"CreateNBFilter", (PyCFunction)CreateNBFilter, 
    METH_VARARGS, 
    "Create a NB filter.\n"},
    {"ProcessNB", (PyCFunction)ProcessNB, 
    METH_VARARGS, 
    "Process latest data through filter.\n"},
    {"ProcessSPH", (PyCFunction)ProcessSPH, 
    METH_VARARGS, 
    "Process latest data through spheric channel.\n"},
    {"ResetNBFilter", (PyCFunction)ResetNBFilter, 
    METH_VARARGS, 
    "Reset a NB filter.\n"},
    {NULL,NULL,0,NULL} /* Sentinel -- don't change*/
};

PyMODINIT_FUNC
initnbmodule(void) {
    (void) Py_InitModule("nbmodule", nbmoduleMethods);
    import_array();
}

#endif

