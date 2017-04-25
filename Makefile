BPDIR=buildingspy
BPDOC=doc

PEP8_ARGS=--recursive --max-line-length=100 \
  --exclude="*/thirdParty/*" \
  --select="E114,E222,E225,E231,E261,E262,E271,E301,E302,E303,E305,E401,E501,E703,E711,E712,E771,W291,W293,W391" buildingspy

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
	python -m unittest discover buildingspy/tests
#	python buildingspy/tests/test_development_error_dictionary.py

doctest:
	python -m doctest \
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
	python setup.py sdist --formats=gztar,zip
	python setup.py bdist_egg
	rm -rf build
	rm -rf buildingspy.egg-info
	twine upload dist/*
	@echo "Source distribution is in directory dist"
	@echo "To post to server, run postBuildingsPyToWeb.sh"


upload-test:
	@# Make sure README.rst are consistent
	cmp -s README.rst buildingspy/README.rst
	python setup.py sdist --formats=gztar,zip bdist_egg upload -r https://testpypi.python.org/pypi

clean-dist:
	rm -rf build
	rm -rf buildingspy.egg-info
	rm -rf buildingspy-*
	rm -rf dist

clean-doc:
	(cd $(BPDOC); make clean)

clean: clean-doc clean-dist
