# Copyright (c) 2013, Joerg Raedler (Berlin, Germany)
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
    import netCDF4 as nc
except:
    nc = None

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
    """Export DyMat data to a netCDF file using netCDF4"""

    if nc is None:
      raise Exception("netCDF4 support not found - please install python-netCDF4!")

    if not fileName:
        fileName = dm.fileName+'.nc'

    ncFile = nc.Dataset(fileName, 'w')
    ncFile.comment = 'file generated with DyMat from %s' % dm.fileName

    convertNames = formatOptions.get('convertNames', False)

    if convertNames:
        nameConv = NameConverter()
    
    vList = dm.sortByBlocks(varList)
    for block in vList:
        a, aname, adesc = dm.abscissa(block)
        dim = '%s_%02i' % (aname, block)
        ncFile.createDimension(dim, a.shape[0])
        av = ncFile.createVariable(dim, 'd', (dim,))
        av.description = adesc
        av.block = block
        av[:] = a
        for vn in vList[block]:
            if convertNames:
                name = nameConv(vn)
            else:
                name = vn
            v = ncFile.createVariable(name, 'd', (dim,))
            d = dm.description(vn)
            if d:
                v.description = d
            if convertNames:
                v.original_name = vn
            v.block = block
            v[:] = dm.data(vn)
    ncFile.sync()
    ncFile.close()
