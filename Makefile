BPDIR=buildingspy
BPDOC=doc

.PHONY: doc clean

doc:
	(cd $(BPDOC); make html linkcheck)

pep8:
	pep8 buildingspy/io/*.py \
	buildingspy/examples/*.py \
	buildingspy/examples/dymola/*.py \
	buildingspy/simulate/*.py \
        buildingspy/development/*.py

unittest:
	python -m unittest discover buildingspy/tests
#	python buildingspy/tests/test_simulate_Simulator.py
#	python buildingspy/tests/test_io_postprocess.py

doctest:
	python -m doctest \
	buildingspy/fmi/*.py \
	buildingspy/io/*.py \
	buildingspy/examples/*.py \
	buildingspy/examples/dymola/*.py \
	buildingspy/simulate/*.py \
        buildingspy/development/*.py
	@rm -f plot.pdf plot.png roomTemperatures.png dymola.log

dist:	clean doctest unittest doc 
	@# Make sure README.rst are consistent
	cmp -s README.rst buildingspy/README.rst
	python setup.py sdist --formats=gztar,zip
	python setup.py bdist_egg
	@rm -rf build
	@rm -rf buildingspy.egg-info
	@echo "Source distribution is in directory dist"
	@echo "To post to server, run postBuildingsPyToWeb.sh"

clean-dist:
	rm -rf build
	rm -rf buildingspy.egg-info
	rm -rf buildingspy-*
	rm -rf dist

clean-doc:
	(cd $(BPDOC); make clean)

clean: clean-doc clean-dist
