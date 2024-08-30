#!/usr/bin/env python3
########################################################
# 2021-02-03: Changed calculation of relative time difference.
# 2020-11-11: Corrected color coding for html output
########################################################
import getpass
import git
import glob
import io
import json
import os
import re
import sys
import shutil
import tempfile

from distutils.dir_util import mkpath


class Comparator(object):
    """ Class that compares various simulation statistics across tools or branches.

    This class allows comparing various simulation performance indicators
    (CPU time, number of state events, number of Jacobian evaluations)
    across Modelica simulation tools and across git branches.
    The tests can be run across a whole library, or across an individual Modelica package.
    The results will be summarized in a table format that compares the performance
    across tools and branches.

    Initiate with the following optional arguments:

    :param tools: A list of tools to compare, such as ``['openmodelica', 'dymola']``.
    :param branches: A list of branches to compare, such as ``['master', 'issueXXX']``.
    :param package: Name of top-level package to compare, such as ``Buildings`` or ``Buildings.Examples``.
    :param repo: Name of repository, such as ``https://github.com/lbl-srg/modelica-buildings``.
    :param skipVerification: Boolean (default ``False``).
            If ``True``, unit test results are not verified against reference points.
    :param nPro: Number of threads that are used to run the translations and simulations.
                 Set to ``0`` to use all processors.
    :param tolAbsTim: float (default ``0.1``). Absolute tolerance in time, if exceeded, results will be flagged in summary table.
    :param tolRelTim: float (default ``0.1``). Relative tolerance in time, if exceeded, results will be flagged in summary table.
    :param postCloneCommand: list. A list of a command and its arguments that is run after cloning the repository. The command is run from
           the root folder inside the repository, e.g., the folder that contains the ``.git`` folder.

    This class can be used to compare translation and simulation statistics across tools and branches.
    Note that only one simulation is done, hence the simulation time can vary from one run to another,
    and therefore indicates trends rather than exact comparison of computing time.

    To run the comparison, type

       >>> import os
       >>> import buildingspy.development.simulationCompare as sc
       >>> s = sc.Comparator(
       ...   tools=['dymola', 'openmodelica'],
       ...   branches=['master'],
       ...   package='Buildings',
       ...   repo='https://github.com/lbl-srg/modelica-buildings',
       ...   skipVerification = True,
       ...   postCloneCommand=[
       ...      "python",
       ...      "Buildings/Resources/src/ThermalZones/install.py",
       ...      "--binaries-for-os-only"])
       >>> s.run()                                           # doctest: +SKIP


    To change the comparison for different tolerances without running the simulations again, type

       >>> import os
       >>> import buildingspy.development.simulationCompare as sc
       >>> s = sc.Comparator(
       ...   tools=['dymola', 'openmodelica'],
       ...   branches=['master'],
       ...   package='Buildings',
       ...   repo='https://github.com/lbl-srg/modelica-buildings',
       ...   postCloneCommand=[
       ...      "python",
       ...      "Buildings/Resources/src/ThermalZones/install.py",
       ...      "--binaries-for-os-only"])
       >>> s.post_process(tolAbsTime=0.2, tolRelTime=0.2)     # doctest: +SKIP


    """

    def __init__(
            self,
            tools,
            branches,
            package,
            repo,
            skipVerification=False,
            nPro=0,
            simulate=True,
            tolAbsTime=0.1,
            tolRelTime=0.1,
            postCloneCommand=None):

        self._cwd = os.getcwd()
        self._tools = tools
        self._branches = branches
        self._package = package
        self._lib_src = repo
        self._skip_verification = skipVerification
        self._nPro = nPro
        self._tolAbsTime = tolAbsTime
        self._tolRelTime = tolRelTime
        self._generate_tables = True
        self._postCloneCommand = postCloneCommand

    def _get_cases(self):
        ''' Set up simulation cases.
        '''
        cases = list()
        for tool in self._tools:
            for branch in self._branches:
                cases.append(
                    {'package': self._package,
                     'tool': tool,
                     'branch': branch})
        for case in cases:
            desDir = os.path.join(self._cwd, case['tool'], case['branch'])
            logFil = os.path.join(desDir, "comparison-%s.log" % case['tool'])
            commitLog = os.path.join(desDir, "commit.log")
            case['name'] = logFil
            case['commit'] = commitLog
        return cases

    @staticmethod
    def _create_and_return_working_directory():
        ''' Create working directory.
        '''
        worDir = tempfile.mkdtemp(prefix='tmp-simulationCompare-' + getpass.getuser())
        print("Created directory {}".format(worDir))
        return worDir

    def _runPostCloneCommand(self, working_directory):
        import subprocess
        if self._postCloneCommand is not None:
            print(f"*** Running {' '.join(self._postCloneCommand)} in '{working_directory}")
            retArg = subprocess.run(self._postCloneCommand, cwd=working_directory)
            if retArg.returncode != 0:
                print(
                    f"*** Error: Command {' '.join(self._postCloneCommand)} in '{working_directory} returned {retArg.returncode}.")

    def _clone_repository(self, working_directory):
        '''Clone or copy repository to working directory'''
