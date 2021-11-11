.PHONY: help install test prepare

.DEFAULT: help
help:
	@echo "make install"
	@echo "       build the executable binary for the project"
	@echo "make test"
	@echo "       run the unittests"
	@echo "make prepare"
	@echo "       install all python dependencies"

test:
	python -m unittest discover -s tests

install:
	pyinstaller -n exchange app.py --onefile
	mv dist/exchange .

prepare:
	python -m pip install -r requirements.txt