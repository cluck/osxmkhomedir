# Makefile

## Copyright (c) 2015, Claudio Luck (Zurich, Switzerland)
##
## Licensed under the terms of the MIT License, see LICENSE file.

mkfile_path := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
PYTHON := python
EGG := birdlist
EGGDIR := osxmkhomedir

all:
	@echo "Usage: make prepare"

# ------------------

prepare: .eggs/stamp-prepare.swp

.eggs/stamp-prepare.swp: .eggs/stamp-virtualenv.swp setup.py Makefile requirements.txt
	PYTHONPATH=./$(shell python -c "from distutils.dist import Distribution;d=Distribution({});\
	    i=d.get_command_obj('install');i.finalize_options();print(i.install_lib)") \
	./$(shell python -c "from distutils.dist import Distribution;d=Distribution({});\
	    i=d.get_command_obj('install');i.finalize_options();print(i.install_scripts)")/virtualenv -p "$(PYTHON)" .
	bin/pip install --upgrade setuptools pip virtualenv
	bin/pip install -r requirements.txt
	touch .eggs/stamp-prepare.swp

.eggs/stamp-virtualenv.swp: .eggs/stamp-pip.swp
	PYTHONPATH=./$(shell python -c "from distutils.dist import Distribution;d=Distribution({});\
	    i=d.get_command_obj('install');i.finalize_options();print(i.install_lib)") \
	./$(shell python -c "from distutils.dist import Distribution;d=Distribution({});\
	    i=d.get_command_obj('install');i.finalize_options();print(i.install_scripts)")/pip \
	    install --ignore-installed --root "$(mkfile_path)" virtualenv
	touch .eggs/stamp-virtualenv.swp

.eggs/stamp-pip.swp:
	mkdir -p .eggs
	which pip 2>/dev/null && \
	pip install --upgrade --ignore-installed --root="$(mkfile_path)" pip && \
	touch .eggs/stamp-pip.swp || true
	test -e .eggs/stamp-pip.swp || \
	cp -n .eggs/get-pip.py get-pip.py || \
	python3 -c 'import urllib.request ; urllib.request.urlretrieve(\
	    "https://bootstrap.pypa.io/get-pip.py", "get-pip.py")' || \
	python -c 'import urllib2 ; f=open("get-pip.py","w") ; \
	    f.write(urllib2.urlopen(\
	    "https://bootstrap.pypa.io/get-pip.py").read())'
	test -e .eggs/stamp-pip.swp || cp -n get-pip.py .eggs/get-pip.py
	test -e .eggs/stamp-pip.swp || \
	python get-pip.py --ignore-installed --root="$(mkfile_path)"
	touch .eggs/stamp-pip.swp

# ------------------

clean:
	find . -name \*.pyc -name \*.pyo -exec rm "{}" \; || true
	find . .eggs -name __pycache__ -type d -exec rm -r "{}" \; || true
	find . -name __pycache__ -type d -exec rm -r "{}" \; || true

distclean: clean
	rm -vrf usr parts build dist develop-eggs
	rm -vrf local bin include lib lib64 Library .Python
	rm -vrf *.egg-info
	rm -vf ./.mr.developer.cfg ./.installed.cfg pyenv.cfg
	rm -vf pip-selfcheck.json

allclean: distclean
	rm -rf .eggs get-pip.py

# ------------------

.PHONY: prepare clean distclean allclean
