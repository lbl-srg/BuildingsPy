#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
class Plotter(object):
    """
       This class contains static methods that can be used to create plots.
       For an example of a simple plot, see also the example
       in :mod:`buildingspy.examples.dymola`.
    """

    def interpolate(tSup, t, y):
        """ Interpolate the values of ``(t,y)`` at the support points ``tSup``.

        :param tSup: Support points.
        :param t: Time stamps of variables ``y``.
        :param y: Function values at time stamps ``t``.
        :return: Interpolated values of ``varName`` at ``tSup``

        Usage: Type

           >>> import os
           >>> import numpy as np
           >>> import matplotlib
           >>> matplotlib.use('Agg')
           >>> import matplotlib.pyplot as plt
           >>>
           >>> from buildingspy.io.outputfile import Reader
           >>> from buildingspy.io.postprocess import Plotter
           >>>
           >>> resultFile = os.path.join("buildingspy", "examples", "dymola", "PlotDemo.mat")
           >>> r=Reader(resultFile, "dymola")
           >>> (t, y) = r.values('temSen.T')
           >>> tSup=np.linspace(0, 1.0, num=50)
           >>> TInt=Plotter.interpolate(tSup, t, y)
           >>> plt.plot(tSup, TInt) #doctest: +ELLIPSIS
           [<matplotlib.lines.Line2D object at ...>]
           >>> plt.show() # doctest: +SKIP

        """
        import numpy as np

        if ((np.isnan(tSup)).any()):
            raise ValueError('NaN in input argument tSup.')
        if ((np.isnan(t)).any()):
            raise ValueError('NaN in time values of data.')
        if ((np.isnan(y)).any()):
            raise ValueError('NaN in function values of data.')
        if len(t) != len(y):
            raise ValueError('len(t) = %d but len(y) = %d, they must be equal.' % (len(t), len(y)))
        # Numpy needs t to be strictly increasing, but Dymola may have the same time stamps
        # more than once.
        # If the last points are for the same time stamp, we remove them from the interpolation
        iMax = len(t) - 1
        maxT = max(t)
        dT = (maxT - min(t)) / float(iMax)
        while t[iMax] <= t[iMax - 1]:
            iMax = iMax - 1

        # Shift tNew slight in case of multiple equal entries.
        # Since the last entry was removed above, the final time is not going to change.
        tTol = 1E-4 * dT
        tInc = 10.0 * tTol

        tNew = list()
        yNew = list()
        tNew.append(t[0])
        yNew.append(y[0])
        for i in range(1, iMax):
            if t[i] > t[i - 1] + tTol:
                tNew.append(t[i])
                yNew.append(y[i])
            else:
                if t[i] != t[i - 1] and t[i - 1] + tInc < maxT:
                    if t[i - 1] + tInc < t[i + 1]:
                        tNew.append(t[i - 1] + tInc)
                        yNew.append(y[i])
        tNew.append(t[iMax])
        yNew.append(y[iMax])

        for i in range(1, len(tNew)):
            if tNew[i - 1] >= tNew[i]:
                raise ValueError('Time t is not strictly increasing.')
        for i in range(1, len(tSup)):
            if tSup[i] <= tSup[i - 1]:
                raise ValueError('Time tSup is not strictly increasing.')
        yI = np.interp(tSup, tNew, yNew)
        if ((np.isnan(yI)).any()):
            raise ValueError('NaN in interpolation.')

        return yI
    interpolate = staticmethod(interpolate)

    def convertToPeriodic(tPeriod, t, y):
        """Convert the data series ``(t, y)`` such that ``t`` is periodic
        with periodicity ``tPeriod``.

        :param tPeriod: Period to which ``t`` needs to be converted.
        :param t: Equally spaced, increasing vector of time, with ``t[0]=0``.
        :param y: Function values at support points ``t``.
        :return: Vectors ``(np.array(tP, y))`` where ``tP`` is periodic with period ``tPeriod``.

        The vector ``t`` must start at zero, be equally spaced and increasing.
        For example, ``t`` could be

            >>> import numpy as np
            >>> t=np.linspace(0, 86399, 86400)

        if ``t`` spans one year and the data are hourly (hence, ``t[0]=0`` and ``t[-1]=86399``).

        """
        import numpy as np

        # Check input
        if t[0] != 0:
            raise ValueError('t[0] must be zero. Received t[0] = ' + str(t[0]))
        if t[-1] < tPeriod:
            raise ValueError('t[-1] = %s, but tPeriod = %s. The array t must contain at least two periods.'
                             % (t[-1], tPeriod))
        # n is the index of the last element before the vector is looped
        n = -1
        for ele in t:
            if abs(ele - tPeriod) < 1E-20:
                break
            n = n + 1
        if n + 1 == len(t):
            raise ValueError('tPeriod is not within t[0] and t[len(t)-1].\n' +
                             "   Received tPeriod = " + str(tPeriod) + '\n' +
                             "            t[-1]   = " + str(t[-1]) + '.')
        tRet = []
        inc = t[1] - t[0]
        for i in t:
            tRet.append(i % ((n + 1) * inc))
        return (np.array(tRet), y)
    convertToPeriodic = staticmethod(convertToPeriodic)

    def boxplot(t, y, increment=3600, nIncrement=24,
                notch=0, sym='b+', vert=1, whis=1.5,
                positions=None, widths=None, patch_artist=False, bootstrap=None):
        """ Create a boxplot of time data.

        :param t: The support points in time as received from the *Reader*.
        :param y: The function values at ``t`` as received from the *Reader*.
        :param increment: The time increment that is used in the plot
        :param nIncrement: The number of increments before the data are wrapped.
        :return: This method returns a
                 `matplotlib.pyplot <https://matplotlib.org/stable/api/pyplot_summary.html>`_ object that can be further
                 processed, such as to label its axis.

        All other arguments are as explained at `matplotlib's boxplot documentation
        <https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.boxplot.html>`_.

        The parameter ``increment`` is used to set the support points in time
        at which the statistics is made.
        The parameter ``nIncrement`` is used to determine how many increments will
        be made. For example,

        - for hourly statistics, use the default, which is ``increment=3600, nIncrement=24``, and
        - for statistics every five minutes over one hour, use ``increment=5*60, nIncrement=12``.

        Usage: Type

           >>> import os
           >>> import matplotlib
           >>> matplotlib.use('Agg')
           >>> import matplotlib.pyplot as plt
           >>>
           >>> from buildingspy.io.outputfile import Reader
           >>> from buildingspy.io.postprocess import Plotter
           >>>
           >>> # Read data
           >>> resultFile = os.path.join("buildingspy", "examples", "dymola", "TwoRoomsWithStorage.mat")
           >>> r=Reader(resultFile, "dymola")
           >>> (t, y) = r.values('roo1.air.vol.T')
           >>>
           >>> # Create basic plot
           >>> plt=Plotter.boxplot(t=t, y=y-273.15, increment=3600, nIncrement=24)
           >>>
           >>> # Decorate, save and show the plot
           >>> plt.xlabel('Time [h]')
           Text(0.5, 0, 'Time [h]')
           >>> plt.ylabel(u'Room temperature [°C]') #doctest: +ELLIPSIS
           Text(0, 0.5, 'Room temperature [°C]')
           >>> plt.grid()
           >>> plt.savefig("roomTemperatures.png")
           >>> plt.show() # doctest: +SKIP

           to create a plot as the one shown below.

        .. image:: ../../../BuildingsPy/doc/source/img/TwoRoomsWithStorage_T.png
           :width: 560 px
           :align: center

        """
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt

        import numpy as np

        # Make sure that input is periodic
        tPeriod = increment * nIncrement
        rem = (t[-1] - t[0]) % tPeriod
        if abs(rem) > 1E-20:
            raise ValueError('Length of time series must be a multiple of increment*nIncrement.\n' +
                             '  Received increment  = ' + str(increment) + '\n' +
                             '           nIncrement = ' + str(nIncrement) + '\n' +
                             '           t[-1]-t[0] = ' + str(t[-1] - t[0]) + '.')

        # Make equidistant grid for the whole simulation period, such as 0, 1, ... 47
        # for two days
        tMax = max(t)
        tGrid = np.linspace(0, tMax - increment, num=int(round(tMax / increment)))

        # Interpolate to hourly time stamps
        yGrid = Plotter.interpolate(tGrid, t, y)

        # Convert to periodic data
        yPer = Plotter.convertToPeriodic(tPeriod=tPeriod,
                                         t=tGrid,
                                         y=yGrid)[1]

        tMaxPlot = nIncrement
        yStacked = np.reshape(yPer, (-1, tMaxPlot))
        plt.boxplot(yStacked, positions=list(range(tMaxPlot)),
                    notch=notch,
                    sym=sym, vert=vert, whis=whis,
                    widths=widths,
                    patch_artist=patch_artist, bootstrap=bootstrap)
        return plt
    boxplot = staticmethod(boxplot)
