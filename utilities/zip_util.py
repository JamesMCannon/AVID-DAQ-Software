import zipfile
import glob
import os


def addFolderToZip(myZipFile,folder):

    folder = folder.encode('ascii') #convert path to ascii for ZipFile Method
    for file in glob.glob(folder+"/*"):
            if os.path.isfile(file):
                print file
                myZipFile.write(file, file, zipfile.ZIP_DEFLATED)
            elif os.path.isdir(file):
                addFolderToZip(myZipFile,file)

def createZipFile(zipFilename,files,folders):

    if not isinstance(files,list):
        files = [files]
    if not isinstance(folders,list):
        folders = [folders]

    myZipFile = zipfile.ZipFile( zipFilename, "w" ) # Open the zip file for writing
    for file in files:
        if len(file)==0:
            continue
        file = file.encode('ascii') #convert path to ascii for ZipFile Method
        if os.path.isfile(file):
            myZipFile.write( file, file, zipfile.ZIP_DEFLATED )

    for folder in  folders:
        if len(folder)==0:
            continue
        addFolderToZip(myZipFile,folder)
    myZipFile.close()
    return (1,zipFilename)