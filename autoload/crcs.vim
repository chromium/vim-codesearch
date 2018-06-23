" Copyright 2017 The Chromium Authors.
"
" Use of this source code is governed by a BSD-style
" license that can be found in the LICENSE file or at
" https://developers.google.com/open-source/licenses/bsd.

" Sets up a buffer for displaying pre-rendered codesearch output.
function! crcs#SetupCodesearchBuffer(bufname, dirname, buftype)
  if exists("s:cs_buffer_" . a:buftype)
    if bufexists(s:cs_buffer_{a:buftype})
      exec 'buffer' s:cs_buffer_{a:buftype}

      if a:dirname != ''
	let b:cs_root_path = a:dirname
      endif
      exec 'file' fnameescape(a:bufname)
      return s:cs_buffer_{a:buftype}
    endif
  endif

  " Will fail if hidden is not set
  enew
  let s:cs_buffer_{a:buftype} = bufnr('$')
  let b:cs_buftype = a:buftype

  syn clear
  syn sync fromstart

  " Include cpp.vim under @embddedC. Currently this is only used to link
  " highlight groups that are defined in c.vim and cpp.vim. This way we'll
  " hopefully apply the correct theme settings when displaying code snippets.
  " 
  " Optionally we can defer highlighting of embedded code snippets entirely to
  " c.vim/cpp.vim by something like:
  "   syn region csEmbeddedCpp start=... end=... contains=@embddedC
  syn include @embddedC $VIMRUNTIME/syntax/cpp.vim
  unlet b:current_syntax

  " csMarkedupCode is a generic container for formatted code snippets based on
  " codesearch responses. Any markup that's applied based on FormatGroup
  " should be described in this section.
  syn cluster csFormatGroups contains=csKeyword,csString,csComment,csNumber,csMacro,csClass,csConst,csDeprecatd,csQueryMatch,csLineNum

  syn region csMacro concealends matchgroup=csConceal start=/\^D{/ end=/}D_/ contained
  syn region csClass concealends matchgroup=csConceal start=/\^C{/ end=/}C_/ contained
  syn region csConst concealends matchgroup=csConceal start=/\^K{/ end=/}K_/ contained
  syn region csNumber concealends matchgroup=csConceal start=/\^0{/ end=/}0_/ contained
  syn region csEscape concealends matchgroup=csConceal start=/\^\\{/ end=/}\\_/ contained
  syn region csString concealends matchgroup=csConceal start=/\^s{/ end=/}s_/ contained contains=@csFormatGroups
  syn region csComment concealends matchgroup=csConceal start=/\^c{/ end=/}c_/ contained contains=@csFormatGroups
  syn region csKeyword concealends matchgroup=csConceal start=/\^k{/ end=/}k_/ contained
  syn region csDeprecatd concealends matchgroup=csConceal start=/\^-{/ end=/}-_/ contained
  syn region csQueryMatch concealends matchgroup=csConceal start=/\^\${/ end=/}\$_/ contained
  syn match csLineNum /^  *\d*/ contained contains=NONE
  syn match csContinuation /\[\.\.\.\]/ contains=NONE
  
  syn region csMarkedupCode concealends matchgroup=csConceal start=/\^>{/ end=/}>_/ transparent contains=@csFormatGroups

  syn region csQuery concealends matchgroup=csConceal start=/\^q{/ end=/}q_/

  hi def link csKeyword cStatement
  hi def link csString cString
  hi def link csComment cComment
  hi def link csNumber cNumber
  hi def link csMacro cPreProc
  hi def link csClass cppStructure
  hi def link csConst cConstant
  hi def link csEscape cSpecial
  hi def link csDeprecatd cSpecial
  hi def link csQueryMatch Underlined
  hi def link csConceal Conceal
  hi def link csLineNum Comment
  hi def link csContinuation Comment
  hi def link csQuery Special
  
  " High level syntax groups for describing search results.
  if a:buftype ==# 'search'
    if has('conceal')
      syn region csMatchFileSpec start=/^\d*\. /rs=s end=/\^>{$/me=e-3,re=e contains=csMatchNum,csMatchFileName keepend
    else
      syn region csMatchFileSpec start=/^\d*\. /rs=s end=/$/ contains=csMatchNum,csMatchFileName keepend
    endif
    syn match csMatchNum /^\d*\./he=e-1 contained nextgroup=csMatchFileName
    syn match csMatchFileName / .*$/hs=s+1 contained
    hi def link csMatchFileName Directory
    hi def link csMatchNum Number

    nnoremap <buffer> <silent> [[ :call crcs#JumpToNextFile()<CR>
    nnoremap <buffer> <silent> ]] :call crcs#JumpToPrevFile()<CR>
  endif

  " Xref results
  if a:buftype ==# 'xref'
    syn region csCategory concealends matchgroup=csConceal start=/\^Cat{/ end=/}Cat_/ contains=NONE nextgroup=csFilename
    syn region csFilename concealends matchgroup=csConceal start=/\^F{/ end=/}F_/ contains=NONE nextgroup=csLine
    syn match csLine /^ *\d+:/me=e-1 nextgroup=csMarkedupCode
    hi def link csCategory Special
    hi def link csLine LineNr
    hi def link csFilename Directory

    nnoremap <buffer> <silent> [[ :call crcs#JumpToNextFile()<CR>
    nnoremap <buffer> <silent> ]] :call crcs#JumpToPrevFile()<CR>
  endif

  if a:buftype ==# 'call'
    syn region csNode concealends matchgroup=csConceal start=/\^N{/ end=/}N_/ contains=csNode,csExpander,csSymbol,csMarkedupCode,csFilename nextgroup=csExpander transparent
    syn match csExpander /\[[-+\*]\]/ nextgroup=csSymbol
    syn region csSymbol concealends matchgroup=csConceal start=/\^S{/ end=/}S_/ nextgroup=csFilename contained
    syn region csFilename concealends matchgroup=csConceal start=/\^F{/ end=/}F_/ contains=NONE nextgroup=csMarkedupCode

    hi def link csExpander Special
    hi def link csSymbol Directory

    nnoremap <buffer> <silent> za :call crcs#OpenCallgraphFold()<CR>
    nnoremap <buffer> <silent> zc :call crcs#CloseCallgraphFold()<CR>
  endif
  
  let b:cs_root_path = ""
  if a:dirname != ''
    let b:cs_root_path = a:dirname
  endif

  setlocal buftype=nofile
  setlocal noswapfile
  setlocal nomodifiable
  setlocal nospell
  setlocal conceallevel=3
  setlocal concealcursor=nc
  setlocal cursorline
  setlocal nonumber
  setlocal norelativenumber

  exec 'file' fnameescape(a:bufname)
  exec 'au BufDelete <buffer> call crcs#OnBufferUnload(expand("<abuf>"), "' . a:buftype . '")'

  nnoremap <buffer> <CR> :call crcs#JumpToContext()<CR>
  let b:current_syntax = 'codesearch'

  return s:cs_buffer_{a:buftype}
endfunction

let s:cs_buffer = -1
let s:initialized = 0
let s:plugin_root = resolve(expand('<sfile>:p:h:h'))

" This needs to be called from a BufDelete auto command where |bufnr| is set
" to <abuf> and the |buftype| is set to the type of the buffer.
function! crcs#OnBufferUnload(bufnr, buftype)
  if s:cs_buffer_{a:buftype} == a:bufnr
    let s:cs_buffer_{a:buftype} = -1
  endif
  exec 'py' 'CleanupBuffer(' . a:bufnr . ')'
endfunction

function! crcs#Setup()
  if s:initialized
    return
  endif
  let s:initialized = 1

  py import sys
  py import os
  exec "py CR_CS_PYTHON_ROOT = r'" . s:plugin_root . "'"
  exec "pyf" fnameescape(s:plugin_root . "/vimsupport.py")

  if !has('conceal')
    py DisableConcealableMarkup()
  endif

  if !has('hidden')
  endif
endfunction

function! crcs#CodeSearch(query)
  call crcs#Setup()
  exec 'py' 'RunCodeSearch("' . fnameescape(a:query) . '")'
endfunction

function! crcs#JumpToContext()
  " Should only be called after initialization. Check just in case.
  if s:initialized != 1
    return
  endif
  py JumpToContext()
endfunction

function! crcs#XrefSearch()
  call crcs#Setup()
  py RunXrefSearch()
endfunction

function! crcs#Callgraph()
  call crcs#Setup()
  py RunCallgraphSearch()
endfunction

function! crcs#JumpToCallers()
  call crcs#Setup()
  let l:callers=pyeval('GetCallers()')
  if l:callers != ''
    cexpr l:callers
  endif
endfunction

function! crcs#JumpToNextFile()
  py JumpToNextFile()
endfunction

function! crcs#JumpToPrevFile()
  py JumpToPrevFile()
endfunction

function! crcs#RefTypeCompleter(arglead, cmdline, cursorpos)
  call crcs#Setup()
  return pyeval("ReferenceTypeCompleter('" . a:arglead . "', '" . a:cmdline . "', '" . a:cursorpos . "')")
endfunction

function! crcs#GoToRef(t)
  call crcs#Setup()
  let l:refs = pyeval("GetReferences('" . a:t . "')")
  if length(l:refs) != 0
    cexpr l:refs
  endif
endfunction

function! crcs#ShowAnnotationsHere()
  call crcs#Setup()
  py ShowAnnotationsHere()
endfunction

function! crcs#ShowSignature()
  call crcs#Setup()
  py ShowSignature()
endfunction

function! crcs#OpenCallgraphFold()
  " Should only be called from a callgraph buffer.
  py RunCallgraphSearch()
endfunction

function! crcs#CloseCallgraphFold()
  " Should only be called from a callgraph buffer.
  py CloseCallgraphFold()
endfunction

function! crcs#PrepareForTesting()
  call crcs#Setup()
  py PrepareForTesting()
endfunction
