/* 
nbmodule.cpp

narrowband
10-29-05 Kiran Madhav
06-13-06 JCC
10-28-09 Nick LaVassar (NFL) : Converted to narrowband python module
*/

#include "nbmodule.h"

//extern int fshandles[NUM_CF_SLOTS]; //commented by NFL

NB_EXPERIMENT* CreateExperimentNB(double* NBFilterTaps, int FilterLen, int transmitterFreq, int sampleFrequency, double calibrationFactor, int is_MSK, int do_low_res) 
{
	
  	
  	struct NB_EXPERIMENT* NBexp = (struct NB_EXPERIMENT*) malloc (sizeof(struct NB_EXPERIMENT));
  	//if(NBexp == NULL) b_log("NBexp equals NULL.\n", 0); //assert(NBexp != NULL);

	// set filter length
  	NBexp->Filter_Length = FilterLen;
  
  	// set filter taps method 1: copy taps
  	//NBexp->FilterTaps = malloc(sizeof(float)*(NBexp->Filter_Length));
	NBexp->FilterTaps = new double[FilterLen];
  	//if(NBexp->FilterTaps == NULL) printf("NBexp->FilterTaps equals NULL.\n", 0);//assert(NBexp->FilterTaps != NULL); 
   	memcpy (NBexp->FilterTaps, NBFilterTaps, FilterLen*sizeof(double));
  	
  	// set filter taps method 2: copy pointer, less mem needed
  	//NBexp->FilterTaps = NBFilterTaps;
	//NBexp->DemodDec = demodDec;
	//NBexp->DemodBufLen = demodBufLen;
	NBexp->is_MSK = is_MSK;
	NBexp->do_low_res = do_low_res;
	NBexp->sampleFrequency = sampleFrequency;
	NBexp->calibrationFactor = calibrationFactor;
	//NBexp->FilteredLen = filteredLen;
	//NBexp->OutputLen = outputLen;
	//NBexp->DemodTimeInt = demodTimeInt;


	NBexp->transmitterFreq = transmitterFreq;
	//DEMOD_TIME_INTERVAL: 10 ms resolution for 100kHz.
	
	//FillMixer(&(NBexp->theMixer[c]),transmitterFreq[c],DEMOD_TIME_INTERVAL,MIXER_MAX_LENGTH,c);
	NBexp->theMixer = new MIXER(transmitterFreq, DEMOD_TIME_INTERVAL, DEMOD_MIXER_LENGTHS, 0, 0); 
	//last parameter 0 means filter is a pointer to FilterTaps

	// Changed to copy pointer instead of full filter array
	//FillFIR(&(NBexp->realFIR[c]),NBexp->FilterTaps, NBexp->Filter_Length, DEMOD_DECIMATE_FACTOR, 1);
	NBexp->realFIR = new FIR(NBexp->FilterTaps, FilterLen, DEMOD_DECIMATE_FACTOR);

	// Changed to copy pointer instead of full filter array
	//FillFIR(&(NBexp->imagFIR[c]),NBexp->FilterTaps, NBexp->Filter_Length, DEMOD_DECIMATE_FACTOR, 1);
	NBexp->imagFIR = new FIR(NBexp->FilterTaps, FilterLen, DEMOD_DECIMATE_FACTOR);
	
	
	//FillMSK(&(NBexp->theMSK[c]));
	
	if (is_MSK) 
		NBexp->theMSK = new MSK();
	else
		NBexp->theMSK = NULL;

	//FillAmp(&(NBexp->theAmp[c]));  
	NBexp->theAmp = new AMP();  

	//FillPhase(&(NBexp->thePhase[c])); 
	NBexp->thePhase = new PHASE();
	
	if (do_low_res) {
		NBexp->theAmp_low = new AMP();
		NBexp->thePhase_low = new PHASE();
	} else {
		NBexp->theAmp_low = NULL;
		NBexp->thePhase_low = NULL;
	}


	

	//printf("%d\n",NBexp->theMixer[c].m_bCreated);
	
	// allocate memory to storage buffers
	NBexp->RealMixedDown = new double[DEMOD_BUFFER_LENGTH];
	NBexp->ImagMixedDown = new double[DEMOD_BUFFER_LENGTH];
	NBexp->RealFiltered = new double[FILTERED_LENGTH+10];
	NBexp->ImagFiltered = new double[FILTERED_LENGTH+10];
	   
	if (is_MSK) {
		NBexp->TrellisTXT = new double[FILTERED_LENGTH+20];
		NBexp->TrellisRCV = new double[FILTERED_LENGTH+20];
	}else {
		NBexp->TrellisTXT = NULL;
		NBexp->TrellisRCV = NULL;
	}

	// one sec of phase data
	NBexp->PhaseData = new float[FILTERED_LENGTH+10];
	// one sec of amplitude data
	NBexp->AmplitudeData=  new float[FILTERED_LENGTH+10];
    
    
  	return NBexp;
}

