# Copyright (c) 2012, Joerg Raedler (Berlin, Germany)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
# Redistributions of source code must retain the above copyright notice, this list
# of conditions and the following disclaimer. Redistributions in binary form must
# reproduce the above copyright notice, this list of conditions and the following
# disclaimer in the documentation and/or other materials provided with the
# distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

try:
    import h5py
except:
    h5py = None

import string


class NameConverter:
    allow0 = string.ascii_letters + string.digits + '_'
    allow  = allow0 + '@+-.'
    repl   = '_'
    
    def __init__(self):
        self.used_names = []
        
    def __call__(self, name):
        n = list(name)
        if not n[0] in self.allow0:
            n.insert(self.repl, 0)
        for i in range(1, len(n)):
            if not n[i] in self.allow:
                n[i] = self.repl
        s = ''.join(n)
        while s in self.used_names:
            s += '_'
        self.used_names.append(s)
        return s

    
def export(dm, varList, fileName=None, formatOptions={}):
    """Export DyMat data to a HDF5 file"""

    if h5py is None:
      raise Exception("HDF5 support not found - please install h5py!")

    if not fileName:
        fileName = dm.fileName+'.hdf5'

    h5File = h5py.File(fileName, 'w')
    h5File.attrs['comment'] = 'file generated with DyMat from %s' % dm.fileName

    convertNames = formatOptions.get('convertNames', False)

    if convertNames:
        nameConv = NameConverter()
    
    vList = dm.sortByBlocks(varList)
    for block in vList:
        a, aname, adesc = dm.abscissa(block)
        dim = '%s_%02i' % (aname, block)
        av = h5File.create_dataset(dim, data=a)
        av.attrs['description'] = str(adesc)
        av.attrs['block'] = block
        for vn in vList[block]:
            if convertNames:
                name = nameConv(vn)
            else:
                name = vn
            v = h5File.create_dataset(name, data=dm.data(vn))
            d = dm.description(vn)
            if d:
                v.attrs['description'] = str(d)
            if convertNames:
                v.attrs['original_name'] = str(vn)
            v.attrs['block'] = block
    h5File.close()
