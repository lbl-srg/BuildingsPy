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

.PHONY: doc clean venv clean-pycache check-deps

define CHECK_DEPS_SCRIPT
import ast
import pathlib
import re
import sys

PINNED_PKG_RE = re.compile(r"^[A-Za-z0-9_.-]+==[A-Za-z0-9_.*+-]+\Z")


def load_pyproject(path):
    try:
        import tomllib
        with open(path, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        try:
            import tomli as tomllib
            with open(path, "rb") as f:
                return tomllib.load(f)
        except ImportError:
            pass
    text = path.read_text(encoding="utf-8")
    data = {"build-system": {}, "project": {"optional-dependencies": {}}}
    section = None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            i += 1
            continue
        for key, target in [
            ("requires", ("build-system", "requires")),
            ("dependencies", ("project", "dependencies")),
            ("dev", ("project.optional-dependencies", "dev")),
        ]:
            if section == target[0] and re.match(rf"^{key}\s*=\s*\[", line):
                buf = [line.split("=", 1)[1]]
                while "]" not in buf[-1] and i + 1 < len(lines):
                    i += 1
                    buf.append(lines[i])
                val = ast.literal_eval("\n".join(buf))
                if target[0] == "project.optional-dependencies":
                    data["project"]["optional-dependencies"]["dev"] = val
                else:
                    data[target[0]][target[1]] = val
        i += 1
    return data


def read_requirements(path):
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def check_pinned(req, source):
    pkg_part = req.split(";", 1)[0].strip()
    if not PINNED_PKG_RE.match(pkg_part):
        return [f"{source}: unpinned dependency '{req}' (expected 'package==version')"]
    return []


errors = []
req_lines = read_requirements(pathlib.Path("requirements.txt"))
for req in req_lines:
    errors.extend(check_pinned(req, "requirements.txt"))

doc_req_path = pathlib.Path("doc/requirements.txt")
if doc_req_path.exists():
    for req in read_requirements(doc_req_path):
        errors.extend(check_pinned(req, "doc/requirements.txt"))

pyproject = load_pyproject(pathlib.Path("pyproject.toml"))
build_reqs = pyproject.get("build-system", {}).get("requires", [])
core_reqs = pyproject.get("project", {}).get("dependencies", [])
dev_reqs = pyproject.get("project", {}).get("optional-dependencies", {}).get("dev", [])

for req in build_reqs + core_reqs + dev_reqs:
    errors.extend(check_pinned(req, "pyproject.toml"))

pyproject_all = set(core_reqs + dev_reqs)
requirements_all = set(req_lines)

only_in_pyproject = sorted(pyproject_all - requirements_all)
only_in_requirements = sorted(requirements_all - pyproject_all)

if only_in_pyproject:
    errors.append(
        f"In pyproject.toml but missing from requirements.txt: {only_in_pyproject}"
    )
if only_in_requirements:
    errors.append(
        f"In requirements.txt but missing from pyproject.toml: {only_in_requirements}"
    )

if errors:
    for err in errors:
        print(f"ERROR: {err}", file=sys.stderr)
    sys.exit(1)
endef
export CHECK_DEPS_SCRIPT

check-deps:
	@echo "*** Checking that dependencies are pinned and consistent"
	@python3 -c "$$CHECK_DEPS_SCRIPT"

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

dist:	venv clean doc check-deps
	@# Make sure README.rst are consistent
	cmp -s README.rst buildingspy/README.rst
	$(PYTHON) -m build
	rm -rf build
	rm -rf buildingspy.egg-info
	find buildingspy -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null
	$(VENV)/bin/twine check dist/*
	@echo "Source distribution is in directory dist"
	@echo "To post to server, run postBuildingsPyToWeb.sh"
	@echo "To upload to PyPi, run 'twine upload dist/*'"

upload-test: venv
	@# Make sure README.rst are consistent
	cmp -s README.rst buildingspy/README.rst
	$(VENV)/bin/twine upload --verbose --repository buildingspy_test dist/*

upload: venv
	@# Make sure README.rst are consistent
	cmp -s README.rst buildingspy/README.rst
	$(VENV)/bin/twine upload --repository buildingspy_production_upload dist/*

clean-pycache:
	find buildingspy -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true

clean-dist: clean-pycache
	rm -rf build
	rm -rf buildingspy.egg-info
	rm -rf buildingspy-*
	rm -rf dist
	rm -rf funnel_comp dymola openmodelica comparison-*.log simulator-*.log

clean-doc:
	(cd $(BPDOC); make clean)

clean-venv:
	rm -rf $(VENV)
	(cd $(BPDOC); make clean-venv)

clean: clean-doc clean-dist
