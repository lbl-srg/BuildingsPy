BPDIR=buildingspy
BPDOC=doc

PEP8_ARGS=--recursive --max-line-length=100 \
  --exclude="*/thirdParty/*" \
  --ignore="E402" \
  --aggressive --aggressive --aggressive \
  buildingspy


.PHONY: doc clean

doc:
	(cd $(BPDOC); make html linkcheck)

pep8:
ifeq ($(PEP8_CORRECT_CODE), true)
	@echo "*** Running autopep8 to correct code"
	autopep8 --in-place $(PEP8_ARGS)
	@echo "*** Checking for required code changes (apply with 'make pep8 PEP8_CORRECT_CODE=true')"
	git diff --exit-code .
else
	@echo "*** Checking for required code changes (apply with 'make pep8 PEP8_CORRECT_CODE=true')"
	autopep8 --diff $(PEP8_ARGS)
endif

unittest:
	# To run a single test, use
	# python buildingspy/tests/test_development_regressiontest_jmodelica.py Test_regressiontest_jmodelica_Tester.test_regressiontest_diagnostics
	python -m unittest discover buildingspy/tests

doctest:
	python3 -m doctest \
	buildingspy/fmi/*.py \
	buildingspy/io/*.py \
	buildingspy/examples/*.py \
	buildingspy/examples/dymola/*.py \
	buildingspy/simulate/*.py \
	buildingspy/development/*.py
	@rm -f plot.pdf plot.png roomTemperatures.png dymola.log MyModel.mat dslog.txt package.order \
	   run_simulate.mos run_translate.mos simulator.log translator.log

dist:	clean doctest unittest doc
	@# Make sure README.rst are consistent
	cmp -s README.rst buildingspy/README.rst
	python setup.py sdist bdist_wheel
	rm -rf build
	rm -rf buildingspy.egg-info
	@echo "Source distribution is in directory dist"
	@echo "To post to server, run postBuildingsPyToWeb.sh"
	@echo "To upload to PyPi, run 'twine upload dist/*'"


upload-test:
	@# Make sure README.rst are consistent
	cmp -s README.rst buildingspy/README.rst
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*
#	python setup.py sdist --formats=gztar,zip bdist_egg upload -r https://testpypi.python.org/pypi

upload:
	@# Make sure README.rst are consistent
	cmp -s README.rst buildingspy/README.rst
	twine upload dist/*


clean-dist:
	rm -rf build
	rm -rf buildingspy.egg-info
	rm -rf buildingspy-*
	rm -rf dist

clean-doc:
	(cd $(BPDOC); make clean)

clean: clean-doc clean-dist
