///////////////////////////////////////////////////////////////////////////////
//
// PHASE.H - Interface file for the PHASE class.
//

#ifndef _PHASE_H_
#define _PHASE_H_

///////////////////////////////////////////////////////////////////////////////
//
// Constants.
//

//const int    PHASE_MAX_AVERAGE_LENGTH     = 1000;
//const int    PHASE_MAX_LENGTH             = 1080 + PHASE_MAX_AVERAGE_LENGTH;
//const double PHASE_BIT_ERROR = 4.11;
#define PHASE_MAX_AVERAGE_LENGTH      1000
#define PHASE_MAX_LENGTH             (1080 + PHASE_MAX_AVERAGE_LENGTH)
#define PHASE_BIT_ERROR  4.11

///////////////////////////////////////////////////////////////////////////////
//
// PHASE Class
//

class PHASE
{
public:
    
    PHASE();

	int Create();
	void Reset();

    void GetMSKPhase
    (
    float*  Output,
    int*    OutputLength,
	double* TrellisTXT,
    int     LengthTXT,
    double*  RealRCV,
    double*  ImagRCV,
    int     LengthRCV,
	int		AverageLength
	);

    void GetCWPhase
    (
    float*  Output,
    int*    OutputLength,
    double*  RealRCV,
    double*  ImagRCV,
    int     LengthRCV,
	int		AverageLength
	);


private:
	void unwrap(double* out, double* phase, int length);
    double mod(double mod_this, double by_this);

    double	m_RealRCV[PHASE_MAX_LENGTH];
    double	m_ImagRCV[PHASE_MAX_LENGTH];
	double 	m_TrellisTXT[PHASE_MAX_LENGTH];
	
    int     m_OutRCV;
    int     m_OutTXT;
	double	m_last_phase_value;
	int		m_tally;
};

#endif



