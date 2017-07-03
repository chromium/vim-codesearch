#! /usr/bin/env bash

set -e

{
  cd vroom/
  vroom --neovim --vimrc default.init.vim .
}