PyObject* processNarrowBand(NB_EXPERIMENT *NBexp,  
				double* rawData, int data_length,
				double* RealMixedDown, double *ImagMixedDown,
			  	double* RealFiltered, double* ImagFiltered, 
			  	double* TrellisTXT, double* TrellisRCV, 
			  	float* PhaseData, float* AmplitudeData)
{
  	//int i, j, c;		//indexes data samples in 1 sec of data. (10000 samples)
/*	
	npy_intp ddims[2] = {100000,1};
	PyArrayObject *dat2 = PyArray_SimpleNewFromData((int)2,(npy_intp *)ddims,PyArray_FLOAT32,(float*)rawData);
	return Py_BuildValue("O", dat2);
*/
  	int ScaleFactor;
  	//int index;
       
  	int lengthRealFiltered;  
  	int lengthImagFiltered;
  	int lengthTXT;
 
  	int lengthAmp;
  	int lengthPhase;
	//int i;
	npy_intp adims[2] = {0,1};	//specify number of columns below
	npy_intp pdims[2] = {0,1}; //specify number of columns below
	PyObject * amp;
	PyObject * amp_low;
	PyObject * phase;
  	PyObject * phase_low;
	
	//sampleFrequency = 1000
	ScaleFactor=1000/NBexp->sampleFrequency;
	
	//finalData->ampdata[c]=  malloc (DATA_CHANNELS*FINAL_OUTPUT_LENGTH*sizeof(float));
	
	//finalData->phasedata[c]= malloc (DATA_CHANNELS*FINAL_OUTPUT_LENGTH*sizeof(float));

	// Run mixer
	NBexp->theMixer->MixDown(RealMixedDown, ImagMixedDown, rawData, static_cast<unsigned int>(data_length));
	//SerOut("*");
	//for(int i = 0; i<data_length;i++){
	//	if(i<10)
	//		cout << RealMixedDown[i] << " " << ImagMixedDown[i] << "\n" << flush;
	//}
	// run filter on real part of data
	NBexp->realFIR->Filter(RealFiltered, &lengthRealFiltered, RealMixedDown, static_cast<unsigned int>(data_length));
	//SerOut("*");
	//for(int i = lengthRealFiltered-10; i<lengthRealFiltered;i++)
		//cout << ImagFiltered[i] << "\n" << flush;
	
	// run filter on imaginary part of data
	NBexp->imagFIR->Filter(ImagFiltered, &lengthImagFiltered, ImagMixedDown, static_cast<unsigned int>(data_length));
	//SerOut("*");
	//for(int i = lengthImagFiltered-10; i<lengthImagFiltered;i++)
	//	cout << RealFiltered[i] << " " << ImagFiltered[i] << "\n" << flush;

	if (NBexp->is_MSK) {
		// fit curve
		NBexp->theMSK->FitCurve(TrellisTXT, &lengthTXT, TrellisRCV, RealFiltered, ImagFiltered, lengthRealFiltered);
		//SerOut("*");
		//for(int i = 0; i<10;i++)
		//	cout << TrellisTXT[i] << " "<< TrellisRCV[i] <<"\n" << flush;
		// Calculate phase info
		NBexp->thePhase->GetMSKPhase(PhaseData, &lengthPhase, TrellisTXT, lengthTXT, RealFiltered, ImagFiltered, lengthRealFiltered, ScaleFactor );
		//SerOut("*");
		//for(int i = 0; i<10;i++)
		//	cout << PhaseData[i] << "\n" << flush;

	} else {
		NBexp->thePhase->GetCWPhase(PhaseData, &lengthPhase, RealFiltered, ImagFiltered, lengthRealFiltered, ScaleFactor );

	}
		 
	//SerOut("*");
	// Calculate amplitude
	NBexp->theAmp->GetAmp(AmplitudeData, &lengthAmp, RealFiltered, ImagFiltered,lengthRealFiltered, NBexp->sampleFrequency, NBexp->calibrationFactor);
	
	
	adims[0] = lengthAmp;
	amp = PyArray_SimpleNew((int)2,(npy_intp *)adims,PyArray_FLOAT32);
	void *amp_data = PyArray_DATA((PyArrayObject*)amp);
	memcpy(amp_data,AmplitudeData,PyArray_ITEMSIZE((PyArrayObject*) amp) * adims[0]);

	pdims[0] = lengthPhase;
	phase = PyArray_SimpleNew((int)2,(npy_intp *)pdims,PyArray_FLOAT32);
	void *phase_data = PyArray_DATA((PyArrayObject*)phase);
	memcpy(phase_data,PhaseData, PyArray_ITEMSIZE((PyArrayObject*) phase) * pdims[0]);
	
	if (NBexp->do_low_res) {
		if (NBexp->is_MSK) {
			
			// Calculate phase info
			NBexp->thePhase_low->GetMSKPhase(PhaseData, &lengthPhase, TrellisTXT, lengthTXT, RealFiltered, ImagFiltered, lengthRealFiltered, 1000 );
			//SerOut("*");
			
			
		} else {
			NBexp->thePhase_low->GetCWPhase(PhaseData, &lengthPhase, RealFiltered, ImagFiltered, lengthRealFiltered, 1000 );
			
		}
		NBexp->theAmp_low->GetAmp(AmplitudeData, &lengthAmp, RealFiltered, ImagFiltered,lengthRealFiltered, 1, NBexp->calibrationFactor);
		//cout << "Amp_low[" << 0 << "] = " << AmplitudeData[0] << endl;
		
		adims[0] = lengthAmp;
		amp_low = PyArray_SimpleNew((int)2,(npy_intp *)adims,PyArray_FLOAT32);
		void *amp_data_low = PyArray_DATA((PyArrayObject*)amp_low);
		memcpy(amp_data_low,AmplitudeData,PyArray_ITEMSIZE((PyArrayObject*) amp_low) * adims[0]);
		
		pdims[0] = lengthPhase;
		phase_low = PyArray_SimpleNew((int)2,(npy_intp *)pdims,PyArray_FLOAT32);
		void *phase_data_low = PyArray_DATA((PyArrayObject*)phase_low);
		memcpy(phase_data_low,PhaseData, PyArray_ITEMSIZE((PyArrayObject*) phase_low) * pdims[0]);
		
		return Py_BuildValue("NNNN",amp,phase,amp_low,phase_low);
	}
	
	return Py_BuildValue("NN",amp,phase);
	
	//return finalData;
}



 
// Destructors
void DestroyExperimentNB(NB_EXPERIMENT *NBexp) 
{
	//int i = 0;
 	//printf("Before Destroy Loop.\n");
  	if (NBexp != NULL)
    {
		//printf("Before Destroy Misxer[%d].\n",i);
		delete(NBexp->theMixer);
		
		//printf("Before Destroy realFIR[%d].\n",i);
		delete(NBexp->realFIR);
		
		//printf("Before Destroy imagFIR[%d].\n",i);
		delete(NBexp->imagFIR);
		
		//printf("Before Destroy theAmp[%d].\n",i);
		delete(NBexp->theAmp);
		if (NBexp->theAmp_low != NULL)
			delete(NBexp->theAmp_low);
		
		//printf("Before Destroy thePhase[%d].\n",i);
		delete(NBexp->thePhase);
		if (NBexp->thePhase_low != NULL)
			delete(NBexp->thePhase_low);
		
		//printf("Before Destroy theMSK[%d].\n",i);
		delete(NBexp->theMSK);

		//     printf("Before Free Filter.\n");
    	//if (NBexp->FilterTaps != NULL)
			//free(NBexp->FilterTaps);
 		
 		//printf("Before Free NBExp.\n");
	
		delete(NBexp->RealMixedDown);
		//printf("Before ImagMixedDown.\n");
		delete(NBexp->ImagMixedDown);
		//printf("Before RealFiltered.\n");
		delete(NBexp->RealFiltered);
		//printf("Before ImagFiltered.\n");
		delete(NBexp->ImagFiltered);
		//printf("Before TrellisTXT.\n");
		delete(NBexp->TrellisTXT);
		//printf("Before TrellisRCV.\n");
		delete(NBexp->TrellisRCV);
		//free(NBexp->PhaseData);  //Destruction of phase and amp data causes core dump in python, since a PyObject is wrapping the data after processing.
		//free(NBexp->AmplitudeData);

		//printf("Before Filter_Length.\n");
		//delete(&NBexp->Filter_Length);
		//printf("Before transmitterFreq.\n");
		//delete(&NBexp->transmitterFreq);
		//printf("Before sampleFrequency.\n");
		//delete(&NBexp->sampleFrequency);RKS: not allocated heap memory (stack variable)
		//printf("Before calibrationFactor.\n");
		//delete(&NBexp->calibrationFactor); RKS: not allocated heap memory (stack variable)

		delete(NBexp->PhaseData);
		delete(NBexp->AmplitudeData);
		delete(NBexp->FilterTaps);
		
			delete(NBexp);
		//printf("NBexp Destroyed!");
    }
	
}

