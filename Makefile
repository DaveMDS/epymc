#
# A simple and stupid Makefile for EpyMC.
#
# This is mainly targeted at lazy devlopers (like me) that
# want to type less, use autocompletion or do not want to 
# learn the python setup syntax.
#
# Usage:
#
# make <cmd>            to build using the default python interpreter
# make <cmd> PY=pythonX to build using the specified python interpreter
#


PY = python


.PHONY: build
build:
	$(PY) setup.py build


.PHONY: themes
themes:
	$(PY) setup.py build_themes


.PHONY: install
install:
	$(PY) setup.py install


.PHONY: uninstall
uninstall:
	$(PY) setup.py uninstall


.PHONY: clean
clean:
	$(PY) setup.py clean --all


.PHONY: update_po
update_po:
	$(PY) setup.py update_po


