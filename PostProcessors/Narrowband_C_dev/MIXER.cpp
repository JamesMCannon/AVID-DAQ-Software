// MIXER.cpp: implementation of the MIXER class.
//
//////////////////////////////////////////////////////////////////////

//#include "stdafx.h"
//#include "VLF_daq.h"
#include "MIXER.h"
#include <math.h>
#include <assert.h>
#include <cstdlib>

#ifdef _DEBUG
#undef THIS_FILE
static char THIS_FILE[]=__FILE__;
#define new DEBUG_NEW
#endif

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////



MIXER::MIXER()
: m_mixerLength(0), m_mixerOffset(0),
  m_bCreated(0)
{
  // Must call the MIXER::Create function to use the MIX
  m_sinTable = NULL;
  m_cosTable = NULL;
}

MIXER::MIXER(unsigned int frequency, double timeInterval,
             unsigned int mixerLengths, unsigned int phase, short channel_select)
: m_mixerOffset(0), m_bCreated(0)
{
  Create(frequency, timeInterval, mixerLengths, phase, channel_select);
}

MIXER::~MIXER() 
{
  Destroy();
}

void MIXER::Create(unsigned int frequency, double timeInterval,
                   unsigned int mixerLengths, unsigned int phase, short channel_select)
{
  const double TWO_PI = (double)6.283185307179586;
  double arg = TWO_PI*((double)frequency)*timeInterval;
  unsigned long i;

  assert(m_bCreated == 0);  // Must call MIXER::Destroy before
                            // creating another mixer.

  //assert(mixerLengths <= MIXER_MAX_LENGTH); // Must increase the MAX
                                            // MIXER LENGTH

  assert((channel_select == 0) || (channel_select == 1));
  m_mixerLength = mixerLengths;
  m_mixerOffset = phase;
  m_sinTable = new double[m_mixerLength];
  m_cosTable = new double[m_mixerLength];


  for(i=0; i < m_mixerLength; i++) 
  {
	  m_sinTable[i] = (double)(-sin(arg * (((double)channel_select)/((double)2.0) + ((double) i))));
	  m_cosTable[i] = (double)cos(arg * (((double)channel_select)/((double)2.0) + ((double) i)));
  }

  m_bCreated = 1;
}

void MIXER::Destroy()
{
  m_bCreated = 0;
  m_mixerLength =0;
  m_mixerOffset =0;
  
  delete [] m_sinTable;
  delete [] m_cosTable;
  m_sinTable = NULL;
  m_cosTable = NULL;

}

void MIXER::MixDown(double* outReal, double* outImag,
                    double* input, unsigned int inputLength)
{
  unsigned int mixerOffset = 0;

  assert(m_bCreated == 1);   // Must call MIXER::Create before using
                             // any of the mixer operations.
  
  //mixerOffset = (m_mixerOffset-1); //Doesn't do anything...

  for(unsigned int i=0; i<inputLength; i++) {
    mixerOffset = (m_mixerOffset+i)%m_mixerLength;
    outReal[i]  = input[i] * m_cosTable[mixerOffset];
    outImag[i]  = input[i] * m_sinTable[mixerOffset];
  }
  m_mixerOffset = mixerOffset+1;
}

void MIXER::Reset()
{
	m_mixerOffset = 0;
}
