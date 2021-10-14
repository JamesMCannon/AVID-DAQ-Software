
// Class::FIR
// ----------
// This is the interface file for the FIR class.  The FIR class
// can be used for real-time filtering of a signal.  One filter
// should be created for each signal that you wish to filter.
// The filter remembers past inputs so that when future inputs
// are received it can use the information.  

//#include "stdafx.h"

// Written By: Jeffrey M. DiCarlo 2-6-97

#ifndef _FIR_H_
#define _FIR_H_

#include <string.h>
#include <iostream>
//#include <cstdlib>
using namespace std;

#define MAX_FILTER_LENGTH 10000

class FIR {

  public:

    // Constructors
    // ------------
    // Use to create an FIR filter.  If the default constructor
    // is used the Create method MUST be called before using
    // using any other methods.
    FIR();
    FIR(double* filter, int filterLength, int decimateLength, bool copyFilter = true);
    
    // Destructors
    // -----------
    // Deallocates the filter object    
    ~FIR();

    // Function: Create
    // ----------------
    // Allocates the necessary space for a filter.  This method
    // MUST be called if the filter object is constructed with
    // the default constructor or the object will be reused. 
    void Create(double* filter, int filterLength, int decimateLength, bool copyFilter = true);
	bool IsCreated();
    
	double* GetFilterPointer(int* filterlength);

    // Function: Destroy
    // -----------------
    // Deallocates the space for a filter.  Call this function
    // if you wish to reuse a filter object.  This function is
    // automatically called if the object is destroyed.
    void Destroy();

    // Function: Filter
    // ----------------
    // Implements an FIR filter on the input data.  The output
    // array must have enough space to hold the output.
    void Filter(double* output, int* outputLength,
                double* input, unsigned int inputLength);

	// Provide a version that takes/gives ints instead 

	void Filter(float* output, int* outputLength,
                 short* input, unsigned int inputLength);



    // Function: Reset
    // ---------------
    // Resets the filter.  Call if a new input signal is going
    // to be run into the same filter type.
    void Reset();
    double* m_filterTable;

  private:


    double* m_pastSum;

    int m_filterLength;
    int m_filterOffset;
    int m_decimateLength;

    bool m_filterCopy;
};

#endif
