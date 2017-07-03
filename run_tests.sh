#! /usr/bin/env bash

set -e

if [ ${VIM_FLAVOR:-neovim} == neovim ]; then
  flags=--neovim
else
  flags=
fi

{
  cd vroom/
  vroom $flags --vimrc default.init.vim .
}

