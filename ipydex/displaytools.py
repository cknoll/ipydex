# -*- coding: utf-8 -*-

"""
This module was written by Carsten Knoll, see

https://github.com/cknoll/ipydex

This code is licensed under GPLv3


https://www.gnu.org/licenses/gpl-3.0.en.html


------------------------------------------------------------------------------

This module is an experimental ipython extension.

Provide special comments to display the 'result' of an assignment or to show similar information (like length or shape)



# load it with %load_ext ipydex.displaytools

usage:

`my_random_variable =  np.random.rand() ##:`

inserts the source line `display(my_random_variable)` to the source code,
that is actually executed.

That way, the notebook is more comprehensible beacause the reader knows
the content of `my_random_variable`. It saves the typing effort and the code
duplication of manually adding `display(my_random_variable)`.
"""

# Issues: SyntaxError points to the wrong line (due to display insertion)
# Note: this extension does not work properly with keywordargs: x = func(a, b=2)


# todo maybe use sp.Eq(sp.Symbol('Z1'), theta, evaluate=False) to get better formatting

import types
import collections
import ast
import textwrap
import re


import tokenize as tk

import IPython
from IPython.display import display
# noinspection PyUnresolvedReferences
from .core import Container, IPS, str_to_token_list


class FC(Container):
    """
    FlagContainer
    """

    def __init__(self, **kwargs):
        self.empty_comment = False
        self.sc = True  # just indicate that we have a special comment (default true servers as abbreviation)
        self.lhs = False  # relates to the comment
        self.assignment = None  # relates to the actual line (will be set later)
        self.transpose = False
        self.shape = False
        self.comment_only = None  # this refers to the whole line
        self.info = None  # this refers to the whole line
        self.multi_match = []

        kwargs["_allow_overwrite"] = True

        # TODO: when python2 support is dropped: change this to super().__init__(...)
        super(FC, self).__init__(**kwargs)


class LogicalLine(Container):
    def __init__(self, txt, tokens, start, end):
        # TODO: when python2 support is dropped: change this to super().__init__(...)
        super(LogicalLine, self).__init__()
        self.tokens = tokens
        self.txt = txt
        self.start = start
        self.end = end

    def __repr__(self):

        if self.txt.endswith("\n"):
            idx = -1
        else:
            idx = None
        return "<LL: {}>".format(self.txt[:idx])


# generate Special Comment Container

def def_special_comments():
    # _base = "##"
    plain = Container(c="##;", flags=FC())
    transpose = Container(c="##T", flags=FC(transpose=True))
    lhs_transpose = Container(c="##:T", flags=FC(lhs=True, transpose=True))
    lhs_shape = Container(c="##:S", flags=FC(lhs=True, shape=True))
    lhs_info = Container(c="##:i", flags=FC(lhs=True, info=True))
    lhs = Container(c="##:", flags=FC(lhs=True))  # this must be the last one in the list

    SCC = Container(cargs=(plain, transpose, lhs_transpose, lhs_shape, lhs_info, lhs))
    return SCC


SCC = def_special_comments()

sc_list = SCC.value_list()


ignorable_tokens = (tk.NEWLINE, tk.NL, tk.DEDENT, tk.ENDMARKER)
ignorable_final_tokens = (tk.DEDENT, tk.ENDMARKER)
aux_only_tokens = ignorable_tokens + (tk.INDENT, tk.COMMENT)


