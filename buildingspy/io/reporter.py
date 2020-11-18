#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
class Reporter(object):
    """ Class that is used to report errors.
    """

    def __init__(self, fileName):
        """ Construct a reporter.

        :param fileName: Name of the output file.

        This class writes the standard output stream and the
        standard error stream to the file ``fileName``.
        """
        import os

        self._logToFile = True
        self._verbose = True
        self._iWar = 0
        self._iErr = 0
        self.logToFile()
        self._logFil = os.path.join(fileName)
        self.deleteLogFile()

    def deleteLogFile(self):
        """ Deletes the log file if it exists.
        """
        import os
        if os.path.isfile(self._logFil):
            # The try-except below guards against a race condition if multiple
            # processes start and they try to delete the file at the same time.
            try:
                os.remove(self._logFil)
            except FileNotFoundError:
                print(f"Failed to remove {self._logFil} as it no longer exists.")

    def logToFile(self, log=True):
        """ Function to log the standard output and standard error stream to a file.

        :param log: If ``True``, then the standard output stream and the standard error stream will be logged to a file.

        This function can be used to enable and disable writing outputs to
        the file ''fileName''.
        The default setting is ``True``
        """
        self._logToFile = log

    def getNumberOfErrors(self):
        """ Returns the number of error messages that were written.

        :return : The number of error messages that were written.
        """
        return self._iErr

    def getNumberOfWarnings(self):
        """ Returns the number of warning messages that were written.

        :return : The number of warning messages that were written.
        """
        return self._iWar

    def writeError(self, message):
        """ Writes an error message.

        :param message: The message to be written.

        Note that this method adds a new line character at the end of the message.
        """
        self._iErr += 1
        self._writeErrorOrWarning(True, message)
        return

    def writeWarning(self, message):
        """ Writes a warning message.

        :param message: The message to be written.

        Note that this method adds a new line character at the end of the message.
        """
        self._iWar += 1
        self._writeErrorOrWarning(False, message)
        return

    def _writeErrorOrWarning(self, isError, message):
        """ Writes an error message or a warning message.

        :param isError: Set to 'True' if an error should be written, or 'False' for a warning.
        :param message: The message to be written.

        Note that this method adds a new line character at the end of the message.
        """
        import sys

        msg = ""
        if self._verbose:
            if isError:
                msg += "*** Error: "
            else:
                msg += "*** Warning: "
        msg += message + "\n"
        sys.stderr.write(msg)
        if self._logToFile:
            with open(self._logFil, mode="a", encoding="utf-8") as fil:
                fil.write(msg)
        return

    def writeOutput(self, message):
        """ Writes a message to the standard output.

        :param message: The message to be written.

        Note that this method adds a new line character at the end of the message.
        """
        import sys

        msg = message + "\n"
        if self._logToFile:
            with open(self._logFil, mode="a", encoding="utf-8") as fil:
                fil.write(msg)
        sys.stdout.write(msg)
        return
