'''libraries for saving and loading data from disk'''
import os

def ensurePath(path,force=False):
    '''Verify path exists, raises error if path exists and force=false.
    Path and directories will be created if they don't exist.
    Returns created path'''
    if os.path.exists(path) and not force:
        raise IOError('path already exists, use force=True to overwrite')
    directory,filename=os.path.split(path)
    if not os.path.exists(directory):
        #some remote filers may need a 'three strikes' test here using sleep()
        os.makedirs(directory)
    return path

