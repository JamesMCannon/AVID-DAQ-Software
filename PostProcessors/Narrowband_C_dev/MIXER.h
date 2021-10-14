// MIXER.h: interface for the MIXER class.
//
//////////////////////////////////////////////////////////////////////

#if !defined(AFX_MIXER_H__B29FEED4_E1FF_4A21_8AEF_4E10E3805ABD__INCLUDED_)
#define AFX_MIXER_H__B29FEED4_E1FF_4A21_8AEF_4E10E3805ABD__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

// Class: MIXER
// ------------
// This class implements a signal processing mixer.  It has the capability of
// mixing a signal with a sin and cos waveform and also filtering a signal.
// A continuous digital data stream can be feed into the mixer by breaking it
// up into individual segments.  The mixer will hold necessary information
// from previous data segments to complete all current calculations.

// Written by Jeffrey DiCarlo  2-6-97
// Edited by Nicholas LaVassar 1-5-10

//const int MIXER_MAX_LENGTH = 100000;
//#define MIXER_MAX_LENGTH 100000

class MIXER {

  public:

    MIXER();
    MIXER(unsigned int frequency, double timeInterval,
          unsigned int mixerLengths, unsigned int phase, short channel_select);
    ~MIXER();
	void Reset();

	void Create(unsigned int frequency, double timeInterval,
		unsigned int mixerLengths, unsigned int phase, short channel_select);
    void Destroy();

    void MixDown(double* outReal, double* outImag,
                 double* input, unsigned int inputLength);  //changed input from short to double

  private:

    double* m_sinTable;
    double* m_cosTable;

    unsigned int m_mixerLength;
    unsigned int m_mixerOffset;
    int m_bCreated;
};

#endif // !defined(AFX_MIXER_H__B29FEED4_E1FF_4A21_8AEF_4E10E3805ABD__INCLUDED_)