def preprocess_logical_line(ll):
    """
    # logical lines might start with physical lines which are only comments, or with empty physical lines.
    # we dont want strip that, except when the logical line does not contain any "real code" at all

    :param ll:

    :return: ll
    """

    ll.original_tokens = ll.tokens[:]
    ll.removed_start_txt = ""

    if all([(tok.type in aux_only_tokens) for tok in ll.tokens]):
        # this logical line does not do anything real (only comments an newlines)
        return ll

    ll.removed_plines = []
    ll.removed_comment_plines = []
    ll.removed_empty_plines = []

    while True:
        if ll.tokens[0].type == tk.COMMENT:
            assert ll.tokens[1].type == tk.NL
            rm_line = "".join((ll.tokens[0].string, ll.tokens[1].string))
            ll.removed_comment_plines.append(rm_line)
            ll.removed_plines.append(rm_line)
            ll.tokens = ll.tokens[2:]

        elif ll.tokens[0].type == tk.NL:
            rm_line = ll.tokens[0].string
            ll.removed_empty_plines.append(rm_line)
            ll.removed_plines.append(rm_line)
            ll.tokens = ll.tokens[1:]
        else:
            # tok is some "real" code
            break

    ll.no_removed_physical_lines = len(ll.removed_plines)
    ll.no_removed_empty_plines = len(ll.removed_empty_plines)
    ll.no_removed_comment_plines = len(ll.removed_comment_plines)
    ll.removed_start_txt = "".join(ll.removed_plines)

    # tag_issue_comment_at_end_of_indented_blocks
    # There is a known problem with all-comment lines at the end of indented blocks.
    # they are handled as the beginning of the next (not) indented logical line
    # mark this as special case

    # find length of leading whitespace of original string
    ll.lws_len = len(re.match(r"\s*", ll.txt, re.UNICODE).group(0))

    if ll.lws_len > 0 and ll.txt[ll.lws_len] == "#":
        ll.special_case_indendeted_comment_start = True
    else:
        ll.special_case_indendeted_comment_start = False

    return ll


def get_line_segments_from_logical_line(ll):
    """
    Split up a logical line into (indent, lhs, rhs, comment)

    lhs ist defined as the rightmost assignment

    (line does not need to be an assignment)

    :param ll:  LogicalLine object
    :return:
    """

    ll = preprocess_logical_line(ll)

    comment_strings = []
    comment_tokens = []
    initial_indent = ""

    for i, t in enumerate(ll.tokens):
        if t.type == tk.INDENT:
            initial_indent = t.string
        if t.type == tk.COMMENT:
            # store string_index and comment string
            comment_strings.append(t.string)
            comment_tokens.append(t)

    assert ll.tokens[-1].type in (tk.NEWLINE, tk.ENDMARKER)

    if not ll.txt.startswith(initial_indent):
        ll.txt = "{}{}".format(initial_indent, ll.txt)

    try:
        # look from behind if the first "relevant" token is a comment
        for tok in ll.tokens[::-1]:
            if tok.type in ignorable_tokens:
                continue
            if tok.type == tk.COMMENT:
                # useful for debugging
                final_comment_token = tok
                final_comment_start = tok.start
                break
        else:
            # no final comment
            # use the last token (except DEDENT and ENDMARKER) as virtual final comment
            for tok in ll.tokens[::-1]:
                if tok.type in ignorable_final_tokens:
                    continue
                break
            final_comment_token = tok
            final_comment_start = tok.start
            # be sure that in the last physical line there is no comment
            assert not any(t for t in ll.tokens if t.type == tk.COMMENT and t.start[0] == ll.tokens[-1].start[0])

    except IndexError:
        # this is an unexpected short line
        return "", None, None, ""

    try:
        # remove *common* leading whitespaces
        dedented_line = textwrap.dedent(ll.txt)
        if not dedented_line.startswith(ll.removed_start_txt):
            # this is unusual
            if not ll.special_case_indendeted_comment_start:
                # now this is unexpected
                msg = "unexpected indendation trouble"
                raise ValueError(msg)
            else:
                # see tag_issue_comment_at_end_of_indented_blocks
                if not dedented_line.startswith(" "*ll.lws_len + ll.removed_start_txt):
                    msg = "Currently not supported: comment line as last line of indented block "
                    raise ValueError(msg)

        # omit the leading linebreaks/comment-lines
        dedented_line = dedented_line[len(ll.removed_start_txt):]
        myast = ast.parse(dedented_line).body[0]

        # correct the start line and the start index of the final comment
        final_comment_start = (final_comment_start[0],
                               final_comment_start[1] - len(initial_indent))
    except (IndexError, SyntaxError):
        myast = None
        dedented_line = ""

    if isinstance(myast, ast.Assign):

        # noinspection PyBroadException
        try:
            lhs_container = get_lhs_from_ast(myast)
        except Exception as lhs_exception:
            # parsing errors are only relevant if there is a special comment at all
            lhs_container = Container(lhs_str=None, parsing_exception=lhs_exception)

        # right hand side is all left from the final comment (which might be "virtual")
        rhs = get_rhs_from_ast(myast, dedented_line, ll.no_removed_physical_lines, final_comment_start)
        rhs_start_line = myast.value.lineno - 1

        assert rhs_start_line >= 0

    else:
        lhs_container = Container(lhs_str=None, parsing_exception=None)
        rhs = dedented_line[0:final_comment_start[1]].strip()
        rhs_start_line = 0

    # in multiline strings, there might reside some comment strings inside rhs
    # we want to cancel them:
    # brute force replace will fail if the same string occurs inside a quote (regular code)

    if rhs == "":
        rhs = None
    else:
        old_rhs = rhs
        rhs_lines = rhs.split("\n")
        for ct in comment_tokens:
            line_idx = ct.start[0] - 1 - rhs_start_line - ll.no_removed_physical_lines
            line = rhs_lines[line_idx]
            if line.endswith(ct.string):
                # for single lines this and last physical line of a multiline-rhs this is not the case
                rhs_lines[line_idx] = line[:-len(ct.string)].rstrip()
        new_rhs = "\n".join(rhs_lines)
        if rhs.endswith("\n"):
            rhs = "{}\n".format(new_rhs)
        else:
            rhs = new_rhs

    comment = "".join(comment_strings).strip()

    return initial_indent, lhs_container, rhs, comment


