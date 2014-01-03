BPDIR=buildingspy
BPDOC=doc

.PHONY: doc clean

doc:
	(cd $(BPDOC); make html linkcheck)

unittest:
	python -m unittest discover buildingspy/tests
#	python buildingspy/tests/test_io_postprocess.py

doctest:
	python -m doctest \
	buildingspy/io/*.py \
	buildingspy/examples/*.py \
	buildingspy/examples/dymola/*.py \
	buildingspy/simulate/*.py \
        buildingspy/development/*.py
	rm plot.pdf plot.png roomTemperatures.png

dist:	clean doc 
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