void DestroyNBFilter(void *ptr){
	//printf("Destroying NBFilter Now!");
	NB_EXPERIMENT* NBexp;
	//fflush(stdin);
	NBexp = (NB_EXPERIMENT *)ptr;
	DestroyExperimentNB(NBexp);
	//printf("Destroyed NBFilter");
	//free(ptr);
}

PyObject *CreateNBFilter(PyObject *self, PyObject *args){
	PyObject *py_FilterTaps=NULL;	
	int FilterLen;
	int transmitterFreq, sampleFrequency;
	//unsigned int DemodDec, DemodBufLen, FilteredLen, OutputLen;
	PyArrayObject *FilterTaps;
	NB_EXPERIMENT* NBexp ;
	int is_MSK, do_low_res;
	double calibrationFactor;
	
	
	if (!PyArg_ParseTuple(args, "Oiiidii", &py_FilterTaps, &FilterLen, &transmitterFreq, &sampleFrequency, &calibrationFactor, &is_MSK, &do_low_res))
        	return NULL;
	
	FilterTaps = (PyArrayObject *) PyArray_FROM_OTF(py_FilterTaps, PyArray_DOUBLE, NPY_IN_ARRAY);
	
	//printf("DemondTimeInt = %f", DemodTimeInt);
	/*//Test input array.
	float* tapss = PyArray_DATA(FilterTaps);
	int i;
	printf("Loop");
	for(i=0;i<10;i++){
		printf("%f \n",tapss[i]*1e9);
	}
	*/

	NBexp = CreateExperimentNB((double*)PyArray_DATA(FilterTaps), FilterLen, transmitterFreq, sampleFrequency, calibrationFactor, is_MSK, do_low_res) ;
	
	Py_DECREF(FilterTaps);
	return PyCObject_FromVoidPtr( NBexp, DestroyNBFilter);
}