def get_lhs_from_ast(myast):
    """
    Handle different possibilities for lhs (Tuple, numeric literal, )

    :param myast:       ast object
    :return:
    """

    t = myast.targets[-1]

    if isinstance(t, ast.Name):
        res = t.id
    elif isinstance(t, ast.Tuple):

        # example situation: C.x, y = 1, 2 (types: (ast.Attribute, ast.Name))

        seq_list = []
        for elt in t.elts:
            if isinstance(elt, ast.Name):
                seq_list.append(elt.id)
            elif isinstance(elt, ast.Attribute):
                seq_list.append(_resolove_ast_attribute(elt))
            else:
                msg = "Unexpected AST-type {} when evaluating lhs-tuple".format(type(elt))
                raise ValueError(msg)

        res = ", ".join(seq_list)

    elif isinstance(t, ast.Attribute):
        res = _resolove_ast_attribute(t)
    else:
        msg = "Unexpected AST-type when evaluating lhs"
        raise ValueError(msg)

    lhs_container = Container(lhs_str=res, parsing_exception=None)
    return lhs_container


def _resolove_ast_attribute(elt):
    """
    Handle the ast-object corresponding e.g. to `C.x.y.z`.

    :param elt: object of type ast.Attribute
    :return:         string representation of that object
    """

    assert isinstance(elt, ast.Attribute)

    res = []
    obj = elt
    # docstring example: obj.attr -> "z"; obj.value.attr -> "y"; obj.value.value.attr -> "x";
    # obj.value.value.value.id -> "C"
    while True:
        res.insert(0, obj.attr)
        if isinstance(obj.value, ast.Attribute):
            obj = obj.value
        else:
            break

    # ensure that we reached the end (i.e. beginning) of the chain: there must be a ast.Name-object
    assert isinstance(obj.value, ast.Name)
    res.insert(0, obj.value.id)

    return ".".join(res)


