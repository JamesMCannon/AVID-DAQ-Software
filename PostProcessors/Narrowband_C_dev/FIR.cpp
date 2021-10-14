
#include "FIR.h"

#include <assert.h>

FIR::FIR()
{
	m_filterTable = NULL;
	m_pastSum = NULL;
	m_filterLength = 0;
	m_filterOffset = 0;
	m_decimateLength = 1;
	m_filterCopy = true;
}

FIR::FIR(double* filter, int filterLength,
         int decimateLength, bool copyFilter)
{
	m_filterTable = NULL;
	m_pastSum = NULL;
	m_filterLength = 0;
	m_filterOffset = 0;
	m_decimateLength = 1;
	m_filterCopy = true;
	Create(filter, filterLength, decimateLength, copyFilter);
}


FIR::~FIR()
{
	Destroy();
}


bool FIR::IsCreated()
{
	return(m_filterTable != NULL);
}

void FIR::Create(double* filter, int filterLength,
                 int decimateLength, bool copyFilter)
{
	int temp;

	if ((filter == NULL) || (filterLength == 0))
		return;
	if (m_filterTable != NULL)
		return;   // Must call FIR::Destroy before a new
                                // filter can be created.
	m_filterLength = filterLength;
	m_decimateLength = decimateLength;
	m_filterCopy = copyFilter;
	m_filterOffset = 0;
	if (m_filterCopy)
	{
		m_filterTable = new double[m_filterLength];
		if (m_filterTable == NULL)
		{
			Destroy();
			return;
		}
		memcpy(m_filterTable, filter, m_filterLength*sizeof(double));
	}
	else
	{
		m_filterTable = filter;
	}
	temp = m_filterLength / m_decimateLength + 1;
	m_pastSum = new double[temp];
	if (m_pastSum == NULL)
	{
		Destroy();
		return;
	}
	memset(m_pastSum,0,temp*sizeof(double));
}

void FIR::Destroy()
{
	if (m_pastSum != NULL)
	{
		delete[] m_pastSum;
		m_pastSum = NULL;
	}
	if (m_filterCopy)
	{
		if (m_filterTable != NULL)
		{	
			delete[] m_filterTable;
			m_filterTable = NULL;
		}
	}
	else
	{
		m_filterTable = NULL;
	}
	
	m_decimateLength = 1;
	m_filterCopy = true;
	m_filterLength = 0;
	m_filterOffset = 0;
}

double* FIR::GetFilterPointer(int* filterlength)
{
	*filterlength = m_filterLength;
	return(m_filterTable);
}


void FIR::Filter(double* output, int* outputLength,
                 double* input, unsigned int inputLength)
{
	unsigned int i,j,index;
	unsigned int offset1, offset2, offset3;

	if (m_filterTable == NULL)
		return;
	// Must take sum values from the past vector input
	index = 0;
	offset1 = (unsigned int)m_filterLength-1;
	for(i=(unsigned int)m_filterOffset; i<offset1; i+=(unsigned int)m_decimateLength)
	{
		output[index] = m_pastSum[index];
		offset2 = offset1-i;
		for(j=0; j<i+1; j++)
		{
			output[index] += input[j] * m_filterTable[offset2+j];
		}
		index++;
	}
	
	// Can filter the data from the current input
	for(; i<inputLength; i+=(unsigned int)m_decimateLength)
	{
		output[index] = (double)0.0;
		offset2 = i-(unsigned int)m_filterLength+1;
		for(j=0; j<(unsigned int)m_filterLength; j++)
		{
			output[index] += input[offset2+j] * m_filterTable[j];
		}
		index++;
	}
	m_filterOffset = (int)(i - inputLength);
	// Fill in the sum vector for next input sequence
	*outputLength = (int) index;
	index = 0;
	offset1 = (unsigned int)m_filterLength-1;
	offset3 = i;
	for(i=0; i<offset1; i+=(unsigned int)m_decimateLength)
	{
		m_pastSum[index] = (double)0.0;
		offset2 = offset3-offset1+i;
		for(j=0; j<offset1-i; j++)
		{
			m_pastSum[index] += input[offset2+j] * m_filterTable[j];
		}
		index++;
	}
}


void FIR::Filter(float* output, int* outputLength,
                 short* input, unsigned int inputLength)
{
	unsigned int i,j,index;
	unsigned int offset1, offset2, offset3;
	double tempdbl;

	if (m_filterTable == NULL)
		return;
	
	// Must take sum values from the past vector input
	index = 0;
	offset1 = (unsigned int)m_filterLength-1;
	for(i=(unsigned int)m_filterOffset; i<offset1; i+=(unsigned int)m_decimateLength)
	{
		tempdbl = m_pastSum[index];
		//output[index] = (float)(m_pastSum[index]);
		offset2 = offset1-i;
		for(j=0; j<i+1; j++)
		{
			tempdbl += ((double)(input[j])) * m_filterTable[offset2+j];
			//output[index] += (float)(((double)(input[j])) * m_filterTable[offset2+j]);
		}
		output[index] = (float) tempdbl;
		index++;
	}
	// Can filter the data from the current input

	for(; i<inputLength; i+=(unsigned int)m_decimateLength)
	{
		tempdbl = 0.0;
		//output[index] = (float)0.0;
		offset2 = i-(unsigned int)m_filterLength+1;
		for(j=0; j<(unsigned int)m_filterLength; j++)
		{
			tempdbl += ((double)(input[offset2+j])) * m_filterTable[j];
			//output[index] += (float)(((double)(input[offset2+j])) * m_filterTable[j]);
		}
		output[index] = (float) tempdbl;
		index++;
	}
	m_filterOffset = (int)(i - inputLength);

	// Fill in the sum vector for next input sequence
	*outputLength = (int) index;
	index = 0;
	offset1 = (unsigned int)m_filterLength-1;
	offset3 = i;
	for(i=0; i<offset1; i+=(unsigned int)m_decimateLength)
	{
		m_pastSum[index] = (double)0.0;
		offset2 = offset3-offset1+i;
		for(j=0; j<offset1-i; j++)
		{
			m_pastSum[index] += ((double)(input[offset2+j])) * m_filterTable[j];
		}
		index++;
	}
}


void FIR::Reset()
{
	int temp = m_filterLength / m_decimateLength + 1;
	
	if (m_filterTable == NULL)
		return;
	
	memset(m_pastSum,0,temp*sizeof(double));
	m_filterOffset = 0;
}
