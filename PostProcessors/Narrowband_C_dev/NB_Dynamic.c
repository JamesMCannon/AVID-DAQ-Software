// This is Kiran's version of test code from Spiro's TIPER Stuff
// 11/3/05

#include "NB_dynamic.h"

// define elsewhere
//#include "taps.h"
extern float FilterTapsNB[];

//extern int fshandles[NUM_CF_SLOTS];
 
#define	DECIMATED_LENGTH 		1000		//1 second of 1kHz data
//#define TWO_PI  				(double)6.28318530717959
#define MIN_AMP_INDEX    		FINAL_OUTPUT_LENGTH*SECS_PER_FILE
#define MAX_AMP_INDEX    		FINAL_OUTPUT_LENGTH*SECS_PER_FILE+1


//****************** 11-29-05 testing one file of data, with scaling!)
int OneFileAcquisition(NB_EXPERIMENT* NBexp, int RDfileptr, short* finalAmpData[], short* finalPhaseData[]) 
{	
	// 11-29-05  
	// Scheduler code for running one minute experiments. 
	// broad band filtering stores  1 minute decimated.  12500 samples/sec -> 25000 bytes/sec -> ~1464 KB/file 
	// narrowband filtering stores  1 minute decimated.
	// amplitude data: 50 samples/sec -> 100 bytes/sec -> ~ 5.8 KB/file
	// phase data:  50 samples/sec -> 100 bytes/sec -> ~ 5.8 KB/file

	float temp;
	int sec=0;
	int c, i;
	int phaseindex;
	int read_bytes;
	
	char temp_text[250];
	
	float absMaxAmp[DATA_CHANNELS];    // absolute maximum amplitude value 
	float absMinAmp[DATA_CHANNELS];    // absolute maximum amplitude value 
	
	//short* currSecRD;   // buffer for current second of raw data for processing
	short* fileSecRD; // buffer for reading in one second of data from file 
	
	NBDATA*  thisSecNBData;
	
	float* tempAmpData[DATA_CHANNELS]; 	// Holds temporary unscaled amplitude data

	// mallocing for arrays that have a component for each channel.
	float* RealMixedDown;		// Holds 1 sec real part of the mixed down data 
	float* ImagMixedDown;		// Holds 1 sec imaginary part of mixed down data
 	float* RealFiltered;		// Holds 1 sec mixed/filtered received data (real)
	float* ImagFiltered;		// Holds 1 sece mixed/filtered received data (imag)
  	float* TrellisTXT;			// Holds 1 sec generated trellis (wrapped)
  	float* TrellisRCV;			// Holds 1 sec received trellis (wrapped)
	float* PhaseData;			// Holds 1 sec phase data
  	float* AmplitudeData;		// Holds 1 sec amplitude data

	float tempMaxAmp, tempMinAmp;

	// allocate memory
	fileSecRD = malloc(DATA_CHANNELS*SAMPLING_RATE*sizeof(short));
	
	thisSecNBData = malloc(sizeof(struct NBDATA));

	RealMixedDown = (float*) malloc ( DEMOD_BUFFER_LENGTH*sizeof(float));

	ImagMixedDown = (float*) malloc ( DEMOD_BUFFER_LENGTH*sizeof(float));

	RealFiltered = (float*) malloc ((FILTERED_LENGTH+10)*sizeof(float));

	ImagFiltered = (float*) malloc ((FILTERED_LENGTH+10)*sizeof(float));

	TrellisTXT = (float*) malloc ((FILTERED_LENGTH+20)*sizeof(float));

	TrellisRCV = (float*) malloc ((FILTERED_LENGTH+20)*sizeof(float));

	// one sec of phase data
	PhaseData = (float*) malloc (DATA_CHANNELS*FINAL_OUTPUT_LENGTH*sizeof(float));

	// one sec of amplitude data
	AmplitudeData=  (float*) malloc (DATA_CHANNELS*FINAL_OUTPUT_LENGTH*sizeof(float));


	/*
    float* RealMixedDown;			// Holds the real part of the mixed down data 
	float* ImagMixedDown;			// Holds the imaginary part of mixed down data
 	float RealFiltered[1010];		// Holds the mixed/filtered received data (real)
	float ImagFiltered[1010];		// Holds the mixed/filtered received data (imag)
  	float TrellisTXT[1010];			// Holds the generated trellis (wrapped)
  	float TrellisRCV[1010];			// Holds the received trellis (wrapped)
	float PhaseData[100];			// Holds the phase data
  	float AmplitudeData[100];		// Holds the amplitude data
	RealMixedDown= (float*) malloc ( DEMOD_BUFFER_LENGTH*sizeof(float));
	assert(RealMixedDown != NULL);
	ImagMixedDown= (float*) malloc ( DEMOD_BUFFER_LENGTH*sizeof(float));
	assert(ImagMixedDown != NULL);
	*/

	// allocate space for temp storage for amplitude data
	for (i=0; i<DATA_CHANNELS; i++)
	{
	    tempAmpData[i]= malloc((FINAL_OUTPUT_LENGTH*SECS_PER_FILE+10)*sizeof(float));
	    //assert(tempMinuteAmpData[i] != NULL);
	    
	    thisSecNBData->ampdata[i]= malloc((FINAL_OUTPUT_LENGTH+10)*sizeof(float));  
	    //assert(thisSecNBData->ampdata[i] != NULL);
	    
	    thisSecNBData->phasedata[i]= malloc((FINAL_OUTPUT_LENGTH+10)*sizeof(short));
	    //assert(thisSecNBData->phasedata[i] != NULL);
	    
	    phaseindex=0;
	    // note that since phase is always between 0 2pi, we scale and cast phase data in the processing function. 
	    //if((tempMinuteAmpData[i] == NULL) || (thisSecNBData->ampdata[i] == NULL) || (thisSecNBData->phasedata[i] == NULL))
		//	b_log("thisSecNBData not allocated properly.\n", 0);
   	}

	SerOut("Start processing data file.\n");
	// loop for each second for a one minute data file
	for(sec=0; sec<SECS_PER_FILE; sec++)
	{
		//UNCOMMENT THESE LINES FOR REAL USE!!!
		//======================================
		//fread(currSecRD, sizeof(short), ADC_SAMPLE_RATE*2, RDfileptr);
		//index = 0;
   		//for (i = antenna; i < ADC_SAMPLE_RATE; i+=2)
   		//{
   		// 		currSecRD[index] = currSecRD[i];
   		// 		index++;
   		//}
		//fread(currSecRD, sizeof(short), ADC_SAMPLE_RATE, RDfileptr);
		
		// read 1 second = #channels*sizeof(short)*Fs
		read_bytes = fs_read(RDfileptr, (char*)fileSecRD, DATA_CHANNELS*SAMPLING_RATE*sizeof(short)); 
		
		//sprintf(temp_text, "Read %i bytes.\n", read_bytes);
		//SerOut(temp_text);
		
		if ((read_bytes < DATA_CHANNELS*SAMPLING_RATE*sizeof(short) ) || (read_bytes <0))
		{
			b_log("Error reading from file.\n", 1);
			return -1;  
		}
		 		
		//thisSecNBData= processNarrowBand(NBexp, currSecRD, RealMixedDown, ImagMixedDown,RealFiltered,ImagFiltered,TrellisTXT,TrellisRCV, PhaseData, AmplitudeData);
		processNarrowBand(	NBexp, 
							thisSecNBData,
							fileSecRD, 
							RealMixedDown, 
							ImagMixedDown, 
							RealFiltered, 
							ImagFiltered, 
							TrellisTXT, 
							TrellisRCV, 
							PhaseData, 
							AmplitudeData);

    	// find the maximum amplitude within the minute of data 
    	for(c=0; c< DATA_CHANNELS; c++) 
    	{ 
    		// for each channel 
	  			
	  		// copy amplitude data over to temp storage, scaled at end.		
			//DSPF_sp_blk_move(&(tempMinuteAmpData[c][(sec)*(FINAL_OUTPUT_LENGTH)]),thisSecNBData->ampdata[c], FINAL_OUTPUT_LENGTH);
	    	memcpy( &(tempAmpData[c][(sec)*(FINAL_OUTPUT_LENGTH)]), thisSecNBData->ampdata[c], FINAL_OUTPUT_LENGTH*sizeof(float));
    		     		
     		// copy phase data over to final output phase data array - and convert to shorts
   			for (i=0; i<(thisSecNBData->phaselength[c]); i++)
    		{
    			finalPhaseData[c][phaseindex+i] = (short)((thisSecNBData->phasedata[c])[i]);
    		}
      	}
    	phaseindex += thisSecNBData->phaselength[c];
    	SerOut("*");
      	
      	//sprintf(temp_text, "Finished processing sec %i\n", sec);
      	//SerOut(temp_text);
	} //for (sec=0; sec<SECS_PER_FILE; sec++)
	SerOut("\nFinished.\n");
	
	SerOut("Scaling...");
	//--------Calculate Max and Min Amp Values for entire file length
	for (c=0; c< DATA_CHANNELS; c++) 
	{
		/*
    	//absMaxAmp[c] = tempMinuteAmpData[c][0];
    	//absMinAmp[c] = tempMinuteAmpData[c][0];
  		tempMaxAmp = tempMinuteAmpData[c][0];
    	tempMinAmp = tempMinuteAmpData[c][0];
  		for(i= 0; i< FINAL_OUTPUT_LENGTH*SECS_PER_FILE; i++) 
		{
			if (tempMinuteAmpData[c][i] > tempMaxAmp)
				tempMaxAmp = tempMinuteAmpData[c][i];
			if (tempMinuteAmpData[c][i] < tempMinAmp)
				tempMinAmp = tempMinuteAmpData[c][i];
		}
		*/	
			
		//float DSPF_sp_maxval (const float* x, int nx)
		tempMaxAmp= DSPF_sp_maxval (tempAmpData[c], FINAL_OUTPUT_LENGTH*SECS_PER_FILE);
		//float DSPF_sp_minval (const float* x, int nx)
		tempMinAmp= DSPF_sp_minval (tempAmpData[c], FINAL_OUTPUT_LENGTH*SECS_PER_FILE);
		
		absMaxAmp[c] = ((short)tempMaxAmp)+1;
		absMinAmp[c] = (short)tempMinAmp;
		
		// rescale all values
  		for(i= 0; i< FINAL_OUTPUT_LENGTH*SECS_PER_FILE; i++) 
  		{
   			// rescale the values here using the maximum and min amplitude values.
			temp = (tempAmpData[c][i]-((float)absMinAmp[c]))/(((float)absMaxAmp[c])- ((float)absMinAmp[c]))*65536.0;
   			if(temp > 65536.0)
   			 	temp = 65536.0;
   			if (temp < 0.0)
   				temp = 0.0;
   			temp = temp-32769.0;
    		finalAmpData[c][i]= (short) temp;
    	} // for(i= 0; i< FINAL_OUTPUT_LENGTH*SECS_PER_FILE; i++)
    
		//printf("After scaling %d loop\n",c);
	    finalAmpData[c][MIN_AMP_INDEX] = absMinAmp[c];
		finalAmpData[c][MAX_AMP_INDEX] = absMaxAmp[c];
	}
	SerOut("Finished.\n");
	
	// Cleanup
	free(RealMixedDown);
	free(ImagMixedDown);
	free(RealFiltered);
	free(ImagFiltered);
	free(TrellisTXT);
	free(TrellisRCV);
	free(PhaseData);
	free(AmplitudeData);

	for(c=0; c<DATA_CHANNELS; c++)
	{
		//printf("Free tempminampdata\n");
	    free(tempAmpData[c]);
		//printf("Free thisampdata\n");
	    free(thisSecNBData->ampdata[c]);  
		//printf("Free thisphsdata\n");
	    free(thisSecNBData->phasedata[c]);
	}
	 
   	free(thisSecNBData);
   	
   	return 1;
}

