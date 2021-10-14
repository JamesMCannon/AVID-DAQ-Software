///////////////////////////////////////////////////////////////////////////////
//
// MSK.CPP - Computes the best fit MSK signal.
//

#include "MSK.h"



///////////////////////////////////////////////////////////////////////////////
//
// Static helper functions
//

static double mod(double mod_this, double by_this)
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


static void wrap(double* out, double* phase, int length)
{
	int i;

	assert(out != NULL);
	assert(phase != NULL);
	assert(length >= 0);

	if (length != 0)
	{
		for(i=0;i<length;i++)
		{
			out[i] = mod(phase[i],(2.0*PI));
			if (out[i] >= PI)
				out[i] -= 2.0*PI;
		}
	}
}

static void unwrap(double* out, double* phase, int length)
{
	double	dphase;
	int		tally;
	int		i;
	double one_behind;

	assert(out != NULL);
	assert(phase != NULL);
	assert(length > 0);

	out[0] = phase[0];
	tally = 0;
	one_behind = phase[0];

	for (i = 1; i < length; i++)
	{
		dphase = phase[i] - one_behind;
		if (dphase > PI)
		{
			tally--;
		}
		else if (dphase < -PI)
		{
			tally++;
		}
		one_behind = phase[i];
		out[i] = phase[i] + 2.0*PI*((double)tally);
	}

	return;
}

static int comparefn(const void *i, const void *j)
{
	// Using qsort, this function will sort in ascending order
	double* k;
	double* l;

	k = (double*) i;
	l = (double*) j;

	if (*k > *l)
		return (1);
	if (*k < *l)
		return (-1);
	return (0);
}     

///////////////////////////////////////////////////////////////////////////////
//
// Constructor
//

MSK::MSK()
{
	m_created = false;
    Create(5);
}

MSK::MSK(int samples_per_bit)
{
	m_created = false;
    Create(samples_per_bit);
}

///////////////////////////////////////////////////////////////////////////////
//
// Create() - Initializes the state of an MSK object
//

void MSK::Create(int samples_per_bit)
{
	m_samples_per_bit = samples_per_bit;
	if (m_samples_per_bit < MIN_SAMPLES_PER_BIT)
		m_samples_per_bit = MIN_SAMPLES_PER_BIT;
	if (m_samples_per_bit > MAX_SAMPLES_PER_BIT)
		m_samples_per_bit = MAX_SAMPLES_PER_BIT;
	m_phase_per_sample = PI/2.0/((double)m_samples_per_bit);
	m_PastLength = 0;
	m_last_phase_sample = 0.0;
	m_PastSavedLength = 0;
	
	memset(m_SavedTrellisRCV, 0, 3*MAX_SAMPLES_PER_BIT*sizeof(double));
	memset(m_BufTrellisRCV, 0, MAX_INPUT_LENGTH*sizeof(double));
	m_created = true;
	m_last_BTT_set = false;
	m_last_BTT = 0.0;
	m_accumulated_offset = 0;
}

///////////////////////////////////////////////////////////////////////////////
//
// Destructor
//

MSK::~MSK()
{
   Destroy();
}

///////////////////////////////////////////////////////////////////////////////
//
// Destroy() - Destroys the state of an MSK object.
//

void MSK::Destroy()
{
	if (m_created)
	{
		memset(m_SavedTrellisRCV, 0, 3*MAX_SAMPLES_PER_BIT*sizeof(double));
		memset(m_BufTrellisRCV, 0, MAX_INPUT_LENGTH*sizeof(double));
		m_created = false;
	}
}

///////////////////////////////////////////////////////////////////////////////
//
// FitCurve() - Fits the input signal with the best ideal MSK signal.
//

