# Use bash shell with pipefail option enabled so that the return status of a
# piped command is the value of the last (rightmost) commnand to exit with a
# non-zero status. This lets us pipe output into tee but still exit on test
# failures.
SHELL = /bin/bash
.SHELLFLAGS = -o pipefail -c

all: test lint

# wait for the device to be available before beginning the test
# A temporary volume is mounted at /build when 'make test' is executing.
# The following steps copy across useful output to this volume which can
# then be extracted to form the CI summary for the test procedure.
test:
	retry --max=10 -- tango_admin --ping-device mid_csp_cbf/sub_elt/master
	retry --max=10 -- tango_admin --ping-device mid_csp_cbf/sub_elt/subarray_01
	retry --max=10 -- tango_admin --ping-device mid_csp_cbf/sub_elt/subarray_02
	retry --max=10 -- tango_admin --ping-device mid_csp/elt/master
	retry --max=10 -- tango_admin --ping-device mid_csp/elt/subarray_01
	retry --max=10 -- tango_admin --ping-device mid_csp/elt/subarray_02
	cd /app/csplmc/CspSubarray && python setup.py test | tee setup_py_test.stdout
	cd /app/csplmc/CspMaster && python setup.py test | tee setup_py_test.stdout
	mkdir -p /build/reports; \
	mv /app/csplmc/CspMaster/setup_py_test.stdout /build/csp_master_setup_test.stdout; \
	mv /app/csplmc/CspMaster/htmlcov /build/csp_master_htmlcov; \
	mv /app/csplmc/CspMaster/coverage.xml /build/csp_master_coverage.xml; \
	mv /app/csplmc/CspSubarray/setup_py_test.stdout /build/csp_subarray_setup_test.stdout; \
	mv /app/csplmc/CspSubarray/htmlcov /build/csp_subarray_htmlcov; \
	mv /app/csplmc/CspSubarray/coverage.xml /build/reports/code-coverage.xml; 
lint:
	pip3 install pylint2junit; \
        mkdir -p /build/reports; \
        cd /app && pylint --output-format=parseable csplmc | tee /build/code_analysis.stdout; \
	cd /app && pylint --output-format=pylint2junit.JunitReporter csplmc > /build/reports/linting.xml;


.PHONY: all test lint
