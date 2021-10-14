///////////////////////////////////////////////////////////////////////////////
//
// PHASE.CPP - Computes the average phase difference.
//

#include <assert.h> 
#include <math.h>    
#include <memory.h>
#include <iostream>
#include <stdio.h>
#include <string.h>
#include "PHASE.h" 

///////////////////////////////////////////////////////////////////////////////
//
// Constants.
//

//static const double PI      = 3.141592653589793;
#define PI 3.141592653589793

///////////////////////////////////////////////////////////////////////////////
//
// Constructor.
//

PHASE::PHASE()
{
	Create();
}


int PHASE::Create()
{
    m_OutTXT  = 0;
    m_OutRCV  = 0;
	memset(m_TrellisTXT, 0, PHASE_MAX_LENGTH*sizeof(*m_TrellisTXT));
	memset(m_RealRCV, 0, PHASE_MAX_LENGTH*sizeof(*m_RealRCV));
	memset(m_ImagRCV, 0, PHASE_MAX_LENGTH*sizeof(*m_ImagRCV));
	m_last_phase_value = 0;
	m_tally = 0;

	return 0;
}

void PHASE::Reset()
{
	Create();
}


///////////////////////////////////////////////////////////////////////////////
//
// GetPhase() - Returns the phase difference between the TXT and RCV signals.
//            - TXT phase is always considered ahead of RCV phase.
//

void PHASE::GetMSKPhase
(
    float*  Output,
    int*    OutputLength,
	double* TrellisTXT,
    int     LengthTXT,
    double*  RealRCV,
    double*  ImagRCV,
    int     LengthRCV,
	int		AverageLength
)
{
    double  PhaseTXT, PhaseRCV;

    int     BufLenRCV,      BufLenTXT;
    int     TempRCV,		TempTXT;
	int     IndexIN,        IndexOT;
    int     ProcessLength;
    int     i, j;
	double	phase1000;
	double	ImagResult, RealResult;
	double tempOutput[PHASE_MAX_LENGTH];
	double last_phase_value;
	bool last_phase_value_set;
	last_phase_value = 0;
    // Copy data to the end of the local buffers.

	memcpy(&m_RealRCV[m_OutRCV], RealRCV, LengthRCV*sizeof(*m_RealRCV));
    memcpy(&m_ImagRCV[m_OutRCV], ImagRCV, LengthRCV*sizeof(*m_ImagRCV));
	memcpy(&m_TrellisTXT[m_OutTXT], TrellisTXT, LengthTXT*sizeof(*TrellisTXT));

    BufLenRCV = LengthRCV + m_OutRCV;
    BufLenTXT = LengthTXT + m_OutTXT;

    assert(BufLenRCV < PHASE_MAX_LENGTH && BufLenTXT < PHASE_MAX_LENGTH);

    // Determine the number of samples to process.
    // Must be a multiple of the average length.
    
    TempRCV = BufLenRCV - ( BufLenRCV % AverageLength );
    TempTXT = BufLenTXT - ( BufLenTXT % AverageLength );
  
    ProcessLength = (TempRCV < TempTXT) ? TempRCV : TempTXT;
    ProcessLength = (ProcessLength < 0) ? 0 : ProcessLength;

    // Calculate the phase difference.	
	last_phase_value_set = false;
    for( i=0, IndexOT=0; i<ProcessLength; i+=AverageLength, IndexOT++ )
    {        
        
		ImagResult = 0;
		RealResult = 0;

		for( j=0; j<AverageLength; j++ )
		{

			IndexIN = i+j;    // Input sample index.

	        // Compute current phases for RCV and TXT.

			if (m_TrellisTXT[IndexIN] != PHASE_BIT_ERROR)
			  {
			    PhaseTXT  = m_TrellisTXT[IndexIN];
			    PhaseRCV  = atan2(2.0*m_RealRCV[IndexIN]*m_ImagRCV[IndexIN], m_RealRCV[IndexIN]*m_RealRCV[IndexIN] - m_ImagRCV[IndexIN]*m_ImagRCV[IndexIN]);
			    
				phase1000 = PhaseRCV - PhaseTXT;
			    
				ImagResult += (double)sin(phase1000);
			    RealResult += (double)cos(phase1000);
			}
		}
		if ((ImagResult == 0) && (RealResult == 0))
			tempOutput[IndexOT] = PHASE_BIT_ERROR;
		else
			tempOutput[IndexOT] = (double)atan2(ImagResult, RealResult);

		last_phase_value = tempOutput[IndexOT];
		last_phase_value_set = true;
	}
	
    *OutputLength = ProcessLength / AverageLength;

	//Unwrap
	unwrap(tempOutput, tempOutput, *OutputLength);

	if (last_phase_value_set)
		m_last_phase_value = last_phase_value;

	//Divide by 2 and Wrap to -PI to PI
	for (i = 0; i < *OutputLength; i++)
	{
		tempOutput[i] = mod(tempOutput[i]/2.0,2.0*PI);
		if (tempOutput[i] >= PI)
			tempOutput[i] -= 2.0*PI;
	}

	for (i = 0; i < *OutputLength; i++)
		Output[i] = (float)(tempOutput[i]*180.0/PI);

    // Move unprocessed data to the front of the local buffer.

    m_OutTXT = BufLenTXT - ProcessLength;
    m_OutRCV = BufLenRCV - ProcessLength;
  
    memmove(m_RealRCV, &m_RealRCV[ProcessLength], m_OutRCV*sizeof(*m_RealRCV));
    memmove(m_ImagRCV, &m_ImagRCV[ProcessLength], m_OutRCV*sizeof(*m_ImagRCV));
	memmove(m_TrellisTXT, &m_TrellisTXT[ProcessLength], m_OutTXT*sizeof(*m_TrellisTXT));
}