int MSK::FitCurve
(
	double* OutTrellisTXT,	// Ideal MSK signal Trellis
	int*	OutLength,		// Ideal MSK signal Length.
	double* OutTrellisRCV,	// Received MSK signal Trellis.
	double*	InReal,			// Received baseband MSK signal (Real part).
	double*	InImag,			// Received baseband MSK signal (Imag part).
	int		InLength		// Received baseband MSK signal length.
)
{
	int ProcessLength;
	int num_processed;
	
	if (m_created)
	{
		// Before we start, let's make sure that our buffer lengths are
		// large enough to handle this amount of new data.
		assert((InLength + m_PastLength) <= MAX_INPUT_LENGTH);

		// Matlab Equivalent: OutTrellisRCV = atan2(Imag,Real);
		GetWrappedTrellis(OutTrellisRCV, InReal, InImag, InLength);

		// This is the output length -- right now we set it to 0.
		(*OutLength) = 0;

		// Changed 10/1/05
		if (m_PastSavedLength > 0)
		{
			//Handle the rest of the last second's of data.
			wrap(m_SavedTrellisRCV, m_SavedTrellisRCV, m_PastSavedLength);
			memcpy(&(m_SavedTrellisRCV[m_PastSavedLength]), OutTrellisRCV, m_samples_per_bit*sizeof(double));
			unwrap(m_SavedTrellisRCV, m_SavedTrellisRCV, m_PastSavedLength+m_samples_per_bit);
			num_processed = FinishIdealTrellis(OutTrellisTXT, m_PastSavedLength);
		    (*OutLength) += num_processed;//should be m_PastSavedLength
		}

		// We are going to take what is left over from the last second of data
		// and add the new data to the end of it.
		ProcessLength = InLength + m_PastLength;
		
		// The left over samples may be unwrapped, so let's wrap them back to -pi to pi.
		wrap(m_BufTrellisRCV, m_BufTrellisRCV, m_PastLength);
		
		// Now we concatenate the new data onto the end of our buffer
		memcpy(&m_BufTrellisRCV[m_PastLength], OutTrellisRCV, InLength*sizeof(double));

		// Unwrap the trellis for processing
		unwrap(m_BufTrellisRCV, m_BufTrellisRCV, ProcessLength);

		//Calculate the BTT for this second of data.
		CalculateBTT(&(m_BufTrellisRCV[m_PastLength]), InLength);
		// After this calculation, we have the exact BTT, the Max Phase Difference Bit, and the Min Phase Difference Bit
		// We use the BTT for sub-sample accuracy.  We use the Max Phase Difference Bit to calculate the bits.
		// The Min Phase Difference Bit is the phase sample on the trellis that behaves most ideally.  We should use it to
		// calculate the output phase.

		num_processed = GetIdealTrellis(&OutTrellisTXT[(*OutLength)], InLength);
	    (*OutLength) += num_processed; // num_processed should be <= InLength
		
		// Calculate the number of samples left over -- these will be processed with the next second of data.
		m_PastSavedLength = InLength - num_processed;

		// Update the buffer so that the left over samples are at the beginning.
		memcpy(m_SavedTrellisRCV, &m_BufTrellisRCV[num_processed+m_PastLength], m_PastSavedLength*sizeof(*m_SavedTrellisRCV));
		memmove(m_BufTrellisRCV, &m_BufTrellisRCV[ProcessLength-2*MAX_SAMPLES_PER_BIT], 2*MAX_SAMPLES_PER_BIT*sizeof(*m_BufTrellisRCV));
		m_PastLength = 2*MAX_SAMPLES_PER_BIT;
	}

	return 0;
}



/////////////////////////////////////////////////////////////////////////////////////////////
/////////////////////////  ROBB"S ADDITIONS /////////////////////////////////////////////////
/////////////////////////////////////////////////////////////////////////////////////////////


void MSK::GetWrappedTrellis(double* out, double* real,double* imag, int length)
{
	int		i;

	assert(out != NULL);
	assert(real != NULL);
	assert(imag != NULL);
	assert(length > 0);

	for(i = 0; i < length; i++)
	{
		out[i] = atan2(imag[i],real[i]);
	}
	return;
}


///////////////////////////////////////////////////////////
///// WRAP/UNWRAP SECTION /////////////////////////////////
///////////////////////////////////////////////////////////


