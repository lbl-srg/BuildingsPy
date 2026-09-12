BPDIR=buildingspy
BPDOC=doc

PEP8_ARGS=--recursive --max-line-length=100 \
  --exclude="*/thirdParty/*,buildingspy/development/openmodelica_run.template" \
  --ignore="E402" \
  --aggressive --aggressive --aggressive \
  buildingspy

VENV := .venv
PYTHON := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

$(VENV)/bin/activate: requirements.txt
	rm -rf buildingspy.egg-info
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .
	touch $(VENV)/bin/activate

venv: $(VENV)/bin/activate

.PHONY: doc clean venv

doc:
	@echo "*** Verifying that readme file used by git and pip are consistent"
	cmp -s README.rst buildingspy/README.rst
	@echo "*** Generating documentation"
	(cd $(BPDOC); make html linkcheck)

pep8: venv
ifeq ($(PEP8_CORRECT_CODE), true)
	@echo "*** Running autopep8 to correct code"
	$(VENV)/bin/autopep8 --in-place $(PEP8_ARGS)
	@echo "*** Checking for required code changes (apply with 'make pep8 PEP8_CORRECT_CODE=true')"
	git diff --exit-code .
else
	@echo "*** Checking for required code changes (apply with 'make pep8 PEP8_CORRECT_CODE=true')"
	$(VENV)/bin/autopep8 --diff $(PEP8_ARGS)
endif

unittest: venv
	# To run a single test, use
	# python buildingspy/tests/test_development_regressiontest_optimica.py Test_regressiontest_optimica_Tester.test_regressiontest_diagnostics
	$(PYTHON) -m unittest discover buildingspy/tests

unittest_development_error_dictionary: venv
	$(PYTHON) buildingspy/tests/test_development_error_dictionary.py

unittest_development_merger: venv
	$(PYTHON) buildingspy/tests/test_development_merger.py

unittest_development_refactor: venv
	$(PYTHON) buildingspy/tests/test_development_refactor.py

unittest_development_regressiontest_openmodelica: venv
	$(PYTHON) buildingspy/tests/test_development_regressiontest_openmodelica.py

unittest_development_regressiontest_optimica: venv
	$(PYTHON) buildingspy/tests/test_development_regressiontest_optimica.py

unittest_development_regressiontest: venv
	$(PYTHON) buildingspy/tests/test_development_regressiontest.py

unittest_development_Validator: venv
	$(PYTHON) buildingspy/tests/test_development_Validator.py

unittest_development_Comparator: venv
	$(PYTHON) buildingspy/tests/test_development_Comparator.py

unittest_examples_dymola: venv
	$(PYTHON) buildingspy/tests/test_examples_dymola.py

unittest_io_outputfile: venv
	$(PYTHON) buildingspy/tests/test_io_outputfile.py

unittest_io_postprocess: venv
	$(PYTHON) buildingspy/tests/test_io_postprocess.py

unittest_simulate_Dymola: venv
	$(PYTHON) buildingspy/tests/test_simulate_Dymola.py

unittest_simulate_OpenModelica: venv
	$(PYTHON) buildingspy/tests/test_simulate_OpenModelica.py

singleTest: venv
	$(PYTHON) buildingspy/tests/test_simulate_OpenModelica.py Test_simulate_Simulator.test_addMethods

unittest_simulate_Optimica: venv
	$(PYTHON) buildingspy/tests/test_simulate_Optimica.py

unittest_simulate_Simulator: venv
	$(PYTHON) buildingspy/tests/test_simulate_Simulator.py

doctest: venv
	$(PYTHON) -m doctest \
	buildingspy/fmi/*.py \
	buildingspy/io/*.py \
	buildingspy/examples/*.py \
	buildingspy/examples/dymola/*.py \
	buildingspy/simulate/*.py \
	buildingspy/development/*.py
	@rm -f plot.pdf plot.png roomTemperatures.png dymola.log MyModel.mat dslog.txt package.order \
	   run_simulate.mos run_translate.mos simulator.log translator.log

dist:	venv clean doc
	@# Make sure README.rst are consistent
	cmp -s README.rst buildingspy/README.rst
	$(PYTHON) setup.py sdist bdist_wheel
	rm -rf build
	rm -rf buildingspy.egg-info
	twine check dist/*
	@echo "Source distribution is in directory dist"
	@echo "To post to server, run postBuildingsPyToWeb.sh"
	@echo "To upload to PyPi, run 'twine upload dist/*'"

upload-test:
	@# Make sure README.rst are consistent
	cmp -s README.rst buildingspy/README.rst
	twine upload --verbose --repository buildingspy_test dist/*

upload:
	@# Make sure README.rst are consistent
	cmp -s README.rst buildingspy/README.rst
	twine upload --repository buildingspy_production_upload dist/*


clean-dist:
	rm -rf build
	rm -rf buildingspy.egg-info
	rm -rf buildingspy-*
	rm -rf dist
	rm -rf funnel_comp dymola openmodelica __pycache__ comparison-*.log simulator-*.log

clean-doc:
	(cd $(BPDOC); make clean)

clean-venv:
	rm -rf $(VENV)
	(cd $(BPDOC); make clean-venv)

clean: clean-doc clean-dist clean-venv