// rewritten to process one
int New_NB_Dynamic(int txFreq, int Datafileptr, int NBAmpFIDs[], int NBPhaseFIDs[])	
{
	int i,c;

	short* ampToWrite[DATA_CHANNELS];
	short* phaseToWrite[DATA_CHANNELS];
	
	short temp_data;
	
	NB_EXPERIMENT* NBexp;	

	SerOut("Starting NB Processing...\n");
 	for (i=0; i<DATA_CHANNELS; i++)
	{
	    // these are the final arrays of data for the ENTIRE file
	    // one for each data channel
	    ampToWrite[i]= malloc ((FINAL_OUTPUT_LENGTH*SECS_PER_FILE+2)*sizeof(short));   
	    phaseToWrite[i]= malloc((FINAL_OUTPUT_LENGTH*SECS_PER_FILE)*sizeof(short)); 
	}
	
	// create the experiment with the desired transmitters to filter
	b_log("Creating NB Experiment...", 0);
	NBexp = CreateExperimentNB(FilterTapsNB, NUMTAPS_NB, txFreq) ;
    SerOut("Finished.\n");

	// run all NB processing here
	// reads raw data, processes and returns two arrays with amp and phase data to be written to file
	b_log("Processing NB...", 0);
	OneFileAcquisition(NBexp, Datafileptr, ampToWrite, phaseToWrite);
	SerOut("Finished.\n");
	
	// open files, write amp data (including min, max values) and phase data
	// this is currently using fprintf so i can easily plot in matlab. will change cmds to fwrite. 
	b_log("Writing Data.", 0);
	for(c=0; c<DATA_CHANNELS; c++) 
	{	
		//fsputc(NBAmpFIDs[c], '*');
		//fsputc(NBAmpFIDs[c], 'N');
		//fsputc(NBAmpFIDs[c], 'B');
		//fsputc(NBAmpFIDs[c], '*');
		//fs_write(NBAmpFIDs[c], "*NB*", 4);
		
		//should switch this up...confusing in post processing.

		//write minAmp value to amp file
		//fprintf(NBAmpFIDs[c], "%d\n",ampToWrite[c][MIN_AMP_INDEX]);
		temp_data = ampToWrite[c][MIN_AMP_INDEX];	 	
		//fsputc(NBAmpFIDs[c], (unsigned char)((temp_data & 0xFF00)>>8));
		//fsputc(NBAmpFIDs[c], (unsigned char)(temp_data & 0x00FF));	
		// reverse byte order
		fsputc(NBAmpFIDs[c], (unsigned char)(temp_data & 0x00FF));	
		fsputc(NBAmpFIDs[c], (unsigned char)((temp_data & 0xFF00)>>8));
		
		//write maxAmp value to amp file
		//fprintf(NBAmpFIDs[c], "%d\n",ampToWrite[c][MAX_AMP_INDEX]);
		temp_data = ampToWrite[c][MAX_AMP_INDEX];	 	
		//fsputc(NBAmpFIDs[c], (unsigned char)((temp_data & 0xFF00)>>8));
		//fsputc(NBAmpFIDs[c], (unsigned char)(temp_data & 0x00FF));	
		// reverse byte order
		fsputc(NBAmpFIDs[c], (unsigned char)(temp_data & 0x00FF));	
		fsputc(NBAmpFIDs[c], (unsigned char)((temp_data & 0xFF00)>>8));

		//fwrite(&(ampToWrite[c][MIN_AMP_INDEX]), sizeof(short), 1, NBAmpFIDs[c]);
  		for(i= 0; i< FINAL_OUTPUT_LENGTH*SECS_PER_FILE; i++) 
  		{
		  	//printf("%d\n", ampToWrite[c][i]);
		  	//printf("%d\n", phaseToWrite[c][i]);
		  	
		  	//fprintf(NBAmpFIDs[c],"%d\n", ampToWrite[c][i]);
			temp_data = ampToWrite[c][i];	 	
			//fsputc(NBAmpFIDs[c], (unsigned char)((temp_data & 0xFF00)>>8));
			//fsputc(NBAmpFIDs[c], (unsigned char)(temp_data & 0x00FF));	
			// reverse byte order
			fsputc(NBAmpFIDs[c], (unsigned char)(temp_data & 0x00FF));	
			fsputc(NBAmpFIDs[c], (unsigned char)((temp_data & 0xFF00)>>8));
			
		  	//fprintf(NBPhaseFIDs[c],"%d\n", phaseToWrite[c][i]);
 			temp_data = phaseToWrite[c][i];	 	
			//fsputc(NBPhaseFIDs[c], (unsigned char)((temp_data & 0xFF00)>>8));
			//fsputc(NBPhaseFIDs[c], (unsigned char)(temp_data & 0x00FF));	
			// reverse byte order
			fsputc(NBPhaseFIDs[c], (unsigned char)(temp_data & 0x00FF));	
			fsputc(NBPhaseFIDs[c], (unsigned char)((temp_data & 0xFF00)>>8));
 		}
  	}//for(c=0; c<NUM_CHAN;c++) 

	// Call in the cleaners
	SerOut("Cleaning up after NB.\n");
	for(c=0; c<DATA_CHANNELS; c++) 
	{
		if (ampToWrite[c] != NULL)
		  	free(ampToWrite[c]);
		if (phaseToWrite[c] != NULL)
		  	free(phaseToWrite[c]);
	}
	
    //when the experiment is done, call DestroyNBExperiment(NBexp)
    DestroyExperimentNB(NBexp);

  	return 0;
}