double PHASE::mod(double mod_this, double by_this)
{
	int x;
	double out,y;

	if (by_this == 0)
		return(mod_this);

	y = (mod_this/by_this);
	
	if (y < (double)((int) y))
		x = (int) y - 1;
	else
		x = (int) y;

	out = mod_this - ((double)x)*by_this;

	return(out);
}


void PHASE::GetCWPhase
(
    float*  Output,
    int*    OutputLength,
    double*  RealRCV,
    double*  ImagRCV,
    int     LengthRCV,
	int		AverageLength
)
{
    double  PhaseRCV;
    double  phase;

	int     IndexIN,        IndexOT;
    int     i, j;
	double	ImagResult, RealResult;

    assert(LengthRCV < PHASE_MAX_LENGTH);

    // Determine the number of samples to process.
    // Must be a multiple of the average length.
      
    // Calculate the phase difference.	
    
    for( i=0, IndexOT=0; i<LengthRCV; i+=AverageLength, IndexOT++ )
    {        
        
		ImagResult = 0;
		RealResult = 0;

		for( j=0; j<AverageLength; j++ )
		{

			IndexIN = i+j;    // Input sample index.

		    PhaseRCV  = atan2( ImagRCV[IndexIN], RealRCV[IndexIN] );
		    			    
		    ImagResult += ((double)sin(PhaseRCV));
		    RealResult += ((double)cos(PhaseRCV));
		}
		if ((ImagResult == 0) && (RealResult == 0))
			phase = PHASE_BIT_ERROR;
		else
			phase = atan2(ImagResult, RealResult);

		Output[IndexOT] = (float) (phase*180.0/PI);
	}

    *OutputLength = LengthRCV / AverageLength;
}


void PHASE::unwrap(double* out, double* phase, int length)
{
	double	dphase;
	int		i;
	double one_behind;

	assert(out != NULL);
	assert(phase != NULL);

	one_behind = m_last_phase_value;

	for (i = 0; i < length; i++)
	{
		dphase = phase[i] - one_behind;
		if (dphase > PI)
		{
			m_tally--;
		}
		else if (dphase < -PI)
		{
			m_tally++;
		}
		one_behind = phase[i];
		out[i] = phase[i] + 2.0*PI*((double)m_tally);
	}
	m_tally %= 2;

	return;
}

