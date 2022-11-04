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

class Comparison(object):
    """ Class that compares various simulation statistics across tools or branches.

    Initiate with the following optional arguments:

    :param tools: A list of tools to compare, such as ``['openmodelica', 'dymola']``.
    :param branches: A list of branches to compare, such as ``['master', 'issueXXX']``.
    :param package: Name of top-level package to compare, such as ``Buildings`` or ``Buildings.Examples``.
    :param repo: Name of repository, such as ``https://github.com/lbl-srg/modelica-buildings``.
    :param nPro: Number of threads that are used to run the translations and simulations.
                 Set to ``0`` to use all processors.
    :param simulate: Boolean (default ``True``). Set to ``False`` to skip the translation and simulation.
                 This may be used to regenerate tables for different tolerance settings.
    :param tolAbsTim: float (default ``0.1``). Absolute tolerance in time, if exceeded, results will be flagged in summary table.
    :param tolRelTim: float (default ``0.1``). Relative tolerance in time, if exceeded, results will be flagged in summary table.

    This class can be used to compare translation and simulation statistics across tools and branches.
    Note that only one simulation is done, hence the simulation time can vary from one run to another,
    and therefore indicates trends rather than exact comparison of computing time.

    To run the comparison, type

       >>> import os
       >>> import buildingspy.development.simulationCompare as s
       >>> s = sc.Comparison(tools=['dymola', 'openmodelica'], branches=['master'],
           package='Buildings', repo='https://github.com/lbl-srg/modelica-buildings')
       >>> s.run()                    # doctest: +SKIP


    """

    def __init__(
        self,
        tools,
        branches,
        package,
        repo,
        nPro = 0,
        simulate = True,
        tolAbsTime = 0.1,
        tolRelTime = 0.1
    ):
        self._cwd = os.getcwd(),
        self._tools = tools,
        self._branches = branches,
        self._package = package,
        self._lib_src = repo,
        self._nPro = nPro,
        self._simulate = simulate,
        self._tolAbsTime = tolAbsTime,
        self._tolRelTime = tolRelTime,
        self._generate_tables = True



    def _get_cases(self):
        ''' Set up simulation cases.
        '''
        cases = list()
        for tool in self._tools:
            for branch in self._branches:
                cases.append( \
                    {'package': self._package,
                     'tool': tool,
                     'branch': branch})
        for case in cases:
            desDir = os.path.join(self._cwd, case['tool'], case['branch'])
            logFil = os.path.join(desDir, "comparison-%s.log" % case['tool'])
            case['name'] = logFil
        return cases

    @staticmethod
    def _create_and_return_working_directory():
        ''' Create working directory.
        '''
        worDir = tempfile.mkdtemp( prefix='tmp-simulationCompare-' + getpass.getuser() )
        print("Created directory {}".format(worDir))
        return worDir


    def _clone_repository(self, working_directory, from_git_hub = True):
        '''Clone or copy repository to working directory'''
        if from_git_hub:
            print(f'*** Cloning repository {self._lib_src}')
            git.Repo.clone_from(self._lib_src, working_directory)
        else:
            shutil.rmtree(working_directory)
            print(f'*** Copying repository from {self._lib_src} to {working_directory}')
            shutil.copytree(self._lib_src, working_directory)

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

        command = f"../bin/runUnitTests.py {single_package} {num_pro} -t {tool} --batch"
        try:
            os.system(command)
        except OSError:
            sys.stderr.write("Execution of '" + command + "' failed.")


    def _simulate(self, case, wor_dir):
        ''' Set up unit tests and save log file
        '''
        bdg_dir = os.path.join(wor_dir, self._package)
        os.chdir(bdg_dir)
        # run unit test
        _runUnitTest(case['package'], case['tool'])
        # copy the log files to current working directory
        logFil = "comparison-%s.log" % case['tool']
        if os.path.exists(logFil):
            logFiles = glob.iglob(os.path.join(bdg_dir, "*.log"))
            desDir = os.path.join(self._cwd, case['tool'], case['branch'])
            mkpath(desDir)
            for file in logFiles:
                shutil.copy2(file, desDir)
        os.chdir(self._cwd)

    @staticmethod
    def sortSimulationData(case):
        ''' Filter the needed data from log file

        The unit test generated log file "comparison-xxx.log", which is then renamed as case['name'], contains more
        data than needed.
        '''
        logs = list()
        with io.open(case['name'], mode="rt", encoding="utf-8-sig") as log:
            stat = json.loads(log.read())
        for ele in stat:
            if "simulation" in ele and ele["simulation"]["success"]:
                temp = {"model": ele["model"],
                        "simulation": ele["simulation"]}
                logs.append(temp)
        return logs

    @staticmethod
    def _refactorLogsStructure(logs):
        ''' Change the structure:
        --From--
        "logs": [{"label": 'branch1', "log": [{"model": model1, "simulation": simulation_log},
                                              {"model": model2, "simulation": simulation_log}]},
                 {"label": 'branch2', "log": [{"model": model1, "simulation": simulation_log},
                                              {"model": model2, "simulation": simulation_log}]}],
        --To--
        "logs": [  {"model": model1,
                    "simulation": [{"label": branch1, "log": simulation_log},
                                   {"label": branch2, "log": simulation_log}]},
                   {"model": model2,
                    "simulation": [{"label": branch1, "log": simulation_log},
                                   {"label": branch2, "log": simulation_log}]}  ]
        '''
        minLog = 0
        modelNumber = len(logs[0]['log'])
        for i in range(1,len(logs)):
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
                                 'log': logs[k]['log'][l]['simulation']}
                        simulation.append(temp)
            model['simulation'] = simulation
            # find the maximum simulation time
            t_0 = model['simulation'][0]['log']['elapsed_time']
            t_max = t_0
            relTim = 0
            relTim = 0
            for m in range(1,len(model['simulation'])):
                elaTim = model['simulation'][m]['log']['elapsed_time']
                if t_0 > 1E-10:
                    relTim = elaTim / t_0
                if elaTim > t_max:
                    t_max = elaTim
            # check if the model should be flagged as the simulation times are
            # significantly different between different tools or branches
            if t_max > tolAbsTime and abs(1-relTim) > tolRelTime:
                model['flag'] = True
            model['relTim'] = relTim
            refactoredLogs.append(model)
        return refactoredLogs


    @staticmethod
    def _refactorDataStructure(data):
        ''' Change data structure
        '''
        refactoredData = list()
        for ele in data:
            temp = {'label': ele['label']}
            logs = _refactorLogsStructure(ele['logs'])
            temp['logs'] = logs
            refactoredData.append(temp)
        return refactoredData


    def _generateTable(self, dataSet):
        ''' Generate html table and write it to file
        '''
        htmlTableDir = os.path.join(self._cwd, 'results', 'html')
        mkpath(htmlTableDir)
        latexTableDir = os.path.join(self._cwd, 'results', 'latex')
        mkpath(latexTableDir)
        for data in dataSet:
            # generate branches comparison tables
            if len(self._branches) > 1:
                for tool in self._tools:
                    if data['label'] == tool:
                        filNam = os.path.join(htmlTableDir, "branches_compare_%s.html" % tool)
                        texTab = os.path.join(latexTableDir, "branches_compare_%s.tex" % tool)
                        # generate html table content
                        htmltext, flagModels = generateHtmlTable(data['logs'])
                        _generateFile(filNam, htmltext)
                        _generateTexTable(texTab, flagModels)
            # generate tools comparison tables
            if len(self._tools) > 1:
                for branch in self._branches:
                    if data['label'] == branch:
                        filNam = os.path.join(htmlTableDir, "tools_compare_%s.html" % branch)
                        texTab = os.path.join(latexTableDir, "tools_compare_%s.tex" % branch)
                        # generate html table content
                        htmltext, flagModels = generateHtmlTable(data['logs'])
                        _generateFile(filNam, htmltext)
                        _generateTexTable(texTab, flagModels)


    def _generateTexTable(filNam, models):
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
        for i in range(totalColumns-2):
            column = column + '''p{2cm}|'''
        column = column + 'p{1cm}|}' + os.linesep
        hline = '''\\hline''' + os.linesep
        # column head
        head = '''Model'''
        for i in range(len(log)):
            head = head + '''&$t_{%s}$ in [s]''' % log[i]['label'].replace('_', '\_')
        head = head + '''&$t_{2}/t_{1}$\\\\'''
        head = head +'''[2.5ex] \\hline''' + os.linesep
        row = ''
        for i in range(len(models)):
            ithModel = models[i]
            temp = ''
            fillColor = textTableColor(ithModel['relTim'])
            temp = '''\\rowcolor[HTML]{%s} ''' % fillColor + os.linesep
            temp = temp + '''{\\small ''' + '''\lstinline|''' + ithModel['model'].replace(f'{self._package}.','') + '''|}'''
            for j in range(len(log)):
                temp = temp + '&' + '{\\small ' + '{:.3f}'.format(ithModel['log'][j]['elapsed_time']) + '}'
            temp = temp + '&' + '{\\small ' + '{:.2f}'.format(ithModel['relTim']) + '}'
            temp = temp +'''\\\[2.5ex] \hline''' + os.linesep
            row = row + temp
        end = '''
\\end{longtable}
\\end{document}'''
        content = begin + column + captionLabel + hline + head + row + end
        _generateFile(filNam, content)


    def textTableColor(relTim):
        dif = relTim - 1 - tolRelTime if relTim > 1 else (1-relTim) - tolRelTime
        dR = 0.5
        dG = 0.1
        if dif < 0:
            color = 'FFFFFF'
        elif dif>=0:
            if relTim < 1:
                if dif >=0 and dif < dG:
                    color = 'edfef2'
                elif dif >= dG and dif < 2*dG:
                    color = 'dbfde4'
                elif dif >= 2*dG and dif < 3*dG:
                    color = 'c9fcd7'
                elif dif >= 3*dG and dif < 4*dG:
                    color = 'b6fbca'
                elif dif >= 4*dG and dif < 5*dG:
                    color = 'a4fbbc'
                elif dif >= 5*dG and dif < 6*dG:
                    color = '92faaf'
                elif dif >= 6*dG and dif < 7*dG:
                    color = '80f9a1'
                else:
                    color = '6ef894'
            else:
                if dif >=0 and dif < dR:
                    color = 'feeded'
                elif dif >= dR and dif < 2*dR:
                    color = 'fddbdb'
                elif dif >= 2*dR and dif < 3*dR:
                    color = 'fcc9c9'
                elif dif >= 3*dR and dif < 4*dR:
                    color = 'fbb6b6'
                elif dif >= 4*dR and dif < 5*dR:
                    color = 'fba4a4'
                elif dif >= 5*dR and dif < 6*dR:
                    color = 'fa9292'
                elif dif >= 6*dR and dif < 7*dR:
                    color = 'f98080'
                else:
                    color = 'f86e6e'
        return color


    def _generateFile(filNam, content):
        ''' Write html table to file
        '''
        with open(filNam, 'w+') as f:
            f.write(content)


    def chooseStyle(relTim, flag):
        # relTim is  (elaTim-t_0) / t_0
        dif = relTim - 1 - tolRelTime if relTim > 1 else (1-relTim) - tolRelTime
        dR = 0.5
        dG = 0.1
        style = 'normal'
        if dif>=0 and flag:
            if relTim < 1:
                if dif >=0 and dif < dG:
                    style = 'g-1'
                elif dif >= dG and dif < 2*dG:
                    style = 'g-2'
                elif dif >= 2*dG and dif < 3*dG:
                    style = 'g-3'
                elif dif >= 3*dG and dif < 4*dG:
                    style = 'g-4'
                elif dif >= 4*dG and dif < 5*dG:
                    style = 'g-5'
                elif dif >= 5*dG and dif < 6*dG:
                    style = 'g-6'
                elif dif >=6*dG and dif < 7*dG:
                    style = 'g-7'
                else:
                    style = 'g-8'
            else:
                if dif >=0 and dif < dR:
                    style = 'r-1'
                elif dif >= dR and dif < 2*dR:
                    style = 'r-2'
                elif dif >= 2*dR and dif < 3*dR:
                    style = 'r-3'
                elif dif >= 3*dR and dif < 4*dR:
                    style = 'r-4'
                elif dif >= 4*dR and dif < 5*dR:
                    style = 'r-5'
                elif dif >= 5*dR and dif < 6*dR:
                    style = 'r-6'
                elif dif >=6*dR and dif < 7*dR:
                    style = 'r-7'
                else:
                    style = 'r-8'
        return style


    def generateHtmlTable(data):
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
    .tg .tg-g-8{background-color:#6ef894;border-color:inherit;text-align:left;overflow:auto;vertical-align:center

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
        firstSimulationLog = data[0]['simulation']
        numberOfDataSet = len(firstSimulationLog)
        colWidth = 100/(3 + numberOfDataSet*3 + 1)

        # specify column style
        colGro = '''
            <table class="tg sortable" style="undefined">
                <colgroup>
            <col style="width: %.2f%%">
            ''' % (3*colWidth)
        for i in range(3*numberOfDataSet + 1):
            temp = '''<col style="width: %.2f%%">''' % colWidth + os.linesep
            colGro = colGro + temp
        colGro = colGro + '''</colgroup>''' + os.linesep

        # specify head
        heaGro = '''
             <tr>
                <th class="tg-head">Model</th>
            '''
        for i in range(numberOfDataSet):
            label = firstSimulationLog[i]['label']
            temp = '''
                <th class="tg-head">%s<br/>-<br/>Elapsed time (s)</td>
                <th class="tg-head">%s<br/>-<br/>State events</td>
                <th class="tg-head">%s<br/>-<br/>Jacobians</td>
            ''' % (label, label, label)
            heaGro = heaGro + temp
        heaGro = heaGro + '''<th class="tg-head">t<sub>2</sub>&frasl;t<sub>1</sub></th>''' + os.linesep
        heaGro = heaGro + '''</tr>''' + os.linesep

        # find total number of models
        numberOfModels = len(data)

        # write simulation logs of each model
        flagModelList = list()
        models = ''
        for i in range(numberOfModels):
            if numberOfDataSet > len(data[i]['simulation']):
                # This option was not simulated for all cases
                break

            modelData = '''<tr>''' + os.linesep
            flag = data[i]['flag']
            relTim = data[i]['relTim']
            tgStyle = 'tg-' + chooseStyle(relTim, flag)
            if flag:
                flagModelListTemp = {'model': data[i]['model']}
                flagModelListTemp['relTim'] = relTim
            temp1 = '''<td class="%s">%s</td>''' % (tgStyle, data[i]['model'])
            modelData = modelData + temp1 + os.linesep
            temp2 = ''
            temp3 = list()
            for j in range(numberOfDataSet):
                variableSet = data[i]['simulation'][j]['log']
                elapsed_time = variableSet['elapsed_time']
                state_events = variableSet['state_events']
                jacobians = variableSet['jacobians']
                flagTemp = {'elapsed_time': elapsed_time, \
                            'state_events': state_events, \
                            'jacobians': jacobians,
                            'label': data[i]['simulation'][j]['label']}
                temp3.append(flagTemp)
                temp2 = temp2 + '''
                    <td class="%s">%.4f</td>
                    <td class="%s">%d</td>
                    <td class="%s">%d</td>
                ''' % (tgStyle, elapsed_time, \
                       tgStyle, int(state_events), \
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
        for i in range(len(sortedList)):
            singleModel = sortedList[i]
            modelData = '''<tr>''' + os.linesep
            relTim = singleModel['relTim']
            tgStyle = 'tg-' + chooseStyle(relTim, True)
            modelName = singleModel['model']
            temp1 = '''<td class="%s">%s</td>''' % (tgStyle, modelName)
            modelData = modelData + temp1 + os.linesep
            temp2=''
            for j in range(len(singleModel['log'])):
                oneSet = singleModel['log'][j]
                temp2 = temp2 + '''
                    <td class="%s">%.4f</td>
                    <td class="%s">%d</td>
                    <td class="%s">%d</td>
                ''' % (tgStyle, oneSet['elapsed_time'], \
                       tgStyle, int(oneSet['state_events']), \
                       tgStyle, int(oneSet['jacobians']))
            modelData = modelData + temp2 + os.linesep
            modelData = modelData + '''<td class="%s">%.2f</td>''' % (tgStyle, relTim) + os.linesep
            modelData = modelData + '''</tr>''' + os.linesep
            flaggedModels = flaggedModels + os.linesep + modelData

        flagInfo = '''<br/>
                     <p><font size="+1.5">
                     Following models were flagged for which the maximum simulation time is greater than %.2f seconds
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
                        ''' % self._package
        allModels = colGro + heaGro + models + os.linesep + \
                    '''</table>'''

        # assembel html content
        htmltext = '''<html>''' + os.linesep + style + flagInfo + flagModels + allModelInfo + allModels + '''</html>'''
        return htmltext, sortedList


    def runCases(cases):
        ''' Run simulations
        '''
        lib_dir = _create_and_return_working_directory()
        self._clone_repository(lib_dir, FROM_GIT_HUB)
        for case in cases:
            d = _checkout_branch(lib_dir, case['branch'])
            case['commit'] = d['commit']
            _simulate(case, lib_dir)
        shutil.rmtree(lib_dir)


    def generateTables(self, cases):
        ''' Generate html tables
        '''
        logs = list()
        for case in cases:
            # filter simulation log
            temp = {'branch': case['branch'],
                    'tool': case['tool'],
                    'log': sortSimulationData(case)}
            logs.append(temp)

        toolsCompare = list()
        branchesCompare = list()

        # comparison between different branches with same tool
        if len(self._branches) > 1:
            for tool in self._tools: # [dymola, jmodelica]
                data = {'label': tool}
                temp = list()
                for log in logs:
                    if log['tool'] == tool:
                        branch = {'label': log['branch'],
                                  'log': log['log']}
                        temp.append(branch)
                data['logs'] = temp
                branchesCompare.append(data)
            # refactor data structure
            branchesData = _refactorDataStructure(branchesCompare)
            # generate html table file
            _generateTable(branchesData)

        # comparison between different tools on same branch
        if len(self._tools) > 1:
            for branch in self._branches:
                data = {'label': branch}
                temp = list()
                for log in logs:
                    if log['branch'] == branch:
                        toolLog = {'label': log['tool'],
                                   'log': log['log']}
                        temp.append(toolLog)
                data['logs'] = temp
                toolsCompare.append(data)
            # refactor data structure
            toolsData = _refactorDataStructure(toolsCompare)
            # generate html table file
            _generateTable(toolsData)
