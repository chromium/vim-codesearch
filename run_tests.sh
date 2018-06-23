#! /usr/bin/env bash

set -e

python -m unittest discover

if [ ${VIM_FLAVOR:-neovim} == neovim ]; then
  flags=--neovim
else
  flags=
fi

{
  cd vroom/
  vroom $flags --vimrc default.init.vim .
}

