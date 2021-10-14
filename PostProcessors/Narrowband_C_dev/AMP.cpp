// AMP.cpp: implementation of the AMP class.
//
//////////////////////////////////////////////////////////////////////
//#include "stdafx.h"
#include "AMP.h"
//#include "VLF_daq.h"
#include <assert.h> 
#include <math.h>    
#include <memory.h>
#include <fstream>




#ifdef _DEBUG
#undef THIS_FILE
static char THIS_FILE[]=__FILE__;
#define new DEBUG_NEW
#endif

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

AMP::AMP()
{
	Create(); 
}

void AMP::Reset()
{
	Create();
}

void AMP::Create()
{
	m_nOutRCV = 0;
	memset(m_fRealRCV, 0, AMP_MAX_LENGTH*sizeof(*m_fRealRCV));
	memset(m_fImagRCV, 0, AMP_MAX_LENGTH*sizeof(*m_fRealRCV));
}

/////////////////////////////////////////////////////////////////////////


void AMP::GetAmp(float* output, int* outputLength, double* realRCV, double* imagRCV, int lengthRCV, int resolution, double ScaleFactor)
{
	int length, i, j;
	int process_length;
	double temp;

	assert(resolution !=0 );
	int AMP_AVERAGE = (int) (1000/resolution);

	memcpy(&m_fRealRCV[m_nOutRCV], realRCV, lengthRCV*sizeof(*m_fRealRCV));
	memcpy(&m_fImagRCV[m_nOutRCV], imagRCV, lengthRCV*sizeof(*m_fImagRCV));
	
	length = lengthRCV + m_nOutRCV;
	assert(length < AMP_MAX_LENGTH);

	//compute averaged amplitude output.
	process_length = (int) (floor((double)length/(double)AMP_AVERAGE) * AMP_AVERAGE);
	for (i =0; i < process_length/AMP_AVERAGE; i++)
	{
		temp = 0.0;
		for (j=0; j < AMP_AVERAGE; j++)
		{
			temp +=(double)pow(m_fRealRCV[j+i*AMP_AVERAGE]*m_fRealRCV[j+i*AMP_AVERAGE] + m_fImagRCV[j+i*AMP_AVERAGE]*m_fImagRCV[j+i*AMP_AVERAGE],(double)0.5);
		}
		output[i] = (float)(temp / (double) AMP_AVERAGE * ScaleFactor); 
	}
	*outputLength = process_length/AMP_AVERAGE;
	
	m_nOutRCV = length - process_length;
	memcpy(m_fRealRCV, &m_fRealRCV[process_length], m_nOutRCV*sizeof(*m_fRealRCV));
	memcpy(m_fImagRCV, &m_fImagRCV[process_length], m_nOutRCV*sizeof(*m_fImagRCV));
}



AMP::~AMP()
{
	Destroy(); 
}


void AMP::Destroy()
{
	m_nOutRCV = 0;
	memset(m_fRealRCV, 0, AMP_MAX_LENGTH*sizeof(*m_fRealRCV));
	memset(m_fImagRCV, 0, AMP_MAX_LENGTH*sizeof(*m_fRealRCV));
}