def get_rhs_from_ast(myast, txt, no_lines_removed, comment_start_tuple):
    """
    Handle different possibilities for rhs (expression, numeric literal, )

    :param txt:
    :param myast:       ast object
    :param no_lines_removed:
                        number of physical lines which have been removed by the caller (leading comment lines)
    :param comment_start_tuple:
                        2-tuple: (lineno, col_offset)
    :return:
    """

    physical_lines = txt.split("\n")
    # myast.value.lineno -> this is the line number (w.r.t 1, 2, 3, ...) where the assignation result starts
    # n_line := (myast.value.lineno - 1) is the number of lines above it -> physical_lines[:n_line] returns them
    n_line = myast.value.lineno - 1
    # count chars from previous lines (including the char "\n")
    previous_chars_start = sum(len(line) for line in physical_lines[:n_line]) + n_line

    start_idx = previous_chars_start + myast.value.col_offset

    # count chars from previous lines (including the char "\n") for the comment
    n_line = comment_start_tuple[0] - 1  # - no_lines_removed
    previous_chars_end = sum(len(line) for line in physical_lines[:n_line]) + n_line

    end_idx = previous_chars_end + comment_start_tuple[1]

    return txt[start_idx:end_idx].strip()


def classify_comment(cmt):

    if cmt == "":
        return FC(empty_comment=True, sc=False)

    assert cmt.startswith("#")

    res = None
    matchflag = False
    for sc in sc_list:
        if sc.c in cmt:
            if matchflag:
                # we have a multi match situation
                # ignore this for now
                res.multi_match.append(sc)
                continue
            matchflag = True

            res = sc.flags

    if res is None:
        res = FC(sc=False)

    return res


def is_single_name(expr):
    """
    Return whether an expression consists of a single name

    :param expr:
    :return:
    """

    tokens = str_to_token_list(expr)

    type_counter = collections.defaultdict(int)

    for t in tokens:
        type_counter[t.type] += 1

    # this is absent in Python2
    type_counter.pop(tk.NEWLINE, 0)

    res = type_counter[tk.NAME] == 1 and type_counter[tk.ENDMARKER] == 1 and len(type_counter) == 2

    return res


def process_line(line, line_flags, expr_to_disp, indent):
    """

    :param line:
    :param line_flags:
    :param expr_to_disp:     this is the expression which will be displayed ("x" or "x1, x2" or "a + b")
    :param indent:
    :return:
    """

    delim = "---"
    if line_flags.assignment and is_single_name(expr_to_disp):
        brace_str = "{}"
    else:
        brace_str = "({})"

    expr_to_disp = brace_str.format(expr_to_disp)

     # !! try ... eval(...) except SyntaxError ?
    if line_flags.transpose:
        expr_to_disp = "{}.T".format(expr_to_disp)

    print_delim = 'display({{"text/plain": "{}"}}, raw=True)'.format(delim)

    if line_flags.lhs:
        if line_flags.shape:
            new_line = '{}custom_display("{}.shape", {}.shape); {}'
            new_line = new_line.format(indent, expr_to_disp, expr_to_disp, print_delim)
        elif line_flags.info:
            new_line = '{}custom_display("info({})", _ipydex__info({})); {}'
            new_line = new_line.format(indent, expr_to_disp, expr_to_disp, print_delim)
        else:
            new_line = '{}custom_display("{}", {}); {}'.format(indent, expr_to_disp, expr_to_disp, print_delim)
    else:
        new_line = '{}display({}); {}'.format(indent, expr_to_disp, print_delim)

    return new_line