int MSK::Reset()
{
	m_PastLength = 0;
	m_last_phase_sample = 0.0;
	m_PastSavedLength = 0;
	
	memset(m_SavedTrellisRCV, 0, 3*MAX_SAMPLES_PER_BIT*sizeof(double));
	memset(m_BufTrellisRCV, 0, MAX_INPUT_LENGTH*sizeof(double));
	m_last_BTT_set = false;
	m_last_BTT = 0.0;
	m_accumulated_offset = 0;
	m_created = true;

	return 0;
}

//Now assumes the input is wrapped




///////////////////////////////////////////////////////////
///// GET TRANSITION SECTION //////////////////////////////
///////////////////////////////////////////////////////////
void MSK::CalculateBTT(double* unwrapped, int length)
{
	// Here we impose some limits -- I don't like mallocing in real-time
	// So we set a max baud rate of 333.333 Hz and a min baud rate of 25 Hz.
	// These values affect the length of the buffers used here.
	// So now we set the min samples per bit to 3, and the max to 40.

	int i, j, diff_index;
	double diffph[MAX_DIFF_LENGTH];
	double sum[MAX_SAMPLES_PER_BIT];
	double min_bit, max_bit, second_min_bit;
	int min_bit_index, max_bit_index, second_min_bit_index;
	int center_index;
	double median1, median2, av_val, BTT;

	if (unwrapped == NULL)
		return;
	if (length <= 0)
		return;
	
	memset(diffph, 0, MAX_DIFF_LENGTH*sizeof(double));
	memset(sum, 0, MAX_SAMPLES_PER_BIT*sizeof(double));

	for(i = 0; i < m_samples_per_bit; i++)
	{
		diff_index = 0;
		for(j = i; j < length-m_samples_per_bit; j += m_samples_per_bit)
		{
			diffph[diff_index] = unwrapped[j+m_samples_per_bit] - unwrapped[j];
			if (diffph[diff_index] < 0)
				diffph[diff_index] = -diffph[diff_index];
			diff_index++;
		}
		qsort((char*) diffph, diff_index, sizeof(double), comparefn);

		for(j = 0; j < (diff_index/2); j++)
			sum[i] = sum[i] + diffph[j];
		sum[i] = sum[i]/((double)(diff_index/2));
	}

	min_bit_index = 0;
	min_bit = sum[0];
	max_bit_index = 0;
	max_bit = sum[0];
	for(i = 1; i < m_samples_per_bit; i++)
	{
		if (sum[i] > max_bit)
		{
			max_bit_index = i;
			max_bit = sum[i];
		}
		if (sum[i] < min_bit)
		{
			min_bit_index = i;
			min_bit = sum[i];
		}
	}

	sum[min_bit_index] = sum[max_bit_index];
	second_min_bit_index = 0;
	second_min_bit = sum[0];
	for(i = 1; i < m_samples_per_bit; i++)
	{
		if (sum[i] < second_min_bit)
		{
			second_min_bit_index = i;
			second_min_bit = sum[i];
		}
	}
	
	i = min_bit_index;
	diff_index = 0;
	for(j = i; j < length-m_samples_per_bit; j += m_samples_per_bit)
	{
		diffph[diff_index] = unwrapped[j+m_samples_per_bit] - unwrapped[j];
		diff_index++;
	}
	qsort((char*) diffph, diff_index, sizeof(double), comparefn);

	//find the first element greater than 0.
	center_index = -1;
	for(i = 0; i < diff_index; i++)
	{
		if (diffph[i] > 0)
		{
			center_index = i;
			break;
		}
	}
	if (center_index == -1)
	{
		median1 = diffph[(int)(((double)diff_index)*3.0/8.0)];
		median2 = diffph[(int)(((double)diff_index)*5.0/8.0)];
	}
	else
	{
		median1 = diffph[(int)(((double)center_index)*3.0/4.0)];
		median2 = diffph[center_index+(int)(((double)(diff_index-center_index))/4.0)];
	}

	if (median1 < 0)
		median1 = -median1;
	if (median2 < 0)
		median2 = -median2;

	av_val = (median1+median2)/4.0/m_phase_per_sample;
	BTT = ((double)min_bit_index)+((double)m_samples_per_bit)/2.0;

	//Even number of samples per bit
	if (second_min_bit_index-min_bit_index == 1)
		BTT += av_val;
	else if (second_min_bit_index-min_bit_index == -1)
		BTT -= av_val;
	else if (second_min_bit_index-min_bit_index == m_samples_per_bit-1)
		BTT -= av_val;
	else
		BTT += av_val;

	m_BTT = mod(BTT,(double)m_samples_per_bit);
	// BTT Calculation is now COMPLETE
	
	//max_bit_index is expected to be equal to mod(round(BTT),5)
	if (m_BTT-(double)((int)m_BTT) > 0.5)
		m_max_bit_index = (int)(m_BTT+1.0);
	else
		m_max_bit_index = (int)m_BTT;
	if (m_max_bit_index >= m_samples_per_bit)
		m_max_bit_index -= m_samples_per_bit;
	//assert(max_bit_index == m_max_bit_index);
	m_min_bit_index = min_bit_index;

	double temp1;
	temp1 = mod(m_BTT-(double)m_PastLength,(double)m_samples_per_bit);
/*	FILE* fid = fopen("BTTNew.txt","ab");
	fwrite(&temp1,sizeof(double),1,fid);
	fwrite(&m_BTT,sizeof(double),1,fid);
	fclose(fid);
*/
}      




