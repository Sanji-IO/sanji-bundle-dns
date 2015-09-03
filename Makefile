all: pylint test

pylint:
	flake8 --exclude=tests,.git -v .
test:
	nosetests --with-coverage --cover-erase --cover-package=dns -v

.PHONY: pylint test
