  
install:
	@echo Nothing to be done for inst_servers as pure python

clean:
	-del *.pyc *.pyd *.pyo

.DEFAULT:
	@echo Nothing to be done for inst_servers as pure python

.PHONY:
	runtests

runtests:
	$(PYTHON) run_all_tests.py && $(PYTHON3) run_all_tests.py