///////////////////////////////////////////////////////////
/////// GET IDEAL SECTION /////////////////////////////////
///////////////////////////////////////////////////////////


int MSK::GetIdealTrellis(double* out, int process_length)
{
	double end_phase, start_phase;
	int start_index;
	double current_phase;
	int out_index;
	double diffph;
	double slope;
	int i, j;
	double offset;
	bool first_BTT_set;
	double min1;
	
	assert(out != NULL);
	if (process_length <= 0)
		return(0);
	
	end_phase = 2.0*m_phase_per_sample*(m_BTT-(double)((int)m_BTT));
	start_phase = 2.0*m_phase_per_sample-end_phase;

	if (m_BTT - (double)((int)m_BTT) > 0.5)
		start_index = m_max_bit_index;
	else
		start_index = m_max_bit_index+1;

	first_BTT_set = false;
	offset = 0.0;
	current_phase = 0.0;
	out_index = 0;
	if (start_index > 0)
	{
		if (m_PastLength+m_max_bit_index-m_samples_per_bit < 0)
		{
			// Calculate phase for the "first" bit (incomplete bit)
			if (start_index == 1)
			{
				diffph = m_BufTrellisRCV[m_PastLength+1] - m_BufTrellisRCV[0];
				slope = (diffph > 0.0)? 1.0 : -1.0;
				out[out_index] = 0.0;
				out_index++;
				if (slope > 0.0)
				{
					if (-end_phase+start_phase > 0.0)
						current_phase = -end_phase;
					else
						current_phase = end_phase;
				}
				else
				{
					if (-end_phase+start_phase < 0.0)
						current_phase = -end_phase;
					else
						current_phase = end_phase;
				}
				// This is the phase at the first BTT.  We want this to be 0.
				offset = -current_phase;
				first_BTT_set = true;
			}
			else
			{
				diffph = m_BufTrellisRCV[m_PastLength+m_max_bit_index] - m_BufTrellisRCV[0];
				slope = (diffph > 0.0)? 1.0 : -1.0;
				out[out_index] = 0.0;
				out_index++;
				for (i = 1; i < start_index; i++)
				{
					out[out_index] = out[out_index-1] + slope*2.0*m_phase_per_sample;
					out_index++;
				}
				current_phase = out[out_index-1] + slope*end_phase;
				// This is the phase at the first BTT.  We want this to be 0.
				offset = -current_phase;
				first_BTT_set = true;
			}
		}
		else
		{
			// Calculate phase for the "first" bit (incomplete bit)
			diffph = m_BufTrellisRCV[m_PastLength+m_max_bit_index] - m_BufTrellisRCV[m_PastLength+m_max_bit_index-m_samples_per_bit];
			slope = (diffph > 0.0)? 1.0 : -1.0;
			out[out_index] = 0.0;
			out_index++;
			for (i = 1; i < start_index; i++)
			{
				out[out_index] = out[out_index-1] + slope*2.0*m_phase_per_sample;
				out_index++;
			}
			current_phase = out[out_index-1] + slope*end_phase;
			// This is the phase at the first BTT.  We want this to be 0.
			offset = -current_phase;
			first_BTT_set = true;
		}
	}

	for (i = m_PastLength+m_max_bit_index; i < m_PastLength+process_length-m_samples_per_bit; i += m_samples_per_bit)
	{
		diffph = m_BufTrellisRCV[i+m_samples_per_bit] - m_BufTrellisRCV[i];
		slope = (diffph > 0)? 1.0 : -1.0;
		out[out_index] = current_phase + slope*start_phase;
		out_index++;
		for (j = 1; j < m_samples_per_bit; j++)
		{
			out[out_index] = out[out_index-1] + slope*2.0*m_phase_per_sample;
			out_index++;
		}
		current_phase = out[out_index-1] + slope*end_phase;
		if (!first_BTT_set)
		{
			// This is the phase at the first BTT.  We want this to be 0.
			offset = -(current_phase);
			first_BTT_set = true;
		}
	}

	if (m_last_BTT_set)
	{
		min1 = m_BTT-m_last_BTT;
		if (min1 < 0) min1 = -min1;
		if (min1 > ((double)m_samples_per_bit)/2.0)
			m_accumulated_offset++;
	}
	m_accumulated_offset %= 2;

	m_last_BTT = m_BTT;
	m_last_BTT_set = true;
	offset += ((double)m_accumulated_offset)*PI;

	// We are done calculating the trellis.

	for (i = 0; i < out_index; i++)
		out[i] += offset;
	current_phase += offset;

	m_last_phase_sample = mod(current_phase, 2.0*PI);
	if (m_last_phase_sample >= PI)
		m_last_phase_sample -= 2.0*PI;

/*	FILE* fid = fopen("RobbNew.txt","ab");
	fwrite(out,sizeof(double),out_index,fid);
	fclose(fid);

	fid = fopen("RobbNewIn.txt","ab");
	fwrite(&(m_BufTrellisRCV[m_PastLength]),sizeof(double),out_index,fid);
	fclose(fid);

	fid = fopen("RobbOffset.txt","ab");
	fwrite(&offset,sizeof(double),1,fid);
	fclose(fid);
*/
	return(out_index);
}