#        if from_git_hub:
        print(f'*** Cloning repository {self._lib_src} in {working_directory}')
        git.Repo.clone_from(self._lib_src, working_directory)
#        else:
#            shutil.rmtree(working_directory)
#            print(f'*** Copying repository from {self._lib_src} to {working_directory}')
#            shutil.copytree(self._lib_src, working_directory)

    @staticmethod
    def _checkout_branch(working_directory, branch):
        '''Checkout feature branch'''
        d = {}
        print(f'Checking out branch {branch}')
        r = git.Repo(working_directory)
        g = git.Git(working_directory)
        g.stash()
        g.checkout(branch)
        # Print commit
        d['branch'] = branch
        d['commit'] = str(r.active_branch.commit)

        return d

    def _runUnitTest(self, package, tool):
        ''' Execute unit tests.
        '''
        if package.find(".") == -1:
            # Top level package is requested
            single_package = ""
        else:
            single_package = f"-s {package}"

        if self._nPro == 0:
            num_pro = ""
        else:
            num_pro = f"-n {self._nPro}"

        ski_ver = f"--skip-verification" if {self._skip_verification} else ""

        command = f"../bin/runUnitTests.py {single_package} {ski_ver} {num_pro} -t {tool} --batch"
        try:
            os.system(command)
        except OSError:
            sys.stderr.write("Execution of '" + command + "' failed.")

    def _simulateCase(self, case, wor_dir):
        ''' Set up unit tests and save log file
        '''
        bdg_dir = os.path.join(wor_dir, self._package.split(".")[0])
        os.chdir(bdg_dir)
        # run unit test
        self._runUnitTest(case['package'], case['tool'])
        # copy the log files to current working directory
        if os.path.exists(bdg_dir):
            # write commit number to the commit.log file
            with io.open(os.path.join(bdg_dir, "commit.log"), mode="w") as f:
                f.write(case['commit'])
            logFiles = glob.iglob(os.path.join(bdg_dir, "*.log"))
            desDir = os.path.join(self._cwd, case['tool'], case['branch'])
            mkpath(desDir)
            for file in logFiles:
                shutil.copy2(file, desDir)
        else:
            sys.stderr.write(f"Error: For {case['tool']} {case['branch']}, did not find {bdg_dir}.")
        os.chdir(self._cwd)

    @staticmethod
    def _sortSimulationData(case):
        ''' Filter the needed data from log file

        The unit test generated log file "comparison-xxx.log", which is then renamed as case['name'], contains more
        data than needed.
        '''
        logs = list()
        with io.open(case['name'], mode="rt", encoding="utf-8-sig") as log:
            stat = json.loads(log.read())
        for ele in stat:
            if "simulation" in ele:
                temp = {"model": ele["model"],
                        "simulation": ele["simulation"]}
                logs.append(temp)
        return logs

    @staticmethod
    def _refactorLogsStructure(logs, tolAbsTime, tolRelTime):
        ''' Change the structure:
        --From--
        "logs": [{"label": 'branch1', "commit": string, "log": [{"model": model1, "simulation": simulation_log},
                                                                {"model": model2, "simulation": simulation_log}]},
                 {"label": 'branch2', "commit": string, "log": [{"model": model1, "simulation": simulation_log},
                                                                {"model": model2, "simulation": simulation_log}]}],
        --To--
        "logs": [  {"model": model1,
                    "simulation": [{"label": branch1, "commit": string, "log": simulation_log},
                                   {"label": branch2, "commit": string, "log": simulation_log}]},
                   {"model": model2,
                    "simulation": [{"label": branch1, "commit": string, "log": simulation_log},
                                   {"label": branch2, "commit": string, "log": simulation_log}]}  ]
        '''
        minLog = 0
        modelNumber = len(logs[0]['log'])
        for i in range(1, len(logs)):
            ithCaseModelNumber = len(logs[i]['log'])
            if ithCaseModelNumber < modelNumber:
                modelNumber = ithCaseModelNumber
                minLog = i
        refactoredLogs = list()
        for j in range(len(logs[minLog]['log'])):
            model = {'model': logs[minLog]['log'][j]['model']}
            model['flag'] = False
            simulation = list()
            # find the same model's simulation log from other simulations
            for k in range(len(logs)):
                for l in range(len(logs[k]['log'])):
                    if logs[k]['log'][l]['model'] == logs[minLog]['log'][j]['model']:
                        temp = {'label': logs[k]['label'],
                                'commit': logs[k]['commit'],
                                'log': logs[k]['log'][l]['simulation']}
                        simulation.append(temp)
            model['simulation'] = simulation
            # check if the model runs successfully in all branches or tools
            suc = Comparator._checkSimulation(model)
            if suc is not True:
                refactoredLogs.append(model)
                continue
            refactoredLogs.append(model)
        return refactoredLogs

    @staticmethod
    def _checkSimulation(model):
        ''' Check if the model runs successfully in all branches or tools
        '''
        suc = True
        simLogs = model['simulation']
        for i in range(len(simLogs)):
            logSuc = simLogs[i]['log']['success']
            suc = suc and logSuc
        return suc

    @staticmethod
    def _refactorDataStructure(data, tolAbsTime, tolRelTime):
        ''' Change data structure
        '''
        refactoredData = list()
        for ele in data:
            temp = {'label': ele['label']}
            logs = Comparator._refactorLogsStructure(ele['logs'], tolAbsTime, tolRelTime)
            temp['logs'] = logs
            refactoredData.append(temp)
        return refactoredData

    def _generateTable(self, dataSet):
        ''' Generate html table and write it to file

            The dataSet has structure as:
            [
                {
                    'label': 'tool_name' (or 'branch_name'),   // 'dymola' (or 'master')
                    'logs': [
                        {
                            'model': 'model1',
                            'simulation': [
                                {
                                    'label': 'branch_name' (or 'tool_name'),   // 'master' (or 'dymola')
                                    'commit': 'commit #',
                                    'log': {
                                        'cpu_time': ,
                                        'elapsed_time': ,
                                        'final_time': ,
                                        'jacobians': ,
                                        'start_time': ,
                                        'state_events': ,
                                        'success':
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        '''

        htmlTableDir = os.path.join(self._cwd, 'results', 'html')
        mkpath(htmlTableDir)
        # latexTableDir = os.path.join(self._cwd, 'results', 'latex')
        # mkpath(latexTableDir)
        for data in dataSet:
            # generate branches comparison tables
            if len(self._branches) > 1:
                for tool in self._tools:
                    if data['label'] == tool:
                        # Compare branches against the first branch listed
                        for comBra in self._branches[1:]:
                            filNam = os.path.join(
                                htmlTableDir, f"compare_{tool}--{self._branches[0]}-{comBra}.html")
                            # texTab = os.path.join(latexTableDir, "branches_compare_%s.tex" % tool)
                            # generate html table content
                            htmltext, flagModels = self._generateHtmlTable(
                                self._package, data, [tool], [
                                    self._branches[0], comBra], self._tolRelTime, self._tolAbsTime, self._lib_src)
                            Comparator._writeFile(filNam, htmltext)
                            # self._generateTexTable(texTab, flagModels)
            # generate tools comparison tables
            if len(self._tools) > 1:
                for branch in self._branches:
                    if data['label'] == branch:
                        for comToo in self._tools[1:]:
                            filNam = os.path.join(
                                htmlTableDir, f"compare_{branch}--{self._tools[0]}-{comToo}.html")
                            # texTab = os.path.join(latexTableDir, "tools_compare_%s.tex" % branch)
                            # generate html table content
                            htmltext, flagModels = self._generateHtmlTable(self._package, data,
                                                                           [self._tools[0], comToo], [branch],
                                                                           self._tolRelTime, self._tolAbsTime, self._lib_src)
                            Comparator._writeFile(filNam, htmltext)
                            # self._generateTexTable(texTab, flagModels)

    def _generateTexTable(self, filNam, models):
        try:
            log = models[0]['log']
        except IndexError:  # No flagged model to process.
            return

        totalColumns = 2 + len(log)
        begin = \
            r'''\documentclass{article}
\usepackage[table]{xcolor}
\usepackage{longtable}
\usepackage{listings}
\begin{document}
\def\tableCaption{xxxYYY.}
\def\tableLabel{tab:xxx}
'''

        column = \
            r'''\begin{longtable}{|p{9cm}|'''
        captionLabel = \
            r'''\caption{\tableCaption}
\label{\tableLabel}\\
    '''
        for i in range(totalColumns - 2):
            column = column + '''p{2cm}|'''
        column = column + 'p{1cm}|}' + os.linesep
        hline = '''\\hline''' + os.linesep
        # column head
        head = '''Model'''
        for i in range(len(log)):
            head = head + '''&$t_{%s}$ in [s]''' % log[i]['label'].replace('_', '\\_')
        head = head + '''&$t_{2}/t_{1}$\\\\'''
        head = head + '''[2.5ex] \\hline''' + os.linesep
        row = ''
        for i in range(len(models)):
            ithModel = models[i]
            temp = ''
            fillColor = self._textTableColor(ithModel['relTim'])
            temp = '''\\rowcolor[HTML]{%s} ''' % fillColor + os.linesep
            temp = temp + '''{\\small ''' + '''\\lstinline|''' + \
                ithModel['model'].replace(f'{self._package}.', '') + '''|}'''
            for j in range(len(log)):
                temp = temp + '&' + '{\\small ' + \
                    '{:.3f}'.format(ithModel['log'][j]['elapsed_time']) + '}'
            temp = temp + '&' + '{\\small ' + '{:.2f}'.format(ithModel['relTim']) + '}'
            temp = temp + '''\\\\[2.5ex] \\hline''' + os.linesep
            row = row + temp
        end = '''
\\end{longtable}
\\end{document}'''
        content = begin + column + captionLabel + hline + head + row + end
        Comparator._writeFile(filNam, content)

    def _textTableColor(self, relTim):
        dif = relTim - 1 - self._tolRelTime if relTim > 1 else (1 - relTim) - self._tolRelTime
        dR = 0.5
        dG = 0.1
        if dif < 0:
            color = 'FFFFFF'
        elif dif >= 0:
            if relTim < 1:
                if dif >= 0 and dif < dG:
                    color = 'edfef2'
                elif dif >= dG and dif < 2 * dG:
                    color = 'dbfde4'
                elif dif >= 2 * dG and dif < 3 * dG:
                    color = 'c9fcd7'
                elif dif >= 3 * dG and dif < 4 * dG:
                    color = 'b6fbca'
                elif dif >= 4 * dG and dif < 5 * dG:
                    color = 'a4fbbc'
                elif dif >= 5 * dG and dif < 6 * dG:
                    color = '92faaf'
                elif dif >= 6 * dG and dif < 7 * dG:
                    color = '80f9a1'
                else:
                    color = '6ef894'
            else:
                if dif >= 0 and dif < dR:
                    color = 'feeded'
                elif dif >= dR and dif < 2 * dR:
                    color = 'fddbdb'
                elif dif >= 2 * dR and dif < 3 * dR:
                    color = 'fcc9c9'
                elif dif >= 3 * dR and dif < 4 * dR:
                    color = 'fbb6b6'
                elif dif >= 4 * dR and dif < 5 * dR:
                    color = 'fba4a4'
                elif dif >= 5 * dR and dif < 6 * dR:
                    color = 'fa9292'
                elif dif >= 6 * dR and dif < 7 * dR:
                    color = 'f98080'
                else:
                    color = 'f86e6e'
        return color

    @staticmethod
    def _writeFile(filNam, content):
        ''' Write html table to file
        '''
        print(f"*** writing {filNam}")
        with open(filNam, 'w+') as f:
            f.write(content)

    @staticmethod
    def _chooseStyle(relTim, tolRelTime, flag):
        # relTim is  (elaTim-t_0) / t_0
        dif = relTim - 1 - tolRelTime if relTim > 1 else (1 - relTim) - tolRelTime
        dR = 0.5
        dG = 0.1
        style = 'normal'
        if dif >= 0 and flag:
            if relTim < 1:
                if dif >= 0 and dif < dG:
                    style = 'g-1'
                elif dif >= dG and dif < 2 * dG:
                    style = 'g-2'
                elif dif >= 2 * dG and dif < 3 * dG:
                    style = 'g-3'
                elif dif >= 3 * dG and dif < 4 * dG:
                    style = 'g-4'
                elif dif >= 4 * dG and dif < 5 * dG:
                    style = 'g-5'
                elif dif >= 5 * dG and dif < 6 * dG:
                    style = 'g-6'
                elif dif >= 6 * dG and dif < 7 * dG:
                    style = 'g-7'
                else:
                    style = 'g-8'
            else:
                if dif >= 0 and dif < dR:
                    style = 'r-1'
                elif dif >= dR and dif < 2 * dR:
                    style = 'r-2'
                elif dif >= 2 * dR and dif < 3 * dR:
                    style = 'r-3'
                elif dif >= 3 * dR and dif < 4 * dR:
                    style = 'r-4'
                elif dif >= 4 * dR and dif < 5 * dR:
                    style = 'r-5'
                elif dif >= 5 * dR and dif < 6 * dR:
                    style = 'r-6'
                elif dif >= 6 * dR and dif < 7 * dR:
                    style = 'r-7'
                else:
                    style = 'r-8'
        return style

    @staticmethod
    def _add_flag(sim, log, tolAbsTime, tolRelTime):
        ''' Add flag to show if one model has significantly different simulation time among different tools or branches
        '''
        relTim = 0
        log['flag'] = False
        if (len(sim) > 1):
            if (sim[0]['log']['success'] and sim[1]['log']['success']):
                t_0 = sim[0]['log']['elapsed_time']
                t_1 = sim[1]['log']['elapsed_time']
                t_max = max(t_0, t_1)
                if (t_0 > 1E-10):
                    relTim = t_1 / t_0
                if t_max > tolAbsTime and abs(1 - relTim) > tolRelTime:
                    log['flag'] = True
        log['relTim'] = relTim

    @staticmethod
    def _filter_data_set(fullLabels, tempLogs, tolAbsTime, tolRelTime):
        ''' Filter data for comparing only two data set, either tools or branches comparison
        '''
        dataLogs = list()
        for tempLog in tempLogs:
            log = {'model': tempLog['model']}
            simLogs = tempLog['simulation']
            if (len(simLogs) > 0):
                tempSim = list()
                for simLog in simLogs:
                    for labEle in fullLabels:
                        if (simLog['label'] == labEle):
                            tempSim.append(simLog)
                log['simulation'] = tempSim
                if (len(tempSim) > 0):
                    # add flag to identify if one model has significantly different simulation
                    # time among different tools or branches
                    Comparator._add_flag(tempSim, log, tolAbsTime, tolRelTime)
            dataLogs.append(log)
        return dataLogs

    def _print_dictionary(msg, dic, exit=False):
        import sys
        import pprint
        pp = pprint.PrettyPrinter(indent=4)
        print(f"*************** {msg} **************************")
        pp.pprint(dic)
        print(f"*****************************************")
        if exit:
            sys.exit(1)

    @staticmethod
    def _generateHtmlTable(package, data, tools, branches, tolRelTime, tolAbsTime, lib_src):
        ''' Html table template
        '''
        # style section
        style = '''
<style type="text/css">
    .tg  {border-collapse:collapse;border-spacing:0;}
    .tg td{font-family:Arial, sans-serif;font-size:14px;padding:10px 5px;border-style:solid;border-width:1px;overflow:auto;word-break:normal;border-color:black;}
    .tg th{font-family:Arial, sans-serif;font-size:14px;font-weight:normal;padding:10px 5px;border-style:solid;border-width:1px;overflow:auto;word-break:normal;border-color:black;}
    .tg .tg-head{font-weight:bold;font-size:16px;border-color:inherit;text-align:center;vertical-align:center}
    .tg .tg-g-1{background-color:#edfef2;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-g-2{background-color:#dbfde4;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-g-3{background-color:#c9fcd7;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-g-4{background-color:#b6fbca;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-g-5{background-color:#a4fbbc;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-g-6{background-color:#92faaf;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-g-7{background-color:#80f9a1;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-g-8{background-color:#6ef894;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}

    .tg .tg-r-1{background-color:#feeded;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-r-2{background-color:#fddbdb;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-r-3{background-color:#fcc9c9;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-r-4{background-color:#fbb6b6;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-r-5{background-color:#fba4a4;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-r-6{background-color:#fa9292;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-r-7{background-color:#f98080;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-r-8{background-color:#f86e6e;border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
    .tg .tg-normal{border-color:inherit;text-align:left;overflow:auto;vertical-align:center}
</style>
<script src="https://www.kryogenix.org/code/browser/sorttable/sorttable.js"></script>
'''

        # calculate column width
        tools_or_branches = "tools" if len(tools) > 1 else "branches"
        fullLabels = tools if tools_or_branches == 'tools' else branches
        numberOfDataSet = len(fullLabels)
        colWidth = 100 / (3 + numberOfDataSet * 3 + 1)

        # find the data logs
        tempLogs = data['logs']
        dataLogs = Comparator._filter_data_set(fullLabels, tempLogs, tolAbsTime, tolRelTime)

        # specify column style
        colGro = '''
            <table class="tg sortable" style="undefined">
                <colgroup>
            <col style="width: %.2f%%">
            ''' % (3 * colWidth)
        for i in range(3 * numberOfDataSet + 1):
            temp = '''<col style="width: %.2f%%">''' % colWidth + os.linesep
            colGro = colGro + temp
        colGro = colGro + '''</colgroup>''' + os.linesep

        # specify head
        heaGro = '''
             <tr>
                <th class="tg-head">Model</th>
            '''
        for i in range(numberOfDataSet):
            label = fullLabels[i]
            temp = '''
                <th class="tg-head">%s<br/>-<br/>Elapsed time (s)</td>
                <th class="tg-head">%s<br/>-<br/>State events</td>
                <th class="tg-head">%s<br/>-<br/>Jacobians</td>
            ''' % (label, label, label)
            heaGro = heaGro + temp
        heaGro = heaGro + '''<th class="tg-head">t<sub>2</sub>&frasl;t<sub>1</sub></th>''' + os.linesep
        heaGro = heaGro + '''</tr>''' + os.linesep

        # find total number of models
        numberOfModels = len(dataLogs)

        # write simulation logs of each model
        flagModelList = list()
        models = ''
        failedModels = list()
        newDataLogs = list()
        for entry in dataLogs:
            entSim = entry['simulation']
            suc = True
            failedIn = list()
            if (len(entSim) == numberOfDataSet):
                # the model has been translated by all tools/in all branches so it has
                # fully set of simulation log, but it may not be simulated successfully.
                for simLog in entSim:
                    suc = suc and simLog['log']['success']
                    if simLog['log']['success'] is not True:
                        failedIn.append(simLog['label'])
            else:
                # the model is not translated by one/more tools or in one/more branches so
                # it does not have fully set of simulation log.
                suc = False
                if (len(entSim) == 0):
                    tmp = ' ,'.join(fullLabels)
                    failedIn.append(tmp)
                else:
                    # list the successful run
                    sucLab = list()
                    for simLog in entSim:
                        if simLog['log']['success']:
                            sucLab.append(simLog['label'])
                    # filter the tools or branches that do not simulate or translate the model
                    for fulLab in fullLabels:
                        if fulLab not in sucLab:
                            failedIn.append(fulLab)
            if suc:
                newDataLogs.append(entry)
            if suc is not True:
                temp = {'model': entry['model']}
                temp['logs'] = failedIn
                failedModels.append(temp)

        # find the branches and the corresponded commit
        firstEnt = newDataLogs[0]
        firstEntSim = firstEnt['simulation']
        toolBranchInfo = ''
        if tools_or_branches == 'tools':
            commitText = f'<a href="{lib_src}/tree/{firstEntSim[0]["commit"]}">{firstEntSim[0]["commit"]}</a>' \
                if lib_src[0:5] == "https" else f'<code>{firstEntSim[0]["commit"]}</code>'
            branchCommit = '''Branch <b>%s</b> (%s)''' % (data['label'], commitText)
            toolsList = list()
            for simLog in firstEntSim:
                toolsList.append(simLog['label'])
            tools = ', '.join(toolsList)
            toolBranchInfo = '''<br/>
                                <p><font size="+1.5">
                                %s,<br/>comparing tools: <b>%s</b>.</font>
                                </p>
                             ''' % (branchCommit, tools)
        else:
            branchCommitList = list()
            for simLog in firstEntSim:
                commitText = f'<a href="{lib_src}/tree/{simLog["commit"]}">{simLog["commit"]}</a>' \
                    if lib_src[0:5] == "https" else f'<code>{simLog["commit"]}</code>'
                temp = '''<b>%s</b> (%s)''' % (simLog['label'], commitText)
                branchCommitList.append(temp)
            branchCommit = ',<br/>'.join(branchCommitList)
            toolBranchInfo = '''<br/>
                                <p><font size="+1.5">
                                Run with <b>%s</b>,<br/>comparing branches:<br/>%s.</font>
                                </p>
                             ''' % (data['label'], branchCommit)

        for entry in newDataLogs:
            modelData = '''<tr>''' + os.linesep
            flag = entry['flag']
            relTim = entry['relTim']
            tgStyle = 'tg-' + Comparator._chooseStyle(relTim, tolRelTime, flag)
            if flag:
                flagModelListTemp = {'model': entry['model']}
                flagModelListTemp['relTim'] = relTim
            temp1 = '''<td class="%s">%s</td>''' % (tgStyle, entry['model'])
            modelData = modelData + temp1 + os.linesep
            temp2 = ''
            temp3 = list()
            for j in range(numberOfDataSet):
                variableSet = entry['simulation'][j]['log']
                elapsed_time = variableSet['elapsed_time']
                state_events = variableSet['state_events']
                jacobians = variableSet['jacobians']
                flagTemp = {'elapsed_time': elapsed_time,
                            'state_events': state_events,
                            'jacobians': jacobians,
                            'label': entry['simulation'][j]['label']}
                temp3.append(flagTemp)
                temp2 = temp2 + '''
                    <td class="%s">%.4f</td>
                    <td class="%s">%d</td>
                    <td class="%s">%d</td>
                ''' % (tgStyle, elapsed_time,
                       tgStyle, int(state_events),
                       tgStyle, int(jacobians))
            if flag:
                flagModelListTemp['log'] = temp3
                flagModelList.append(flagModelListTemp)
            modelData = modelData + temp2 + os.linesep
            modelData = modelData + '''<td class="%s">%.2f</td>''' % (tgStyle, relTim) + os.linesep
            modelData = modelData + '''</tr>''' + os.linesep
            models = models + os.linesep + modelData

        sortedList = sorted(flagModelList, reverse=True, key=lambda k: k['relTim'])

        # write flagged models
        flaggedModels = ''
        for model in sortedList:
            modelData = '''<tr>''' + os.linesep
            relTim = model['relTim']
            tgStyle = 'tg-' + Comparator._chooseStyle(relTim, tolRelTime, True)
            modelName = model['model']
            temp1 = '''<td class="%s">%s</td>''' % (tgStyle, modelName)
            modelData = modelData + temp1 + os.linesep
            temp2 = ''
            for j in range(len(model['log'])):
                oneSet = model['log'][j]
                temp2 = temp2 + '''
                    <td class="%s">%.4f</td>
                    <td class="%s">%d</td>
                    <td class="%s">%d</td>
                ''' % (tgStyle, oneSet['elapsed_time'],
                       tgStyle, int(oneSet['state_events']),
                       tgStyle, int(oneSet['jacobians']))
            modelData = modelData + temp2 + os.linesep
            modelData = modelData + '''<td class="%s">%.2f</td>''' % (tgStyle, relTim) + os.linesep
            modelData = modelData + '''</tr>''' + os.linesep
            flaggedModels = flaggedModels + os.linesep + modelData

        failedFlagText = ''
        if tools_or_branches == 'branches':
            failedFlagText = 'failed in branches'
        else:
            failedFlagText = 'failed or excluded by tools'
        failedModelsInfo = ''
        if len(failedModels) > 0:
            failedModelsInfo = '''<br/>
                                <p><font size="+1.5">
                                Following models were flagged as %s.</font>
                                </p>
                                ''' % failedFlagText
            failedModelsInfo += os.linesep
            failedModelsInfo += '''<table class="tg sortable" style="undefined">''' + os.linesep
            failedModelsInfo += '''<tr><th class="tg-head">Model</th><th class="tg-head">Failed Info</th> </tr>''' + os.linesep
            for i in range(len(failedModels)):
                failedTxt = ', '.join(failedModels[i]['logs'])
                failedModelsInfo += '''<tr><td class="tg-r-8">%s</td><td>%s</td></tr>
                                    ''' % (failedModels[i]['model'], failedTxt) + os.linesep
            failedModelsInfo += '''</table>'''

        flagInfo = '''<br/>
                     <p><font size="+1.5">
                     Following models were flagged because the maximum simulation time is greater than %.2f seconds
                     and the relative difference between maximum and minimum simulation time
                     (i.e. <code>(t<sub>max</sub> - t<sub>min</sub>)/t<sub>max</sub></code>)
                     is greater than %.2f.</font>
                     </p>
                    ''' % (tolAbsTime, tolRelTime)
        flagModels = colGro + heaGro + flaggedModels + os.linesep + \
            '''</table>'''
        allModelInfo = '''<br/><br/>
                        <p><font size="+1.5">
                        Following models are in package <code>%s</code>:
                        </font></p>
                        ''' % package
        allModels = colGro + heaGro + models + os.linesep + \
            '''</table>'''

        # assemble html content
        htmltext = '''<html>''' + os.linesep + style + toolBranchInfo + failedModelsInfo + \
            flagInfo + flagModels + allModelInfo + allModels + '''</html>'''
        return htmltext, sortedList

    def _runCases(self, cases):
        ''' Run simulations
        '''
        lib_dir = self._create_and_return_working_directory()
        self._clone_repository(lib_dir)
        self._runPostCloneCommand(lib_dir)
        for case in cases:
            d = self._checkout_branch(lib_dir, case['branch'])
            case['commit'] = d['commit']
            self._simulateCase(case, lib_dir)
        shutil.rmtree(lib_dir)

    def run(self):
        ''' Run the comparison and generate the output.

            The output files will be in the directory ``results``, and the raw test data
            are in the directories with the same names as specified by the parameter ``tools``.
        '''
        cases = self._get_cases()
        self._runCases(cases)
        self.post_process()

    def post_process(self, tolAbsTime=None, tolRelTime=None):
        ''' Generate the html tables.

            This function post-processes the simulations, generates the overview tables, and writes the tables
            to the directory `results`.

            :param tolAbsTime: float. Optional argument for absolute tolerance in time, if exceeded, results will be flagged in summary table.
            :param tolRelTime: float. Optional argument for relative tolerance in time, if exceeded, results will be flagged in summary table.

        '''

        _tolAbsTime = self._tolAbsTime if tolAbsTime is None else tolAbsTime
        _tolRelTime = self._tolRelTime if tolRelTime is None else tolRelTime

        logs = list()
        for case in self._get_cases():
            # find commit number
            with io.open(case['commit'], mode="r") as f:
                commit = f.read()
            # filter simulation log
            temp = {'branch': case['branch'],
                    'commit': commit,
                    'tool': case['tool'],
                    'log': Comparator._sortSimulationData(case)}
            logs.append(temp)
        toolsCompare = list()
        branchesCompare = list()

        # comparison between different branches with same tool
        if len(self._branches) > 1:
            for tool in self._tools:  # [dymola, jmodelica, OpenModelica]
                data = {'label': tool}
                temp = list()
                for log in logs:
                    if log['tool'] == tool:
                        branch = {'label': log['branch'],
                                  'commit': log['commit'],
                                  'log': log['log']}
                        temp.append(branch)
                data['logs'] = temp
                branchesCompare.append(data)
            # refactor data structure
            branchesData = Comparator._refactorDataStructure(
                branchesCompare, _tolAbsTime, _tolRelTime)
            # generate html table file
            self._generateTable(branchesData)

        # comparison between different tools on same branch
        if len(self._tools) > 1:
            for branch in self._branches:
                data = {'label': branch}
                temp = list()
                for log in logs:
                    if log['branch'] == branch:
                        toolLog = {'label': log['tool'],
                                   'commit': log['commit'],
                                   'log': log['log']}
                        temp.append(toolLog)
                data['logs'] = temp
                toolsCompare.append(data)
            # refactor data structure
            toolsData = Comparator._refactorDataStructure(toolsCompare, _tolAbsTime, _tolRelTime)
            # generate html table file
            self._generateTable(toolsData)
