# Copyright 2017 The Chromium Authors.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd.

import os
import sys
import re
from contextlib import contextmanager

import codesearch as cs

# For type checking. Not needed at runtime.
try:
  from typing import Any, Optional, List, Dict, Union, Type, Tuple
except ImportError:
  pass

SNIPPET_INDENT = 4

TAG_START_FORMAT = '^{:s}{{'
TAG_END_FORMAT = '}}{:s}_'


def StartTag(s):
  assert isinstance(s, str)
  return TAG_START_FORMAT.format(s)


def EndTag(s):
  assert isinstance(s, str)
  return TAG_END_FORMAT.format(s)


RE_BLOCK_START_META = re.compile(r'\^[^{]+{')
RE_BLOCK_END_META = re.compile(r'}[^_]+_')


def CountBlockMarkupOverhead(s):
  # type: (str) -> int
  """\
  Return the number of characters that have been used up by |s| for
  markup.

  Only counts complete tags. I.e. "^S{foo}S_" will
  return 6:

  >>> CountBlockMarkupOverhead("^S{foo}S_")
  6

  , but CountBlockMarkupOverhead("^S{foo}S") will return 3.

  >>> CountBlockMarkupOverhead("^S{foo}S")
  3
  """
  return len(''.join(RE_BLOCK_START_META.findall(s))) + \
      len(''.join(RE_BLOCK_END_META.findall(s)))


@contextmanager
def TaggedBlock(mapper, block_type):
  '''\
  Context for writing the contents of a tagged block. Automatically writes the
  start and end blocks with no additional newlines.

  Use as:
     with TaggedBlock(mapper, 'x'):
        mapper.write(...)
  '''
  mapper.write(StartTag(block_type))
  yield
  mapper.write(EndTag(block_type))


class LocationMapper(object):

  def __init__(self):
    self.jump_map_ = {}
    self.signature_map_ = {}
    self.lines_ = ['']

  def SetSignatureForLine(self, sig):
    current_line = len(self.lines_) - 1
    self.signature_map_[current_line] = sig

  def SetTargetForPos(self, fn, line):
    assert line > 0
    current_line = len(self.lines_) - 1
    self.jump_map_[current_line] = (fn, line - 1, self.column())

  def column(self):
    return len(self.lines_[-1])

  def write(self, s):
    assert isinstance(s, str)
    lines = s.split('\n')
    self.lines_[-1] += lines[0]
    self.lines_.extend(lines[1:])

  def newline(self):
    self.lines_.extend([''])

  def Lines(self):
    return self.lines_

  def JumpTargetAt(self, line, column):
    # line and column are counting from 1
    assert line > 0
    assert column > 0
    line -= 1
    column -= 1
    if line not in self.jump_map_:
      candidates = [l for l in self.jump_map_.keys() if l < line]
      if len(candidates) == 0:
        return None
      line = max(candidates)
    filename, target_line, offset_column = self.jump_map_[line]
    if offset_column < column:
      overhead = CountBlockMarkupOverhead(
          self.lines_[line][offset_column:column])
      target_column = column - offset_column - overhead
      assert target_column >= 0
    else:
      target_column = 0
    return (filename, target_line + 1, target_column + 1)

  def PreviousFileLocation(self, line):
    current_file, _, _ = self.jump_map_.get(line, ('', 0, 0))

    line -= 2
    while line >= 1:
      f, _, _ = self.jump_map_.get(line, ('', 0, 0))
      if f and f != current_file:
        new_file = f
        break
      line -= 1

    old_line = line
    line -= 1
    while line >= 1:
      f, _, _ = self.jump_map_.get(line, ('', 0, 0))
      if f != new_file:
        return old_line + 1
      old_line = line
      line -= 1
    return 1

  def NextFileLocation(self, line):
    original_line = line
    current_file, _, _ = self.jump_map_.get(line, ('', 0, 0))
    while line <= len(self.lines_):
      f, _, _ = self.jump_map_.get(line, ('', 0, 0))
      if f and f != current_file:
        return line + 1
      line += 1
    return original_line

  def SignatureAt(self, line):
    assert line > 0
    line -= 1
    if line not in self.signature_map_:
      candidates = [l for l in self.signature_map_.keys() if l < line]
      if len(candidates) == 0:
        return None

      line = max(candidates)
    return self.signature_map_[line]


def GetBlockTypeFromFormatType(r):
  return {
      cs.FormatType.SYNTAX_KEYWORD: 'k',
      cs.FormatType.SYNTAX_STRING: 's',
      cs.FormatType.SYNTAX_COMMENT: 'c',
      cs.FormatType.SYNTAX_NUMBER: '0',
      cs.FormatType.SYNTAX_MACRO: 'D',
      cs.FormatType.SYNTAX_CLASS: 'C',
      cs.FormatType.SYNTAX_CONST: 'K',
      cs.FormatType.SYNTAX_ESCAPE_SEQUENCE: '\\',
      cs.FormatType.SYNTAX_DEPRECATED: '-',
      cs.FormatType.SYNTAX_KEYWORD_STRONG: 'k',
      cs.FormatType.QUERY_MATCH: '$',
      cs.FormatType.SNIPPET_QUERY_MATCH: '$'
  }.get(r, None)


