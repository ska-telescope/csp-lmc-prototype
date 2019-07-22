#!/usr/bin/env bash
echo "STATIC CODE ANALYSIS"
echo "===================="
echo

echo "MODULE ANALYSIS"
echo "---------------"
pylint --rcfile=.pylintrc csplmc/CspMaster/CspMaster
pylint --rcfile=.pylintrc csplmc/CspSubarray/CspSubarray

echo "TESTS ANALYSIS"
echo "--------------"
pylint --rcfile=.pylintrc csplmc/CspMaster/test
pylint --rcfile=.pylintrc csplmc/CspSubarray/test
