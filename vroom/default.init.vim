" Copyright 2017 The Chromium Authors.
"
" Use of this source code is governed by a BSD-style
" license that can be found in the LICENSE file or at
" https://developers.google.com/open-source/licenses/bsd.

exec 'set rtp+=' . fnameescape(fnamemodify(getcwd(), ':p:h:h'))
set hidden

let g:codesearch_test_data_dir = fnamemodify(getcwd(), ':p')

call crcs#PrepareForTesting()