//end OneFileAcquisition   
	
//int main(int argc, char* argv[])
/*
int main(void)
{
	//interpret argc and argv to get our variables....
//  buoyfilt FILE* BBfileptr int antenna FILE* NBAmp0 FILE* NBPhase0
//										 FILE* NBAmp1 FILE* NBPhase1
//										FILE* NBAmp2 FILE* NBPhase2
//										FILE* NBAmp3 FILE* NBPhase3
	FILE* BBfileptr;
	int antenna = 0;
	FILE* NBAmpFIDs[NUM_CHAN];
	FILE* NBPhaseFIDs[NUM_CHAN];
	int i;

	BBfileptr = fopen("minuteRawData", "r");
	assert(BBfileptr != NULL);
	NBAmpFIDs[0] = fopen("AmpCh0.m","w");
	assert(NBAmpFIDs[0] != NULL);
	NBAmpFIDs[1] = fopen("AmpCh1.m","w");
	assert(NBAmpFIDs[1] != NULL);
	NBAmpFIDs[2] = fopen("AmpCh2.m","w");
	assert(NBAmpFIDs[2] != NULL);
	NBAmpFIDs[3] = fopen("AmpCh3.m","w");
	assert(NBAmpFIDs[3] != NULL);
	NBPhaseFIDs[0] = fopen("PhaseCh0.m","w");
	assert(NBPhaseFIDs[0] != NULL);
	NBPhaseFIDs[1] = fopen("PhaseCh1.m","w");
	assert(NBPhaseFIDs[1] != NULL);
	NBPhaseFIDs[2] = fopen("PhaseCh2.m","w");
	assert(NBPhaseFIDs[2] != NULL);
	NBPhaseFIDs[3] = fopen("PhaseCh3.m","w");
	assert(NBPhaseFIDs[3] != NULL);

	printf("Just Before Run.\n");
	Run(BBfileptr, antenna, NBAmpFIDs, NBPhaseFIDs);
	printf("Just After Run.\n");

	if (BBfileptr != NULL) fclose(BBfileptr);
	for (i = 0; i < NUM_CHAN; i++)
	{
		if (NBAmpFIDs[i] != NULL) 
			fclose(NBAmpFIDs[i]);
		if (NBPhaseFIDs[i] != NULL) 
			fclose(NBPhaseFIDs[i]);
	}
}
*/