def RenderAnnotatedText(mapper,
                        annotated_text,
                        indent,
                        filename,
                        first_line_number=1):
  text_lines = annotated_text.text.split('\n')

  # Max number of digits it takes to represent the line number
  line_number_width = len(str(first_line_number + len(text_lines) - 1))

  insertions = []

  for r in annotated_text.range:
    block_type = GetBlockTypeFromFormatType(r.type)
    if block_type is None:
      continue
    if r.range.end_column == 1 and r.range.start_line != r.range.end_line:
      r.range.end_line -= 1
      r.range.end_column = len(text_lines[r.range.end_line - 1]) + 1
    insertions.append((r.range.end_line, r.range.end_column,
                       EndTag(block_type)))
    insertions.append((r.range.start_line, r.range.start_column,
                       StartTag(block_type)))

  insertions.sort(
      lambda i1, i2: i2[0] - i1[0] if i2[0] != i1[0] else i2[1] - i1[1])

  for line, column, tag in insertions:
    assert line > 0
    assert column > 0
    line -= 1
    column -= 1
    text = text_lines[line]
    text_lines[line] = text[:column] + tag + text[column:]

  for index, text in enumerate(text_lines):
    mapper.newline()
    mapper.write(' ' * indent)
    mapper.write('{:{}d} '.format(index + first_line_number, line_number_width))
    mapper.SetTargetForPos(filename, index + first_line_number)
    mapper.write(text)


def RenderSnippet(mapper,
                  s_index,
                  snippet,
                  filename,
                  level=1,
                  aux_first_line_number=1):
  first_line_number = snippet.first_line_number if snippet.first_line_number else aux_first_line_number
  if s_index != 0:
    mapper.newline()
    mapper.write(' ' * SNIPPET_INDENT * level)
    mapper.write('[...]')
    mapper.SetTargetForPos(filename, first_line_number)
  RenderAnnotatedText(mapper, snippet.text, SNIPPET_INDENT * level, filename,
                      first_line_number)


def RenderSearchResult(mapper, index, search_result):
  filename = search_result.top_file.file.name
  mapper.SetTargetForPos(filename, 1)
  mapper.write('{}. {}'.format(index + 1, filename))
  for s_index, snippet in enumerate(search_result.snippet):
    with TaggedBlock(mapper, '>'):
      RenderSnippet(mapper, s_index, snippet, filename)
  mapper.newline()


def RenderSearchResponse(mapper, query, search_response):
  assert isinstance(search_response, cs.SearchResponse)

  if search_response.search_result:
    mapper.write('CodeSearch results for ')
    with TaggedBlock(mapper, 'q'):
      mapper.write(query)
    mapper.newline()
    mapper.newline()

    for index, result in enumerate(search_response.search_result):
      RenderSearchResult(mapper, index + search_response.results_offset, result)
      mapper.newline()

    if search_response.hit_max_results:
      mapper.write(
          'Search results are truncated. Showing {} results out of an estimated {}.'.
          format(
              len(search_response.search_result),
              search_response.estimated_total_number_of_results))
      mapper.newline()
  else:
    mapper.write('No results for query ')
    with TaggedBlock(mapper, 'q'):
      mapper.write(query)
    mapper.newline()
    mapper.newline()

    if search_response.status_message:
      mapper.write('Server status: {}'.format(search_response.status_message))
      mapper.newline()
    mapper.write('Status code  : {}'.format(search_response.status))
    mapper.newline()


def RenderXrefResults(mapper, results):

  def XrefResultSorter(r1, r2):
    if r1[0].name == r2[0].name:
      return cmp(r1[1].line_number, r2[1].line_number)
    return cmp(r1[0].name, r2[0].name)

  results.sort(cmp=XrefResultSorter)

  last_fn = None
  for result in results:
    fn, m = result
    if fn.name != last_fn:
      if last_fn is not None:
        mapper.newline()
      last_fn = fn.name
      mapper.write(' ' * 2)
      mapper.SetTargetForPos(fn.name, 1)
      with TaggedBlock(mapper, 'F'):
        mapper.write(fn.name)
      mapper.newline()
    mapper.write('{indent:s}{line:d}:  '.format(
        indent=' ' * 4, line=m.line_number))
    mapper.SetTargetForPos(last_fn, m.line_number)
    with TaggedBlock(mapper, '>'):
      mapper.write(m.line_text)
    mapper.newline()


