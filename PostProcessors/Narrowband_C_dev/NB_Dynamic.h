// wrapper for accessing experiment.c functions
#ifndef _NB_DYNAMIC_H
#define _NB_DYNAMIC_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <DSPF_sp_maxval.h>
#include <DSPF_sp_minval.h>

#include "Globals.h"

#include "experiment.h"
#include "serialIO.h"
#include "revfs10.h"

/*
void sum(short* output, short* A, short* B, int length);

void makecosf(float* out, float A, float omega, int fs, int length);
void makecoss(short* out, float A, float omega, int fs, int length);
void makesinf(float* out, float A, float omega, int fs, int length);
void makesins(short* out, float A, float omega, int fs, int length);
void linspace(float* out, float pointA, float pointB, int length);
void testAmp(void);
void testPhase(void);
void testMixer(void);
void testFir(void);
void testExperiment(void);
*/
    
//int NB_Dynamic(int BBfileptr, int antenna, int NBAmpFIDs[], int NBPhaseFIDs[]);
	
// takes input tranmitter freq, data file pointer, writes to output files
int New_NB_Dynamic(int txFreq, int Datafileptr, int NBAmpFIDs[], int NBPhaseFIDs[]);
    
// files are opened ,read from in OneFileAcq, for the length of data in one file.
int OneFileAcquisition(	NB_EXPERIMENT* NBexp, 
							int RDfileptr, 
							short* finalAmpData[DATA_CHANNELS], 
							short* finalPhaseData[DATA_CHANNELS]);
    
#endif

