# LF DAQ Distro, CU updated version
# Austin Sousa
# 6.24.2018
# austin.sousa@colorado.edu


Hey! Here's a few notes about this version of the LF-DAQ distribution.

----- To run the DAQ: -----
- To run it from the bare python, use "run_main.bat"

- "run_main.bat" automatically builds the daqSettings xml file, using "Default_LF_settings.txt"
- "run_calibration.bat" builds settings from "LF_calibration_settings.txt". It's configured to
	save 1-minute broadband files in the "Calibration Data/Continuous" directory.

----- To build a standalone DAQ: -----
- To build a standalone version, run "build.bat"
	- A new version of the distro will be packed up into the "Builds" directory.

----- Some new settings: -----
- copy_to_external:
	- if active=1, data will be stored in data_root on the internal drive
	- every 30 minutes, completed files will be moved to the external drive.
	- external_drive is a comma-separated list of external drives to use:
		external_drive=D:\,E:\,F:\
	- the DAQ software will cycle through this list, using the first drive until it's full,
		then moving on to the next, and so forth.

- copy_to_dropbox:
	- The intent of this module is to copy current spectrograms and the log file to dropbox,
		so it can be monitored remotely (without having to use the Stanford SSH server)
	- The transfer occurs every copy_period seconds
	- if tail_only=0, the entire log file will be copied to dropbox
	- if tail_only=1, only the last ~50 lines will be copied over, to save on bandwidth.
		(the log files can get huge)

- ErrorEmail:
	- Same as before -- every time the daq throws a major error, it'll send an email.
	- the email settings are brought out into the config file

- ErrorPost:
	- This *probably* works, but I haven't tested it since I can't get at the
	 old Stanford servers anymore.

----- To perform a calibration: ----
	- Start the DAQ using "run_calibration.bat"
	- wait until you're taking data within a full-sized file (e.g., wait until the time is at :00:00)
	- Push the caltone button on the preamp box, and hold it for ~10 seconds.
	- quit the DAQ
	- run the calibration script: 
		- open the Anaconda terminal
		- run "calibrate_LF.py <one of the data files with the caltone in it>"
			python calibrate_LF.py "Calibration Data/Continuous/R118062312000_000.mat"

		- The script will ask you some details about the antenna:
			- Square or triangle
			- wire AWG
			- number of turns
			- baseline, in centimeters.

			For RELAMPAGO, we're using:
				triangle
				16 AWG
				13 turns
				260 cm baseline

		- If it all went right, four plots will pop up, showing:
			- CalibrationResponse: 	The frequency response 
			- CalibrationNumber: 	The scaling factor (pT per amplitude division in sampling)
			- ResponseRatio: 		The matching ratio between the two channels
			- NoiseResponse: 		The frequency spectrum of the noise floor

			- The computed calibration curves are stored in CalibrationVariables.mat

		- That's it! Close the plots; everything automatically saves in the LF-DAQ root directory.

