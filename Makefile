
ADDONS=`cd addons && find * -maxdepth 0 -type d -not -name ".git" -not -name "debian"`
INSTALL_DIR=$(DESTDIR)/usr/share/pyshared/openerp/addons

SOURCE_FILES=`find -name "*.xml" -or -name "*.js" -or -name "*.py" -or -name "*.html" -or -name "*.po" -or -name "*.pot"`
IMAGE_FILES=`find -name "*.png"`
CLEAN_FILES=`find -name "*.pyc"`

build:
	@true

clean:
	@true

install:
	@mkdir -p $(INSTALL_DIR)
	@rm -f $(CLEAN_FILES)
	@for i in $(ADDONS) ; do \
		cp -R --preserve addons/$$i $(INSTALL_DIR) ;	\
		find $(INSTALL_DIR)/$$i -name "*.pyc" | xargs rm -f ; \
	done

policy:
	@for i in $(SOURCE_FILES) ; do dos2unix -q "$$i" ; done
	@chmod ugo-x $(SOURCE_FILES) $(IMAGE_FILES)
	@for i in `find -name "*.xml"` ; do xmlindent -t -w "$$i" && rm -f "$$i~"; done
