
import sys, os
#packages which define __version__:
packages = ['numpy','matplotlib','scipy','processing','wx',
            'paramiko','Crypto','setuptools']

if os.name == 'nt':
    packages.append('mpl_toolkits.basemap')

#some packages do not define __version__:
special_packages = [('serial','VERSION'),
                    ('bbfreeze','version'),
                    ('Image','VERSION')]


if os.name=='nt':
    special_packages.append(('elementtree.ElementTree','VERSION'))
else:
    special_packages.append(('xml.etree.ElementTree','VERSION'))

def save_version_numbers(filename):
    """
    Save version number of packages to filename
    """

    fid = open(filename,'w')
    fid.write('Python %s' % sys.version)
    fid.write('\n\n%-15s: %s\n\n'% ('Package name','version'))
    for package in packages:
        module = __import__(package, fromlist=['__version__'])
        fid.write('%-15s: %-15s\n' %(package,module.__version__))


    for package,version in special_packages:
        module = __import__(package, fromlist=[version])
        fid.write('%-15s: %-15s\n' %(package,eval('module.%s'%version)))

    fid.close()

if __name__ == '__main__':
    save_version_numbers('../../../documentation/package_versions.txt')