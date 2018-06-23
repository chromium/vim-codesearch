#! /usr/bin/env bash

# Copyright 2017 The Chromium Authors.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd.

# Rebaselines the tests after a change to the layout logic. Please examine the
# resulting .expected files to make sure the output is correct.
#
# Cannot be used to "rebaseline" the inputs. See the README.md file in this
# directory for details.

pushd `dirname ${BASH_SOURCE[0]}` > /dev/null
python -m unittest discover .. "test_*.py"
for json_file in *.json; do
  if [ -r ${json_file}.actual ]; then
    cp ${json_file}.actual ${json_file}.expected
    git add ${json_file}.expected
  fi
done
popd > /dev/null

echo "Don't forget to check and commit the updated .expected files"