/*
int NB_Dynamic(int BBfileptr, int antenna, int NBAmpFIDs[], int NBPhaseFIDs[])	
{
	int i,c;
	int txFreq[NUM_CHAN]; 

	short* ampToWrite[NUM_CHAN];
	short* phaseToWrite[NUM_CHAN];
	
	short temp_data;
	
	NB_EXPERIMENT* NBexp;
	
	txFreq[0]= NAA;
	txFreq[1]= NLK;
	txFreq[2]= NLM;
	txFreq[3]= NPM;
	

	//printf("Just Before Run Malloc.\n");
 	for (i=0; i<NUM_CHAN; i++)
	{
	    //these are the final arrays of data for the ENTIRE file.
	    ampToWrite[i]= malloc ((FINAL_OUTPUT_LENGTH*SECS_PER_FILE+2)*sizeof(short));   
	    //assert(ampToWrite[i] != NULL);
	    if(ampToWrite[i] == NULL) b_log(fshandles, "ampToWrite[i] equals NULL.\n", 0);
	    
	    phaseToWrite[i]= malloc((FINAL_OUTPUT_LENGTH*SECS_PER_FILE)*sizeof(short)); 
	    //assert(phaseToWrite[i] != NULL);
	    if(phaseToWrite[i] == NULL) b_log(fshandles, "phaseToWrite[i] equals NULL.\n", 0);
	}
	
// *************************************************************************************8
// *** create the experiment with the desired transmitters to filter
	//printf("Just Before Run CreateExperimentNB.\n");
	NBexp = CreateExperimentNB(FilterTapsNB,NUMTAPS_NB, txFreq) ;

	// *** run all NB processing here
	// *** reads raw data, processes and returns two arrays with amp and phase data to be written to file

	//printf("Just Before Run OneFileAcquisition.\n");
	OneFileAcquisition(NBexp,BBfileptr,antenna,ampToWrite,phaseToWrite);

	// ***open files, write amp data (including min, max values) and phase data
	// this is currently using fprintf so i can easily plot in matlab. will change cmds to fwrite. 
	//printf("Just Before Run OutputWrites.\n");
	for(c=0; c<NUM_CHAN;c++) 
	{	
		//write minAmp value to amp file
		//fprintf(NBAmpFIDs[c], "%d\n",ampToWrite[c][MIN_AMP_INDEX]);
		temp_data = ampToWrite[c][MIN_AMP_INDEX];	 	
		fsputc(NBAmpFIDs[c], (unsigned char)((temp_data & 0xFF00)>>8));
		fsputc(NBAmpFIDs[c], (unsigned char)(temp_data & 0x00FF));	
		
		//write maxAmp value to amp file
		//fprintf(NBAmpFIDs[c], "%d\n",ampToWrite[c][MAX_AMP_INDEX]);
		temp_data = ampToWrite[c][MAX_AMP_INDEX];	 	
		fsputc(NBAmpFIDs[c], (unsigned char)((temp_data & 0xFF00)>>8));
		fsputc(NBAmpFIDs[c], (unsigned char)(temp_data & 0x00FF));	

		//fwrite(&(ampToWrite[c][MIN_AMP_INDEX]), sizeof(short), 1, NBAmpFIDs[c]);
  		for(i= 0; i< FINAL_OUTPUT_LENGTH*SECS_PER_FILE; i++) 
  		{
		  	//printf("%d\n", ampToWrite[c][i]);
		  	//printf("%d\n", phaseToWrite[c][i]);
		  	
		  	//fprintf(NBAmpFIDs[c],"%d\n", ampToWrite[c][i]);
			temp_data = ampToWrite[c][i];	 	
			fsputc(NBAmpFIDs[c], (unsigned char)((temp_data & 0xFF00)>>8));
			fsputc(NBAmpFIDs[c], (unsigned char)(temp_data & 0x00FF));	
			
		  	//fprintf(NBPhaseFIDs[c],"%d\n", phaseToWrite[c][i]);
 			temp_data = phaseToWrite[c][i];	 	
			fsputc(NBPhaseFIDs[c], (unsigned char)((temp_data & 0xFF00)>>8));
			fsputc(NBPhaseFIDs[c], (unsigned char)(temp_data & 0x00FF));	
 		}
  	}//for(c=0; c<NUM_CHAN;c++) 

	// ****END TEST FILE ONE*********************
	for(c=0; c<NUM_CHAN;c++) 
	{
		if (ampToWrite[c] != NULL)
		  free(ampToWrite[c]);
		if (phaseToWrite[c] != NULL)
		  free(phaseToWrite[c]);
	}
	
    //when the experiment is done, call DestroyNBExperiment(NBexp)
	//printf("Just Before Run DestroyExpNB.\n");
       	DestroyExperimentNB(NBexp);
	//printf("Just After Run DestroyExpNB.\n");

  	return 0;
}
*/