PyObject *ProcessNB(PyObject *self, PyObject *args){
	PyObject *py_NBexp=NULL, *py_rawBuffer=NULL;
	PyArrayObject *rawBuffer;
	NB_EXPERIMENT *NBexp;
	PyObject *data;
	int n; //length of raw data.
	
	if (!PyArg_ParseTuple(args, "OO", &py_NBexp, &py_rawBuffer))
        	return NULL;
	
	
	//return Py_BuildValue("i", pt->transmitterFreq);
	
	rawBuffer = (PyArrayObject *)PyArray_ContiguousFromObject(py_rawBuffer, PyArray_DOUBLE, 0, 3);
	if(rawBuffer == NULL) return NULL;
	// Compute Size of Array 
	if(rawBuffer->nd == 0)
		n = 1;
	else {
		n = 1;
		for(int i=0;i<rawBuffer->nd;i++) 
			n = n * rawBuffer->dimensions[i];
	} 

	//PyArrayObject *rawBuf = PyArray_GETCONTIGUOUS((PyArrayObject*)rawBuffer);
	
	/*//Test input array.
	double* rawBuf = (double *)PyArray_DATA(rawBuffer);
	printf("Loop");
	for(int i=0;i<3;i++){
		printf("%f \n",rawBuf[i]);
	}
	
	for(int i=(n-3); i<n;i++){
		printf("%f \n",rawBuf[i]);
	}
	//*/

	//NB_EXPERIMENT *flt = (NB_EXPERIMENT *)PyCObject_AsVoidPtr(NBexp);

	//return rawBuffer;
	
	NBexp = (NB_EXPERIMENT *)PyCObject_AsVoidPtr(py_NBexp);
	
	/*//Test taps:	
	cout << "Taps:\n";
	for(int i=0;i<10;i++){
		cout << NBexp->FilterTaps[i] << "\n";
	}
	//*/
	//cout << "Length input = " << n << endl;
	data = processNarrowBand(NBexp, (double *)PyArray_DATA(rawBuffer), n,
			NBexp->RealMixedDown, NBexp->ImagMixedDown, NBexp->RealFiltered, NBexp->ImagFiltered,
			NBexp->TrellisTXT, NBexp->TrellisRCV, NBexp->PhaseData, NBexp->AmplitudeData);
	
	Py_DECREF(rawBuffer);	//RKS

	return data;	
	//return PyArray_SimpleNewFromData(nd, dims, typenum, data);

}



