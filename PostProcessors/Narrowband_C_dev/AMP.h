// AMP.h: interface for the AMP class.
//
//////////////////////////////////////////////////////////////////////

#if !defined(AFX_AMP_H__E8B26D0F_0DEB_49C7_BD89_1C9F83D2FE64__INCLUDED_)
#define AFX_AMP_H__E8B26D0F_0DEB_49C7_BD89_1C9F83D2FE64__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

const int AMP_MAX_LENGTH = 1010 + 1000;

class AMP {
   	
  public:
    
    AMP();
	void Create();
    void GetAmp(float * output, int* outputLength, double* realRCV, double* imagRCV, int lengthRCV, int resolution, double ScaleFactor);
    ~AMP();
	void Reset();

	void Destroy();

  private:
    
  	double m_fRealRCV[AMP_MAX_LENGTH]; 
    double m_fImagRCV[AMP_MAX_LENGTH];
    int m_nOutRCV; 
};


#endif // !defined(AFX_AMP_H__E8B26D0F_0DEB_49C7_BD89_1C9F83D2FE64__INCLUDED_)
