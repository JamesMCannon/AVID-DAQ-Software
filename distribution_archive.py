"""
Archives project

Saves source files and compiled distribution
"""
import os,shutil

distro_archive_folder = '../../distro_archive'

#specific files to copy:
files = ['../../Builds/python_daq.zip','../../Builds/python_daq.tar.bz2']

#entire folders to copy:
dirs = ['../../src']

#folder and file suffixes to delete after copy:
ignore_flags = ['.svn','.pyc','.mat','.log']


from __ver__ import __ver__

archive_folder = os.path.join(distro_archive_folder,__ver__)

if os.path.isdir(archive_folder):
    raise 'Distribution archive %s alread exists' % archive_folder
else:
    print 'Saving archive to %s ...' % archive_folder
    os.makedirs(archive_folder)

for afile in files:
    if os.path.isfile(afile):
        write_name = os.path.split(afile)[-1]
        shutil.copyfile(afile,os.path.join(archive_folder,write_name))
    else:
        print 'File dne: %s' % afile

for adir in dirs:
    if os.path.isdir(adir):
        write_name = os.path.split(adir)[-1]
        shutil.copytree(adir,os.path.join(archive_folder,write_name))
    else:
        print 'Folder dne: %s' % adir



for root, dirs, files in os.walk(archive_folder, topdown=False):
    for name in files:
        for ignore in ignore_flags:
            if (root.rfind(ignore)>-1) or (name.rfind(ignore)>-1):
##                print 'Removing file %s' % os.path.join(root,name)
                try:
                    os.remove(os.path.join(root, name))
                except:
                    pass

    for name in dirs:
        for ignore in ignore_flags:
            if name.endswith(ignore) or (root.rfind(ignore)>-1):
##                print 'Removing dir %s' % os.path.join(root,name)
                try:
                    os.rmdir(os.path.join(root, name))
                except:
                    pass

print 'Finished archiving version %s' % __ver__