def insert_disp_lines(raw_cell):

    if "##!! raise TestException !!" in raw_cell:
        raise SyntaxError("Virtual syntax error (only for testing)")

    original_raw_cell = raw_cell
    raw_cell = raw_cell.strip()

    physical_lines = raw_cell.split('\n')
    logical_lines = get_logical_lines_of_cell(raw_cell)
    nphy = len(physical_lines)
    nlog = len(logical_lines)

    lines_of_new_cell = []

    # iterate from behind -> insert does not change the lower indices
    for i in range(nlog-1, -1, -1):
        # line = physical_lines[i]

        ll = logical_lines[i]

        # indent, lhs, rhs, cmt = get_line_segments(line)
        indent, lhs_container, rhs, cmt = get_line_segments_from_logical_line(ll)
        lhs_str = lhs_container.lhs_str
        cmt_flags = classify_comment(cmt)

        if rhs is None or not cmt_flags.sc:
            # no actual statement on that line or
            # no special comment
            lines_of_new_cell.insert(0, ll.txt)
            continue

        # we have a special comment

        # if there was an parsing exception earlier, now its time to raise it
        if lhs_container.parsing_exception:
            raise lhs_container.parsing_exception

        if lhs_str is not None:

            # situation
            # lhs = rhs ##: sc

            cmt_flags.assignment = True
            new_line = process_line(ll, cmt_flags, lhs_str, indent)
            lines_of_new_cell.insert(0, new_line)
            lines_of_new_cell.insert(0, ll.txt)
        else:
            # situation
            # rhs ##: sc

            # this line is not an assignment
            # -> it is replaced by `display(line)`
            # in practise this case is not so important
            cmt_flags.assignment = False
            new_line = process_line(ll, cmt_flags, rhs, indent)
            lines_of_new_cell.insert(0, new_line)
            # physical_lines[i] = new_line

    res = []
    for line in lines_of_new_cell:
        res.append("{}\n".format(line.rstrip()))
    new_raw_cell = "".join(res+[""])

    # there might still be lines like "    \n" in -> split and merge again
    new_raw_cell2 = "\n".join([line.rstrip() for line in new_raw_cell.split("\n")])

    # ensure the same number of "\n"-chars at the end
    # count original number
    lb_count = 0
    for c in original_raw_cell[::-1]:
        if c != "\n":
            break
        else:
            lb_count += 1

    new_raw_cell3 = "{}{}".format(new_raw_cell2.rstrip(), "\n"*lb_count)

    return new_raw_cell3


def custom_display(lhs, rhs):
    """
    lhs: left hand side
    rhs: right hand side

    This function serves to inject the string for the left hand side
    of an assignment
    """

    # This code is mainly copied from IPython/display.py
    # (IPython version 2.3.0)
    kwargs = {}
    raw = kwargs.get('raw', False)
    include = kwargs.get('include')
    exclude = kwargs.get('exclude')
    metadata = kwargs.get('metadata')

    from IPython.core.interactiveshell import InteractiveShell
    from IPython.core.displaypub import publish_display_data

    format = InteractiveShell.instance().display_formatter.format
    format_dict, md_dict = format(rhs, include=include, exclude=exclude)

    # example format_dict (for a sympy expression):
    # {u'image/png': '\x89PNG\r\n\x1a\n\x00 ...\x00\x00IEND\xaeB`\x82',
    #  u'text/latex': '$$- 2 \\pi \\sin{\\left (2 \\pi t \\right )}$$',
    # u'text/plain': u'-2\u22c5\u03c0\u22c5sin(2\u22c5\u03c0\u22c5t)'}

    # it is up to IPython which item value is finally used

    # now merge the lhs into the dict:

    if not isinstance(lhs, str):
        raise TypeError('unexpexted Type for lhs object: %s' %type(lhs))

    new_format_dict = {}
    for key, value in list(format_dict.items()):
        if 'text/plain' in key:
            prefix = "{} := ".format(lhs)
            if value.startswith("array") or value.startswith("matrix"):
                value = format_np_array(value, len(prefix))

            new_value = prefix + value
            new_format_dict[key] = new_value

        elif 'text/latex' in key:
            if value.startswith("$$"):
                # this is the expected case
                new_value = r"$$\verb|%s| := %s" % (lhs, value[2:])
                new_format_dict[key] = new_value
            else:
                # this is unexpected but raising an exceptions seems
                # not necessary; handle like plain text (see above)
                new_value = lhs+' := '+value
                new_format_dict[key] = new_value
        else:
            # this happens e.g. for mime-type (i.e. key) 'image/png'
            new_format_dict[key] = value

    # legacy IPython 2.x support
    if IPython.__version__.startswith('2.'):
        # noinspection PyTypeChecker
        publish_display_data('display', new_format_dict, md_dict)
    else:
        # indeed, I dont know with which version the api changed
        # but it does not really matter (for me)
        publish_display_data(data=new_format_dict, metadata=md_dict)