PyObject *ProcessSPH(PyObject *self, PyObject *args){
	PyObject *py_rawBuffer=NULL;
	PyArrayObject *rawBuffer;
	NB_EXPERIMENT *NBexp;
	PyObject * amp;
	npy_intp adims[2] = {0,1};	//specify number of columns below
	int n; //length of raw data.
	int sampling_rate;
	unsigned int SPHERIC_DECIMATE;
	float* sphericData;
	double * raw_buffer;
	
	unsigned int i, j, numSamples, outputLength;
	
	if (!PyArg_ParseTuple(args, "iO", &sampling_rate, &py_rawBuffer))
        	return NULL;
	
	
	//return Py_BuildValue("i", pt->transmitterFreq);
	
	rawBuffer = (PyArrayObject *)PyArray_ContiguousFromObject(py_rawBuffer, PyArray_DOUBLE, 0, 3);
	if(rawBuffer == NULL) return NULL;
	// Compute Size of Array 
	if(rawBuffer->nd == 0)
		n = 1;
	else {
		n = 1;
		for(int i=0;i<rawBuffer->nd;i++) 
			n = n * rawBuffer->dimensions[i];
	} 

	raw_buffer = (double *) PyArray_DATA(rawBuffer);
	
	SPHERIC_DECIMATE = (DEMOD_BUFFER_LENGTH/sampling_rate);
	sphericData = new float[sampling_rate+10];

	/* New code: find the mean value, not the max */

    outputLength = 0;
	for (i = 0; i < (unsigned int) floor((double) n / (double)SPHERIC_DECIMATE); i++)
	{
      numSamples = 0;

	  double temp = (double)0;
	  for (j = 0; j < SPHERIC_DECIMATE; j++) 
	  {
		  if (raw_buffer[i*SPHERIC_DECIMATE+j] > 0)
			  temp += (double)raw_buffer[i*SPHERIC_DECIMATE+j];
		  else
			  temp -= (double)raw_buffer[i*SPHERIC_DECIMATE+j];

		  numSamples++;
	  } 

      // Be careful with the division below; if numSamples is not cast
	  // to float, we will get an integer divide
	  sphericData[i] = (float) (((double) temp)/((double) numSamples));
	  outputLength++;
	}
  

	adims[0] = outputLength;
	amp = PyArray_SimpleNew((int)2,(npy_intp *)adims,PyArray_FLOAT32);
	void *amp_data = PyArray_DATA((PyArrayObject*)amp);
	memcpy(amp_data,sphericData,PyArray_ITEMSIZE((PyArrayObject*) amp) * adims[0]);	
	
	delete(sphericData);

	Py_DECREF(rawBuffer);
	return Py_BuildValue("N",amp);	
	//return PyArray_SimpleNewFromData(nd, dims, typenum, data);

}

PyObject *ResetNBFilter(PyObject *self, PyObject *args){
	PyObject *py_NBexp=NULL;
	NB_EXPERIMENT *NBexp;
	
	if (!PyArg_ParseTuple(args, "O", &py_NBexp))		return NULL;

	NBexp = (NB_EXPERIMENT *)PyCObject_AsVoidPtr(py_NBexp);
	
	NBexp->theMixer->Reset();
	NBexp->realFIR->Reset();
	NBexp->imagFIR->Reset();
	if (NBexp->is_MSK)
		NBexp->theMSK->Reset();
	NBexp->theAmp->Reset();
	NBexp->thePhase->Reset();
	if (NBexp->do_low_res){
		NBexp->theAmp_low->Reset();
		NBexp->thePhase_low->Reset();
	}
	return Py_BuildValue("");
}
