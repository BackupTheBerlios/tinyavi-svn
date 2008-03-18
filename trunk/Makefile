# Makefile for TinyAVI video converter

.SUFFIXES: .po .pot .mo

VERSION=$(shell cat VERSION)

# Default target - do nothing
all:
	@echo "Make one of the following targets:"
	@echo "	install		install the library and tools"
	@echo "	clean		remove all generated files"
	@echo "	update-po	update all po files with new strings from sources"
	@echo "	dist		make a distribution archive"

install:
	python setup.py install

dist:
	rm -rf tinyavi-$(VERSION)
	mkdir tinyavi-$(VERSION) tinyavi-$(VERSION)/po \
	      tinyavi-$(VERSION)/share  tinyavi-$(VERSION)/tinyavi
	cp -a po/*.po* tinyavi-$(VERSION)/po
	cp -a share/*.glade share/*.svg tinyavi-$(VERSION)/share
	cp -a tinyavi/*.py tinyavi-$(VERSION)/tinyavi
	cp -a COPYING CHANGELOG Makefile README TRANSLATORS VERSION \
	      setup.py tavi tavi-gui tavi.desktop tinyavi-$(VERSION)
	tar cvjf tinyavi-$(VERSION).tar.bz2 tinyavi-$(VERSION)
	rm -rf tinyavi-$(VERSION)

clean:
	rm -f tinyavi/*.pyc *.log
	rm -rf build dist tinyavi-$(VERSION)

# Update translation files
update-po: $(wildcard po/*.po)

po/%.po: $(wildcard share/*.glade) $(wildcard tinyavi/*.py) tavi tavi-gui
	@(xgettext --omit-header $(filter %.glade,$^) -o - ; \
	 xgettext --omit-header -L python $(filter-out %.glade,$^) -o -) | \
	msgmerge $@ - -o $@
