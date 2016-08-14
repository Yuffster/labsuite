#!/bin/sh
git stash -q --keep-index --no-gpg-sign
echo "Stashing working copy."
echo "Running tests."
nosetests
RESULT=$?
echo "Restoring working copy."
git stash pop -q
[ $RESULT -ne 0 ] && exit 1
exit 0