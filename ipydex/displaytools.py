# -*- coding: utf-8 -*-


"""
This module was written by Carsten Knoll, see

https://github.com/cknoll/ipydex

This code is licensed under GPLv3


https://www.gnu.org/licenses/gpl-3.0.en.html


------------------------------------------------------------------------------

This module is an experimental ipython extension.

Background: insert some logic to display the 'result' of an assignment



# load it with %reload_ext ipydex.displaytools

usage:

`my_random_variable =  np.random.rand() ##`

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

import tokenize as tk
import io

import IPython
from IPython.display import display
from .core import Container, IPS


class FC(Container):
    """
    FlagContainer
    """

    def __init__(self, **kwargs):
        self.empty_comment = False
        self.sc = True  # just indicate that we have a special comment (default true servers as abbreviation)
        self.lhs = False
        self.transpose = False
        self.shape = False
        self.comment_only = None  # this refers to the whole line
        self.multi_match = []

        kwargs["_allow_overwrite"] = True

        # TODO: when python2 support is dropped: change this to super().__init__(...)
        super(FC, self).__init__(**kwargs)


# generate Special Comment Container

def def_special_comments():
    # _base = "##"
    plain = Container(c="##;", flags=FC())
    lhs = Container(c="##:", flags=FC(lhs=True))
    transpose = Container(c="##T", flags=FC(transpose=True))
    lhs_transpose = Container(c="##:T", flags=FC(lhs=True, transpose=True))
    lhs_shape = Container(c="##:S", flags=FC(lhs=True, shape=True))

    SCC = Container(cargs=(plain, transpose, lhs_transpose, lhs_shape, lhs))
    return SCC


SCC = def_special_comments()

sc_list = SCC.value_list()


def classify_line_by_comment(line):

    tokens = tk.generate_tokens(io.StringIO(line).readline)

    for i, t in enumerate(tokens):
        if t.type == tk.COMMENT:
            if i == 0:
                res = FC(comment_only=True, sc=False)
            else:
                res = classify_comment(t.string)

            break
    else:  # no break
        res = FC(sc=False)

    return res


def get_line_segments(line):
    """
    Split up a line into lhs, rhs, comment, flags

    lhs ist defined as the leftmost assignment

    (line does not need to be an assignment)
    
    :param line: 
    :return: lhs, rhs, comment 
    """
    line = line.strip()

    tokens = tk.generate_tokens(io.StringIO(line).readline)

    equality_signs = [-1]
    comment_tuple = None, ""
    for i, t in enumerate(tokens):
        if t.type == tk.COMMENT:
            # store string_index and comment string
            comment_tuple = t.start[1], t.string
        if t.type == tk.OP and t.string == "=":
            equality_signs.append(t.start[1])

    if len(equality_signs) > 1:
        # we have at least one assignment
        lhs = line[equality_signs[-2]+1:equality_signs[-1]].strip()
        equality_signs.pop(0)
    else:
        lhs = None

    rhs_start_idx = equality_signs[-1] + 1

    # from the last `=` until the beginning of the comment
    rhs = line[rhs_start_idx:comment_tuple[0]].strip()
    if rhs == "":
        rhs = None
    comment = comment_tuple[1].strip()

    return lhs, rhs, comment


def classify_comment(cmt):

    if cmt == "":
        return FC(empty_comment=True)

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


def process_line(line, line_flags, disp_str):

    if line_flags.assignment:
        delim = "---"
        brace_str = "%s"
    else:
        delim = "___"
        brace_str = "(%s)"

     #!! try ... eval(...) except SyntaxError ?
    if line_flags.transpose:
        disp_str = brace_str % disp_str
        disp_str += '.T'
    if line_flags.lhs:
        new_line = 'custom_display("%s", %s); print("%s")' % (disp_str, disp_str, delim)
    else:
        new_line = 'display(%s); print("%s")' % (disp_str, delim)

    return new_line


def insert_disp_lines(raw_cell):
    lines = raw_cell.split('\n')
    N = len(lines)

    # iterate from behind -> insert does not change the lower indices
    for i in range(N-1, -1, -1):
        line = lines[i]
        # line_flags = eval_line_end(line)
        line_flags = classify_line_by_comment(line)

        lhs, rhs, cmt = get_line_segments(line)

        if line_flags.comment_only:
            continue

        if line_flags.sc:
            if line[0] in [' ', '#']:
                # this line is part of a comment or indented block
                # -> ignore
                continue

            # TODO: delegate this to tokenize
            if ' = ' in line:
                idx = line.index(' = ')
                var_str = line[:idx].strip()
                line_flags.assignment = True
                new_line = process_line(line, line_flags, var_str)
                lines.insert(i+1, new_line)
            else:
                # this line is not an assignment
                # -> it is replaced by `display(line)`
                # in practise this case is not so important
                idx = line.index("##")
                disp_str = line[:idx]
                line_flags.assignment = False
                new_line = process_line(line, line_flags, disp_str)
                lines[i] = new_line

    new_raw_cell = "\n".join(lines)

    return new_raw_cell


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
        publish_display_data('display', new_format_dict, md_dict)
    else:
        # indeed, I dont know with which version the api changed
        # but it does not really matter (for me)
        publish_display_data(data=new_format_dict, metadata=md_dict)


def get_np_linewidth():
    try:
        import numpy as np
    except ImportError:
        # numpy not available
        # unexpected situation but not critical
        # return the default
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


def load_ipython_extension(ip):

    def new_run_cell(self, raw_cell, *args, **kwargs):

        new_raw_cell = insert_disp_lines(raw_cell)

        if 0:
            #debug
            print("cell:")
            print(raw_cell)
            print("new_cell:")
            print(new_raw_cell)
            print('-'*5)
            #print("args", args)
            #print("kwargs", kwargs)

        return ip.old_run_cell(new_raw_cell, *args, **kwargs)

    # prevent unwanted overwriting when the extension is reloaded
    if not 'new_run_cell' in str(ip.run_cell):
        ip.old_run_cell = ip.run_cell

    ip.run_cell = types.MethodType(new_run_cell, ip)
    ip.user_ns['display'] = display
    ip.user_ns['custom_display'] = custom_display

