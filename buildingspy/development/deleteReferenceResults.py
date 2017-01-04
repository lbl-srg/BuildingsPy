# Python script for deleting reference results prior to execution of BuildingsPy

import os
import re

def recursive_glob(rootdir='.', suffix=''):
    return [os.path.join(rootdir, filename) for rootdir, dirnames, 
            filenames in os.walk(rootdir) for filename in filenames 
            if ( filename.endswith(suffix) 
                 and ("ConvertBuildings_from" not in filename)) ]


txt_files = recursive_glob('../Buildings/Resources/ReferenceResults/Dymola', '.txt')

def delete_reference(filPat):
    n_files=0
    for itr in filPat:
        n_files=n_files+1
        os.remove(itr)
    return n_files

# Number of .txt files
N_txt_files = len(txt_files)

if __name__ == "__main__":
    
    n_ref_files = delete_reference (txt_files)
    assert N_txt_files-n_ref_files == 0, "The number of .txt files deleted does not match the number of .txt found."