def info(arg):
    """
    Print some short and useful information about arg
    :param arg:
    :return:
    """

    C = Container()
    C.type = type(arg)
    C.shape = getattr(arg, "shape", None)
    C.len = getattr(arg, "__len__", None)

    # if symbtools is installed sympy objects have this property (shortcut for count ops)
    C.co = getattr(arg, "co", None)

    try:
        tmp = float(arg)
    except (TypeError, ValueError):

        C.is_number = False
    else:
        C.is_number = tmp == arg

    res = "{} with {}: {}"
    if C.is_number:
        final = res.format(C.type, "value", arg)
    elif C.co is not None:
        final = res.format(C.type, "count_ops", C.co)
    elif C.shape is not None:
        final = res.format(C.type, "shape", C.shape)
    elif C.len is not None:
        final = res.format(C.type, "length", len(arg))
    else:
        final = res.format(C.type, "str repr", str(arg))

    return final


def get_np_linewidth():
    try:
        # noinspection PyPackageRequirements
        import numpy as np
    except ImportError:
        # numpy not available
        # unexpected situation but not critical
        # return the default

        # noinspection PyUnusedLocal
        np = None  # make pycharm happy
        return 75
    return np.get_printoptions().get('linewidth', 75)


def format_np_array(value, prefixlen):
    lw = get_np_linewidth()
    rows = value.split("\n")
    if len(rows[0]) + prefixlen > lw:
        # inserting prefix will cause linebreaks (or they will occur anyway)
        # start the array at a new line
        rows.insert(0, "")# + [r.strip() for r in rows]
        separation = "\n"
    else:
        # there is enough space to insert the prefix and
        # shift every row to the right appropriately
        separation = "\n" + " "*prefixlen

    return separation.join(rows)


def get_logical_lines_of_cell(raw_cell):

    physical_lines = raw_cell.split("\n")

    tokens = str_to_token_list(raw_cell)

    logical_lines_tk_list = [[]]
    last_tok = None
    for tok in tokens:
        # append tok to the last list
        logical_lines_tk_list[-1].append(tok)
        if tok.type == tk.NEWLINE:
            # append a new empty list
            logical_lines_tk_list.append([])

        last_tok = tok  # for debugging

    assert logical_lines_tk_list[-1][-1].type == tk.ENDMARKER
    if 0 and len(logical_lines_tk_list) > 1 and len(logical_lines_tk_list[-1]) == 1:
        # if the last logical line only consists of ENDMARKER
        logical_lines_tk_list.pop()  # ignore last token

    logical_lines = []
    for ll_tokens in logical_lines_tk_list:
        # .start is a 2-tuple: (lineno, col_offset)
        start_line = ll_tokens[0].start[0] - 1
        end_line = ll_tokens[-1].end[0] - 1

        # to track the indentation independently from preceding lines,
        # we perform tokenization again for each logical line

        txt = "\n".join(physical_lines[start_line:end_line+1]).rstrip() + "\n"
        new_tokens = str_to_token_list(txt)

        ll = LogicalLine(txt, new_tokens, start_line, end_line)
        logical_lines.append(ll)

    return logical_lines


def load_ipython_extension(ip):

    def new_run_cell(self, raw_cell, *args, **kwargs):

        # noinspection PyBroadException
        try:
            new_raw_cell = insert_disp_lines(raw_cell)
        except Exception as e:
            msg = "There was an error in the displaytools extension (probably due to unsupported syntax).\n"\
                  "This is the error message:\n\n{}\n\n"\
                  "We leave this cell unchanged."
            print(msg.format(e))
            new_raw_cell = raw_cell

        q = 0
        if q:
            # debug
            print("cell:")
            print(raw_cell)
            print("new_cell:")
            print(new_raw_cell)
            print('-'*5)

        return ip.old_run_cell(new_raw_cell, *args, **kwargs)

    # prevent unwanted overwriting when the extension is reloaded
    if 'new_run_cell' not in str(ip.run_cell):
        ip.old_run_cell = ip.run_cell

    ip.run_cell = types.MethodType(new_run_cell, ip)
    ip.user_ns['display'] = display
    ip.user_ns['custom_display'] = custom_display
    ip.user_ns['_ipydex__info'] = info