int MSK::FinishIdealTrellis(double* out, int process_length)
{
	double end_phase, start_phase;
	double diffph;
	double slope;
	int i;

	assert(out != NULL);
	if (process_length <= 0)
		return(0);

	// This calculation uses the LAST SECOND's Values of BTT etc.!  Be careful!
	end_phase = 2.0*m_phase_per_sample*(m_BTT-(double)((int)m_BTT));
	start_phase = 2.0*m_phase_per_sample-end_phase;
	
	diffph = m_SavedTrellisRCV[m_samples_per_bit] - m_SavedTrellisRCV[0];
	slope = (diffph > 0.0)? 1.0 : -1.0;
	out[0] = m_last_phase_sample+slope*start_phase;
	for (i = 1; i < process_length; i++)
	{
		out[i] = out[i-1] + slope*2.0*m_phase_per_sample;
	}
	
/*	FILE* fid = fopen("RobbNew.txt","ab");
	fwrite(out,sizeof(double),process_length,fid);
	fclose(fid);

	fid = fopen("RobbNewIn.txt","ab");
	fwrite(m_SavedTrellisRCV,sizeof(double),process_length,fid);
	fclose(fid);
*/
	m_last_phase_sample = mod(out[i-1], 2.0*PI);
	if (m_last_phase_sample >= PI)
		m_last_phase_sample -= 2.0*PI;

	return(process_length);
}