def RenderXrefSearchResponse(mapper, xref_search_response):
  # Failed?
  if xref_search_response.status != 0:
    mapper.write('No results for query\n')
    if xref_search_response.status_message:
      mapper.write('Server status: {}'.format(
          xref_search_response.status_message))
    mapper.write('Status code  : {}'.format(xref_search_response.status))
    return

  class Bin:

    def __init__(self, name, order):
      self.name = name
      self.order = order

      # Each element in the list is a tuple, of which the first element
      # is a cs.FileSpec, and the second element is a XrefSingleMatch.
      self.bin = []

  collectors = {
      cs.KytheXrefKind.DEFINITION: Bin('Definition', 1),
      cs.KytheXrefKind.DECLARATION: Bin('Declaration', 2),
      cs.KytheXrefKind.CALLED_BY: Bin('Called by', 3),
      cs.KytheXrefKind.INSTANTIATION: Bin('Instantiations', 4),
      cs.KytheXrefKind.OVERRIDDEN_BY: Bin('Overridden by', 5),
      cs.KytheXrefKind.OVERRIDES: Bin('Overrides', 6),
      cs.KytheXrefKind.EXTENDED_BY: Bin('Extended by', 7),
      cs.KytheXrefKind.EXTENDS: Bin('Extends', 8),
      cs.KytheXrefKind.GENERATES: Bin('Generates', 9),
      cs.KytheXrefKind.GENERATED_BY: Bin('Generated by', 10),
      cs.KytheXrefKind.ANNOTATES: Bin('Annotates', 11),
      cs.KytheXrefKind.ANNOTATED_BY: Bin('Annotated by', 12),

      # Everything else.
      0: Bin('References', 100)
  }

  for search_result in xref_search_response.search_result:
    for match in search_result.match:
      if match.type_id in collectors:
        target_bin = collectors[match.type_id]
      else:
        target_bin = collectors[0]
      target_bin.bin.append((search_result.file, match))

  bins = collectors.values()
  bins.sort(key=lambda b: b.order)

  for ref_bin in bins:
    if len(ref_bin.bin) == 0:
      continue
    with TaggedBlock(mapper, 'Cat'):
      mapper.write('{}:\n'.format(ref_bin.name))
    RenderXrefResults(mapper, ref_bin.bin)
    mapper.newline()


NODE_INDENT = 4


# Shorten display names by adding elided sections for template parameters.
def AbbreviateCppSymbol(s):
  s = s.replace('<anonymous-namespace>', '{}')
  short = ''
  template_count = 0
  for c in s:
    if c == '>':
      template_count -= 1

    if template_count == 0:
      short += c

    if c == '<':
      template_count += 1
      if template_count == 1:
        short += '...'
  return short


def RenderNode(mapper, node, level):

  with TaggedBlock(mapper, 'N'):
    # Rendered text looks like:
    #
    # [-] namespace::Bar() (filename.cc)
    #     38   InvokeBaz(1, 2, true);
    #
    #     [+] Quux() (filename.cc)
    #         10   Bar()
    #

    # Widget
    mapper.SetSignatureForLine(node.signature)

    if node.children:
      expander = '[-]' if len(node.children) > 0 else ' * '
    else:
      expander = '[+]'

    mapper.write('{indent}{expander} '.format(
        indent=' ' * (level * NODE_INDENT), expander=expander))

    # Symbol
    if node.file_path and node.identifier:
      with TaggedBlock(mapper, 'S'):
        if node.call_scope_range.start_line:
          start_line = node.call_scope_range.start_line
        elif node.call_site_range.start_line:
          start_line = node.call_site_range.start_line
        else:
          start_line = 1
        mapper.SetTargetForPos(node.file_path, start_line)
        mapper.write(AbbreviateCppSymbol(node.identifier))
      mapper.write(' ')
      with TaggedBlock(mapper, 'F'):
        mapper.write(node.file_path)

    # Render snippet
    if node.snippet_file_path:
      aux_first_line_number = node.call_site_range.start_line \
          if node.call_site_range.start_line else 1
      with TaggedBlock(mapper, '>'):
        RenderSnippet(mapper, 0, node.snippet, node.snippet_file_path,
                      level + 1, aux_first_line_number)
        mapper.newline()
    else:
      mapper.newline()

    # Add some padding. Otherwise it looks too "busy".
    mapper.newline()

    for c in node.children:
      RenderNode(mapper, c, level + 1)


def RenderCompoundResponse(compound_response, query):
  mapper = LocationMapper()

  if compound_response.search_response:
    assert isinstance(compound_response.search_response, list)
    assert len(compound_response.search_response) == 1
    RenderSearchResponse(mapper, query, compound_response.search_response[0])

  elif compound_response.xref_search_response:
    assert isinstance(compound_response.xref_search_response, list)
    assert len(compound_response.xref_search_response) == 1
    RenderXrefSearchResponse(mapper, compound_response.xref_search_response[0])

  elif compound_response.call_graph_response:
    assert isinstance(compound_response.call_graph_response, list)
    assert len(compound_response.call_graph_response) == 1
    RenderNode(mapper, compound_response.call_graph_response[0].node, 0)

  else:
    raise Exception("Unknown response type")

  return mapper


def DisableConcealableMarkup():
  global TAG_START_FORMAT
  global TAG_END_FORMAT

  TAG_START_FORMAT = ''
  TAG_END_FORMAT = ''
