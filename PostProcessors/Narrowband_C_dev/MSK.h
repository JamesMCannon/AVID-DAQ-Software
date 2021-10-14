///////////////////////////////////////////////////////////////////////////////
//
// MSK.H - Interface file for the MSK class.
//

// Written By: Jeffrey M. DiCarlo 7-30-98

#ifndef _MSK_H_
#define _MSK_H_

//#include <iostream.h>
#include <math.h>
#include <assert.h>
#include <memory.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <iostream>
using namespace std;

///////////////////////////////////////////////////////////////////////////////
//
// CONSTANTS 
//

//const double PI	     = 3.141592653589793;
#define PI	      3.141592653589793

//static double mod(double mod_this, double by_this);
//static void wrap(double* out, double* phase, int length);
//static void unwrap(double* out, double* phase, int length);
//static int comparefn(const void *i, const void *j);

///////////////////////////////////////////////////////////////////////////////
//
// CONSTANTS
//
								
//const int MIN_SAMPLES_PER_BIT = 3;
//const int MAX_SAMPLES_PER_BIT = 40;
//const int MAX_INPUT_LENGTH = 1000+2*MAX_SAMPLES_PER_BIT;
//const int MAX_DIFF_LENGTH = MAX_INPUT_LENGTH/MIN_SAMPLES_PER_BIT+1;

#define MIN_SAMPLES_PER_BIT 3
#define MAX_SAMPLES_PER_BIT 40
#define MAX_INPUT_LENGTH (1000+2*MAX_SAMPLES_PER_BIT)
#define MAX_DIFF_LENGTH (MAX_INPUT_LENGTH/MIN_SAMPLES_PER_BIT+1)

///////////////////////////////////////////////////////////////////////////////
//
// MSK Class
//

class MSK
{
public:

    // Constructor Functions

            MSK();
			MSK(int samples_per_bit);
            ~MSK();
    int Reset();

    // Creatation Functions

	void Create(int samples_per_bit);
    void    Destroy                 (                       );
    
    // Processing Functions
    
    int     FitCurve                (	double* OutTrellisTXT,
										int*	OutLengthTXT,
										//double*	MagOutRCV,
										double* OutTrellisRCV,
										double*	InReal,
										double*	InImag,
										int		InLength  );
    

private:
	void GetWrappedTrellis(double* out, double* real,double* imag, int length);
	int GetIdealTrellis(double* out, int process_length);
	int FinishIdealTrellis(double* out, int process_length);
	void CalculateBTT(double* unwrapped, int length);

	double m_SavedTrellisRCV[3*MAX_SAMPLES_PER_BIT];

    double m_BufTrellisRCV[MAX_INPUT_LENGTH];	// RCV Trellis
	double m_last_phase_sample;
    int m_PastLength; // Length of old data left
	int m_PastSavedLength;
	int m_samples_per_bit;
	bool m_created;
	double m_phase_per_sample;
	int m_max_bit_index;
	double m_BTT;
	int m_min_bit_index;
	bool m_last_BTT_set;
	double m_last_BTT;
	int m_count;
	int m_accumulated_offset;
};

#endif /* _MSK_H_ */


