# -*- coding: utf-8 -*-


import collections
import inspect
import sys
import os
import tokenize as tk
import io
import pickle
import subprocess
import dataclasses

import stack_data
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.styles import get_style_by_name

from IPython.terminal.ipapp import load_default_config
from IPython.terminal.embed import InteractiveShellEmbed
from IPython.core import ultratb

from IPython.core.debugger import Pdb

sys_orig_excepthook = sys.excepthook

# Licence: GPLv3
#  (full text: http://www.gnu.org/licenses/gpl-3.0-standalone.html)
# Origin: a coobook example extended by Carsten Knoll for personal needs
# Please send bug reports via Email
# "Carsten.+".replace('+', 'Knoll@') + "tu-dresden.de"


"""
Module which offers an slightly enhanced IPython shell and other tools
which might be helpful for debugging and exploring.


typical use cases:

from ipydex import ip_syshook, IPS,  activate_ips_on_exception
activate_ips_on_exception()

# some code ...

IPS()  # call the IPython shell to interactively investigate the situaion

--

# access to the commandline debugger

from ipydex import TracerFactory
ST = TracerFactory()
...
ST() # starts the debugger prompt ("Start Trace"); type 'help' to get started
in contrast to the IPython Shell the debugger allows to go stepwise through
the following code.

--

dirsearch # has nothing to do with ipython but may help to explore
the namespace. Example: import os; dirsearch('path', os)

--

known bugs:
- - - - - -

if used from within a PyQt app: annoying meassages

  "QCoreApplication::exec: The event loop is already running"

solution:
QtCore.pyqtRemoveInputHook() # to be called in __init__ of main-dialog-class


------------

the way colors are represented in a "normal" shell conflicts with embedded
shells in eclipse, pyscripter or spyder; result: ugly control characters

workarround: start your script from an externall shell

-----------

The embedded IPython-Shell seems to conflict with output suppressing in
the module py.test (for unittesting).

To avoid this, disable the output suppressing via:
py.test -s <testfiles>

-----------

There have been problems with pyparallel


-----------
-----------


If IPython is not installed, dummy objects are created.
This makes it possible to run code which import the ipHelp module on machines
where IPython is not available (useful for modules which are still under
development, but already are deployd on different machines/ platforms)

"""


# allow global write access to config vars of this module
module_config = dataclasses.dataclass()
module_config.COLOR_SCHEME = "Linux"




class DummyMod(object):
    """A dummy module used for IPython's interactive module when
    a name space must be assigned to the module's __dict__."""
    pass


def get_frame_list(frame=None, code_context=1, add_context_for_latest=0):
    """
    return the list of frames and frame_info_tuples in desceninding order (newest frame is last)
    """

    # TODO: use this function in IPS below (less code duplication)

    frame_info_list = []
    frame_list = []
    if not frame:
        frame = inspect.currentframe()
    while frame is not None:
        frame_list.append(frame)
        info = inspect.getframeinfo(frame, code_context)
        frame_info_list.append(info)
        frame = frame.f_back

    # special treatment for last frame:

    frame_info_list.reverse()
    frame_list.reverse()

    frame_info_list[-1] = inspect.getframeinfo(frame_list[-1], code_context + add_context_for_latest)

    return frame_list, frame_info_list


class InteractiveShellEmbedWithoutBanner(InteractiveShellEmbed):
    display_banner = False


# noinspection PyPep8Naming
def IPS(condition=True, frame=None, ns_extension=None, copy_namespaces=True, overwrite_globals=False,
        code_context=1, print_tb=True, add_context_for_latest=6, color_scheme=module_config.COLOR_SCHEME):
    """

    :param condition:           return immediately if False
    :param frame:
    :param ns_extension:
    :param copy_namespaces:
    :param overwrite_globals:
    :param code_context:
    :param print_tb:            boolean or negative integer (number of printed last tracebacks)
    :param add_context_for_latest:
    :param color_scheme:        (optional) one of ['Linux', 'NoColor', 'LightBG', 'Neutral']
    :return:

    Starts IPython embedded shell. This is similar to IPython.embed() but with some
    additional features:

    1. Print a list of the calling frames before entering the prompt
    2. (optionally) copy local name space to global one to prevent certain IPython bug.
    3. while doing so optionally overwrite names in the global namespace
    """

    if not condition:
        return None

    # note some but not all portions of IPython code need the camelcase verions
    assert color_scheme.lower() in ['nocolor', 'neutral', 'linux', 'lightbg']
    C = Container(copy_namespaces=copy_namespaces, overwrite_globals=overwrite_globals, color_scheme=color_scheme )


    if not frame:
        frame = inspect.currentframe().f_back

    # extension of local namespace for IPS-debugging purposes
    if not ns_extension:
        C.ns_extension = {}
    else:
        C.ns_extension = ns_extension

    # let the user know, where this shell is 'waking up'
    if isinstance(print_tb, int) and not isinstance(print_tb, bool):
        assert print_tb < 0, "print_tb:{}".format(print_tb)
        limit_to = print_tb
    else:
        limit_to = 0

    fli = generate_frame_list_info(frame, code_context, add_context_for_latest, limit_to=limit_to, color_scheme=color_scheme)
    custom_header2 = "\n--- Interactive IPython Shell. Type `?`<enter> for help. ----\n"

    C.ns_extension["_ips_fli"] = fli

    if print_tb:
        # noinspection PyUnresolvedReferences
        C.custom_header = "{0}{1}".format(fli.tb_txt, custom_header2)
    else:
        C.custom_header = ""

    # noinspection PyUnresolvedReferences
    frame_list, frame_info_list = fli.frame_list, fli.frame_info_list
    # prevent IPython shell to be launched in IP-Notebook

    test_str = str(frame_info_list[0])
    try:
        test_str += str(frame_info_list[1])
    except IndexError:
        # IPS was called in the top-level frame
        # -> no problem
        pass

    if 'IPython' in test_str and 'zmq' in test_str:
        print("\n- Not entering IPython embedded shell  -\n")
        return

    diff_index = _run_ips(frame_list, C)

    # restore the custom excepthook if possible
    custom_excepthook = getattr(sys, 'custom_excepthook', None)
    if custom_excepthook is not None:
        assert callable(custom_excepthook)
        sys.excepthook = custom_excepthook

    return diff_index


def _run_ips(frame_list, c):
    """
    :param frame_list:  list of frames
    :param c:       Container for arguments
    """

    # copied (and modified) from IPython/terminal/embed.py
    config = load_default_config()
    config.InteractiveShellEmbed = config.TerminalInteractiveShell

    color_scheme = getattr(c, "color_scheme", "neutral")


    config.InteractiveShellEmbed.colors = color_scheme

    # these two lines prevent problems related to the initialization
    # of ultratb.FormattedTB below
    InteractiveShellEmbed.clear_instance()
    InteractiveShellEmbed._instance = None

    shell = InteractiveShellEmbed.instance(config=config)

    # achieve that custom macros are loaded in interactive shell
    shell.magic('load_ext storemagic')
    if config.StoreMagics.autorestore:
        shell.magic('store -r')
        ar_keys = [k.split("/")[-1] for k in shell.db.keys() if k.startswith("autorestore/")]
    else:
        ar_keys = []

    # adapt the namespaces to prevent missing names inside the shell
    # see: https://github.com/ipython/ipython/issues/62
    # https://github.com/ipython/ipython/issues/10695
    if c.copy_namespaces and len(frame_list) >= 1:
        # callers_frame to IPS()
        # note that frame_list and frame_info_list were reversed above
        f1 = frame_list[-1]
        lns = f1.f_locals
        gns = f1.f_globals

        # insert some IPS-debugging variables
        lns.update(c.ns_extension)

        l_keys = set(lns)
        g_keys = set(gns)
        u_keys = shell.user_ns.keys()

        # those keys which are in local ns but not in global
        safe_keys = l_keys - g_keys
        unsafe_keys = l_keys.intersection(g_keys)

        assert safe_keys.union(unsafe_keys) == l_keys

        gns.update({k: lns[k] for k in safe_keys})

        if unsafe_keys and not c.overwrite_globals:
            c.custom_header += "following local keys have " \
                             "not been copied:\n{}\n".format(unsafe_keys)

        if unsafe_keys and c.overwrite_globals:
            gns.update({k: lns[k] for k in unsafe_keys})
            c.custom_header += "following global keys have " \
                             "been overwritten:\n{}\n".format(unsafe_keys)

        # now update the gns with stuff from the user_ns (if it will not overwrite anything)
        # this could be implemented cleaner
        for k in ar_keys:
            if k not in gns:
                gns[k] = shell.user_ns[k]
            else:
                print("omitting key from user_namespace:", k)

        dummy_module = DummyMod()
        dummy_module.__dict__ = gns

    else:
        # unexpected few frames or no copying desired:
        lns = {}
        dummy_module = None

    # now execute the shell
    shell(header=c.custom_header, stack_depth=2, local_ns=lns, module=dummy_module)

    # if `diff_index` is not None it will be interpreted as index increment for the frame_list in the except hook
    # "__mu" means "move up"
    diff_index = lns.get("__mu")
    if not isinstance(diff_index, int):
        diff_index = None

    return diff_index


# noinspection PyPep8Naming
def ips_excepthook(excType, excValue, traceback, frame_upcount=0):
    """
    This function is launched after an exception. It launches IPS in suitable frame.
    Also note that if `__mu` is an integer in the local_ns of the closed IPS-Session then another Session
    is launched in the corresponding frame: "__mu" means = "move up" and referes to frame levels.

    :param excType:     Exception type
    :param excValue:    Exception value
    :param traceback:   Traceback
    :param frame_upcount:   int; initial value for diff index; useful if this hook is called from outside
    :return:
    """

    assert isinstance(frame_upcount, int)

    # first: print the traceback:
    tb_printer = TBPrinter(excType, excValue, traceback)

    # go down the stack
    tb = traceback
    tb_frame_list = []
    while tb.tb_next is not None:
        tb_frame_list.append(tb.tb_frame)
        tb = tb.tb_next

    critical_frame = tb.tb_frame
    tb_frame_list.append(critical_frame)

    tb_frame_list.reverse()
    # now the first frame in the list is the critical frame where the exception occured
    index = 0
    diff_index = frame_upcount

    # this allows to repeat the traceback inside the interactive function

    def __ips_print_tb(**kwargs):
        return tb_printer.printout(end_offset=index, **kwargs)

    while diff_index is not None:
        index += diff_index
        tb_printer.printout(end_offset=index)
        print("\n")
        current_frame = tb_frame_list[index]
        diff_index = IPS(frame=current_frame, ns_extension={"__ips_print_tb": __ips_print_tb}, print_tb=False, color_scheme=module_config.COLOR_SCHEME)


def generate_frame_list_info(frame, code_context, add_context_for_latest=0, limit_to=0, color_scheme=module_config.COLOR_SCHEME):
    res = Container()
    TB = ultratb.FormattedTB(mode="Context", color_scheme=color_scheme, call_pdb=False)
    res.frame_list, res.frame_info_list = get_frame_list(frame, code_context, add_context_for_latest)

    # old Signature: TB.format_record(frame, file, lnum, func, lines, index)

    # formated_records = [TB.format_record(frame, *fi) for fi in res.frame_info_list]
    formated_records = []

    style = get_style_by_name("default")
    # style = stack_data.style_with_executing_node(style, "bg:ansiyellow")
    formatter = Terminal256Formatter(style=style)

    options = stack_data.Options(
            before=code_context - (code_context // 2),
            after=code_context // 2 ,
            pygments_formatter=formatter,
        )


    fil = list(stack_data.FrameInfo.stack_data(frame, options=options))
    for fic in fil:


        # `fi` is a Traceback-Object which has no .frame attribute. That must be added
        #fic = Container(code_context=fi.code_context, count=fi.count, filename=fi.filename, function=fi.function, index=fi.index, lineno=fi.lineno, frame=frame)
        # fic = list(stack_data.FrameInfo.stack_data(frame, options=options))[-1]
        formated_records.append(TB.format_record(fic))

    assert isinstance(limit_to, int) and limit_to <= 0
    res.tb_txt = "\n".join(formated_records[limit_to:])
    return res


def calling_stack_info(print_res=True, code_context=1, **kwargs):
    """
    Debugging helper function. Can be called anywhere and returns (and optionally prints) a stacktrace
    :param print_res:
    :return:
    """

    start_frame = inspect.currentframe().f_back

    fil = generate_frame_list_info(start_frame, code_context=code_context, **kwargs)

    if print_res:
        # noinspection PyUnresolvedReferences
        print(fil.tb_txt)
    return fil



class TBPrinter(object):

    def __init__(self, excType, excValue, traceback):
        self.excType = excType
        self.excValue = excValue
        self.traceback = traceback

        self.TB = ultratb.FormattedTB(mode="Context", color_scheme=module_config.COLOR_SCHEME, call_pdb=False)

    def printout(self, *args, **kwargs):
            debug = kwargs.get("debug", False)
            res = self.get_tb_txt(*args, **kwargs)
            if debug:
                return res
            else:
                print(res)

    def get_tb_txt(self, end_offset=0, prefix="\n", debug=False, cut_logging=True):
        """

        :param prefix:      string which is printed befor the actual TB (default: "\n")
        :param end_offset:  0 means print all, 1 means print parts[:-1] etc
        :param debug:       debug flag (return debug_container)
        :param cut_logging: flag (cut off logging information e.g. injected by nosetests)
        :return:
        """
        # note that the kwarg `tb_offset` of the FormattedTB constructor is refers to the start of the list
        tb_parts = self.TB.structured_traceback(self.excType, self.excValue, self.traceback)
        line_list = [prefix] + tb_parts[:len(tb_parts)-1-end_offset] + [tb_parts[-1]]

        if cut_logging:
            start_idcs = []
            end_idcs = []
            removed_lines = []
            for i, line in enumerate(line_list):
                if ">> begin captured logging <<" in line:
                    start_idcs.append(i)
                if ">> end captured logging <<" in line:
                    end_idcs.append(i)

            if len(start_idcs) == len(end_idcs) == 1:
                for i in range(start_idcs[0], end_idcs[0] + 1):
                    removed_lines.append(line_list.pop(i))

                msg = "Note: {} lines ({} chars) of logging information have beed removed for better overview."
                n_chars = len("\n".join(removed_lines))
                msg = msg.format(len(removed_lines), n_chars)
                line_list.insert(start_idcs[0], msg)

                # the first removed line might contain useful information

                fl = removed_lines[0]
                idx = fl.index(">> begin captured logging <<")

                # find the last line break before the unwanted logging info
                br_idx = fl.rfind("\n", 0, idx) + 1

                line_list.insert(start_idcs[0], fl[:br_idx])

        text = "\n".join(line_list)

        if debug:
            return Container(fetch_locals=True)

        return text


def activate_ips_on_exception(color_scheme=module_config.COLOR_SCHEME):

    module_config.COLOR_SCHEME = color_scheme

    if os.environ.get("NO_IPS_EXCEPTHOOK"):
        # this is useful in the context of calling python programs from other processes
        # e.g. via subprocess.run(...). Then this flag allows to prevent dropping
        # into an IP-Shell after an exception
        return

    
    # set the hook
    sys.excepthook = ips_excepthook

    # save the hook (because it might be overridden from extern)
    sys.custom_excepthook = ips_excepthook


def color_excepthook(pdb=0, mode=2, force=True):
    """
    Make tracebacks after exceptions colored, verbose, and/or call pdb
    (python cmd line debugger) at the place where the exception occurs
    """

    modus = ['Plain', 'Context', 'Verbose'][mode] # select the mode

    if force or not sys.excepthook == sys_orig_excepthook:
        sys.excepthook = ultratb.FormattedTB(mode=modus,
                                             color_scheme=module_config.COLOR_SCHEME, call_pdb=pdb)


# for backward compatibiliy
ip_syshook = color_excepthook

# now, we immediately  apply this new excepthook.
# consequence: when this module is imported the tracebacks automatically are colored (easier to read)
color_excepthook(force=True)


def ip_extra_syshook(fnc, pdb=0, filename=None):
    """
    Extended system hook for exceptions.

    supports logging of tracebacks to a file

    lets fnc() be executed imediately before the IPython
    Verbose Traceback is started

    this can be used to pop up a QTMessageBox: "An exception occured"
    """

    assert isinstance(fnc, collections.Callable)
    from IPython.core import ultratb
    import time

    if not filename == None:
        assert isinstance(filename, str)
        pdb = 0

    ip_excepthook = ultratb.FormattedTB(mode='Verbose',
                                    color_scheme=module_config.COLOR_SCHEME, call_pdb=pdb)

    fileTraceback = ultratb.FormattedTB(mode='Verbose',
                                    color_scheme='NoColor', call_pdb=0)

    # define the new excepthook
    def theexecpthook (type, value, traceback):
        fnc()
        ip_excepthook(type, value, traceback)
        # write this to a File without Colors
        if not filename == None:
            outFile = open(filename, "a")
            outFile.write("--" + time.ctime()+" --\n")
            outFile.write(fileTraceback.text(type, value, traceback))
            outFile.write("\n-- --\n")
            outFile.close()

    # assign it
    sys.excepthook = theexecpthook



# noinspection PyPep8Naming
def TracerFactory(color_scheme=module_config.COLOR_SCHEME):
    """
    Returns a callable `set_trace`-object.
    When this object is called it starts the ipython commandline debugger
    in that place.

    :param color_scheme:    (optional) one of ['Linux', 'NoColor', 'LightBG', 'Neutral']
    """

    Pdb_instance = Pdb()

    # Note: colors can be adapted at runtime from the calling script via
    # Pdb_instance.set_colors("Neutral") # default
    # Pdb_instance.set_colors("NoColor")

    Pdb_instance.set_colors(color_scheme) # default
    set_trace = Pdb_instance.set_trace

    return set_trace



set_trace = TracerFactory()



# this has legacy reasons:
# noinspection PyPep8Naming
def ST():
    a = " "*3
    print("\n"*5, a, "ST is dreprecated due to namespace problems.")
    print(a, "use: from ipydex import set_trace")
    print(a, "\n"*2)
    print(a , "<ENTER>")
    print(a, "\n"*5)
    # noinspection PyBroadException
    try:
        input()
    except:
        pass

#################################
# Code below is jupyter notebook specific


def get_notebook_name():
    """
    Return the full path of the jupyter notebook.
    """
    # taken from https://github.com/jupyter/notebook/issues/1000#issuecomment-359875246

    try:
        import requests
        from requests.compat import urljoin
    except ImportError:
        msg = "This functions depends on the module requests."
        # it is not an official dependency because this is not a core functionality
        raise ImportError(msg)

    import ipykernel
    import json
    import re
    from notebook.notebookapp import list_running_servers

    kernel_id = re.search('kernel-(.*).json',
                          ipykernel.connect.get_connection_file()).group(1)
    servers = list_running_servers()
    for ss in servers:
        response = requests.get(urljoin(ss['url'], 'api/sessions'),
                                params={'token': ss.get('token', '')})
        for nn in json.loads(response.text):
            if nn['kernel']['id'] == kernel_id:
                relative_path = nn['notebook']['path']
                return os.path.join(ss['notebook_dir'], relative_path)


def in_ipynb(debug=False):
    """
    Test whether this functions is called from within an ipython notebook on jupyter
    """

    frame_info_list = get_frame_list()[1]
    filenames = [fi.filename for fi in frame_info_list]

    test_str = "\n".join(filenames)
    # this should be made more reliable
    if "ipykernel_launcher" in test_str and \
       "ipykernel/kernelapp.py" in test_str and \
       "zmqshell" in test_str:
        res = True
    else:
        res = False

    if debug:
        dbgc = Container(fetch_locals=True)
        return dbgc
    else:
        return res


def save_current_nb_as_html(info=None, return_res=False):
    """
    Save the current notebook as html file in the same directory
    """
    assert in_ipynb()

    full_path = get_notebook_name()
    path, filename = os.path.split(full_path)

    wd_save = os.getcwd()
    os.chdir(path)
    cmd_list = ["jupyter", "nbconvert", filename, "--to", "html", "--template", "classic"]

    res = subprocess.run(cmd_list, capture_output=True)
    res.exited = res.returncode
    res.stdout = res.stdout.decode("utf8")
    res.stderr = res.stderr.decode("utf8")

    os.chdir(wd_save)

    if info == True:
        print("target dir: ", path)
        print("cmd: ", cmd)
        print("working dir: ", wd_save)
    elif info is None:
        print("`{}`".format(filename), "written.")

    if return_res:
        return res

#################################

# The function below is just for convenience part of this module
# formally it would belong to an own module

###############################


def dump_to_tmpfile(obj):
    """
    Write str(obj) to temporary file and return the path. Useful to open that file in a text editor for advanced
    examination of its content (for debugging).

    :param obj:
    :return:
    """

    import tempfile

    fname = tempfile.mktemp()
    with open(fname, "w") as txtfile:
        txtfile.write(str(obj))

    print("str(obj) was written to {}".format(fname))

    return fname


def dirsearch(s, obj, only_keys=True, deep=0, maxlength=20):
    """
    Search a string `s` (case-insensitive) in `dir(obj)`. If `obj` is a dict, then search in its keys.

    :param s:           str. The string to search for.
    :param obj:         The object or dict to search in.
    :param only_keys:   default: True. If False, return also a str-version of attributes or dict-values (not only the
                        keys). Note, this implies that matches are also found in attributes/dict-values if they fulfill
                        isinstance(value, str).

    :param maxlength:   int. default=20; maximum displayed lenghth of the above str.-version
    :param deep:        recursion level

    """
    s = s.lower()

    if isinstance(obj, dict):
        # only consider keys which are basestrings
        items = [(key, val) for key, val in list(obj.items()) if isinstance(key, str)]
    else:

        items = []
        for key in dir(obj):
            try:
                items.append( (key, getattr(obj, key)) )
            except AttributeError:
                continue
            except NotImplementedError:
                continue

    def maxlen(s, n):
        s = s.replace("\n", " ")
        if len(s) > n:
            s = s[:n-2]+'..'
        return s

    def match(word, key, value):
        if only_keys:
            return word in key.lower()
        else:
            # search also in value (if it is of type basestring)
            if not isinstance(value, str):
                value = ""  # only local change

            return (word in key.lower()) or (word in value.lower())

    res = [(k, maxlen(str(v), maxlength)) for k, v in items if match(s, k, v)]

    # res is a list like [(key1, value1), (key2, value2), ...]

    if deep > 0:
        # recursively search in the attributes/values

        def interesting(obj):
            module = type(sys)
            deep_types = (module, type, dict)
            # noinspection PyShadowingNames
            res = isinstance(type(obj), deep_types)
            return res

        deeper_items = [(name, obj) for name, obj in items if interesting(obj)]

        for name, obj in deeper_items:
            deep_res = dirsearch(s, obj, only_keys=False, deep=deep - 1, maxlength=maxlength)
            deep_res = [("%s.%s" %(name, d_name), d_obj) for d_name, d_obj in deep_res]
            res.extend(deep_res)

    if only_keys and len(res) >0:
        res = list(zip(*res))[0]
        # now res only contains the keys
    return res


class Container(object):
    """General purpose container class to conveniently store data attributes

    There are three main usecases for this container data type (see below) which are triggered by args and keyword args:

    (1) Store some data:

        C = Container()
        C.x = x
        C.y = y

    (2) Collect provided variables:

        x = 7
        y = 8
        C = Container(cargs=(x, y))

        # now by some `inspect`-magic x and y are available as attributes
        assert C.x == x
        assert C.y == y


    (3) Collect all variables from local namespace and (by some `inspect`-magic) make them available as
        attributes (usefull for debugging).

        def func1(x, debug=False):
            y = complicated_func1(x)
            res = complicated_func2(x, y)

            C = Container(fetch_locals=True)

            if debug:
                return C
            else:
                return res

        C = func1(100, debug=True)

        # investigate internal behavior
        print(C.x)
        print(C.y)
        print(C.res)
    """

    def __init__(self, cargs=None, **kwargs):

        fetch_locals = kwargs.pop("fetch_locals", False)
        allow_overwrite = kwargs.pop("_allow_overwrite", False)

        # this might later hold the variable names passed to cargs (used for sorting)
        self.__carg_varnames = []

        if cargs is not None:
            assert not fetch_locals
            # we were called with something like: c = Container(cargs=(x, y, z))

            caller_frame = inspect.currentframe().f_back

            tmp_dict, self.__carg_varnames = get_carg_vars_from_frame(caller_frame, type(cargs), return_varnames=True)

            for k in tmp_dict.keys():
                if k in kwargs:
                    msg = "Name conflict between cargs and kwargs w.r.t. name: '{}'".format(k)
                    raise NameError(msg)
            kwargs.update(tmp_dict)

        if fetch_locals:
            self.fetch_locals(upcount=2)

        isec = set(dir(self)).intersection(list(kwargs.keys()))
        if len(isec) > 0 and not allow_overwrite:
            msg = "Name conflict with the following names: {}".format(isec)
            raise NameError(msg)
        self.__dict__.update(kwargs)

    def _get_attrs(self, names):
        """
        Convenience function to extract multiple attributes at once

        :param names:   string of names separated by comma or space
        :return:
        """
        assert isinstance(names, str)
        names = names.replace(",", " ").split(" ")
        res = []
        for n in names:
            if n == "":
                continue
            if n not in self.__dict__:
                raise KeyError("Unknown name for Container attribute: '{}'".format(n))
            res.append(getattr(self, n))
        return res

    def fetch_locals(self, upcount=1):
        """
        Magic function which fetches all variables from the callers namespace
        :param upcount     int, how many stack levels we go up
        :return:
        """

        frame = inspect.currentframe()
        i = upcount
        while True:
            if frame.f_back is None:
                break
            frame = frame.f_back
            i -= 1
            if i == 0:
                break

        for k, v in frame.f_locals.items():
            self.__dict__[k] = v

    def publish_attrs(self, upcount=1):
        """
        Magic function which inject all attrs into the callers namespace
        :param upcount     int, how many stack levels we go up
        :return:
        """

        frame = inspect.currentframe()
        i = upcount
        while True:
            if frame.f_back is None:
                break
            frame = frame.f_back
            i -= 1
            if i == 0:
                break

        for k, v in self.__dict__.items():
            frame.f_globals[k] = v

    def value_list(self):
        ilist = self.item_list()

        return list(zip(*ilist))[1]

    def item_list(self):

        tmp_dict = dict(self.__dict__)
        tmp_dict.pop("_Container__carg_varnames")

        ilist = list(tmp_dict.items())

        def keyfnc(tup):
            try:
                idx = self.__carg_varnames.index(tup[0])
            except ValueError:
                idx = float("inf")

            return idx

        ilist.sort(key=keyfnc)
        return ilist

    def save_with_pickle(self, fname):

        attribute_dict = dict(self.item_list())

        with open(fname, "wb") as pfile:
            pickle.dump(attribute_dict, pfile)

    @staticmethod
    def load_with_pickle(fname):
        with open(fname, "rb") as pfile:
            attribute_dict = pickle.load(pfile)
        C = Container(**attribute_dict)
        return C

    def __repr__(self):
        # basically return the representation of the dict
        return "<Container: {}>".format(self.__dict__)

    def __eq__(self, other):
        if not isinstance(other, Container):
            return False
        
        return self.__dict__ == other.__dict__


# End of class Container


def get_whole_assignment_expression(line, varname, seq_type):
    """
    Example:

    line = "x = Container(cargs=(a, b, c))"
    varname = cargs
    delimiter pair = "()"

    return "a, b, c"

    :return:
    """

    tokens = str_to_token_list(line)

    if issubclass(seq_type, tuple):
        L, R = "()"
    elif issubclass(seq_type, list):
        L, R = "[]"
    else:
        raise TypeError("Invalid sequence type given: {}".format(seq_type))

    errmsg = "Unexpected format to process assignment `{}=...` in line '{}'".format(varname, line)

    # Delimiter_open_level
    DOL = 0

    # 0 -> not searching, 1 -> searching for first occurence of `L`, 2 -> searching for last occurence of `R`
    search_mode = 0

    i_start, i_end = None, None

    for i, t in enumerate(tokens):
        if t.type == tk.NAME and t.string == varname:
            search_mode = 1
            i_start = i
            assert tokens[i + 1].string == "="
            assert tokens[i + 2].string == L
            continue

        if search_mode < 1 or not t.type == tk.OP:
            continue

        if t.string == L:
            DOL += 1
            search_mode = 2

        if t.string == R:
            DOL -= 1

        if search_mode == 2 and DOL == 0:
            i_end = i
            break
    else:  # no break
        raise ValueError(errmsg)

    substr = line[tokens[i_start].start[1]: tokens[i_end].end[1]]

    try:
        assert substr.count(L) == 1
        assert substr.count(R) == 1
        assert substr.count('"') == 0
        assert substr.count("'") == 0
    except AssertionError:
        raise ValueError(errmsg)

    return substr


def get_carg_vars(expr):
    expr = expr.replace(" ", "")
    assert expr.startswith("cargs=(") or expr.startswith("cargs=[")

    vars = expr[7:-1].split(",")

    return vars


def get_carg_vars_from_frame(frame, seq_type, return_varnames=False):

    info = inspect.getframeinfo(frame)
    context = info.code_context

    code_line = " ".join(context)

    expr = get_whole_assignment_expression(code_line, "cargs", seq_type)
    varnames = get_carg_vars(expr)

    not_found_list = []
    results = {}
    for vn in varnames:
        if vn in frame.f_locals:
            results[vn] = frame.f_locals[vn]
        elif vn in frame.f_globals:
            results[vn] = frame.f_globals[vn]
        else:
            not_found_list.append(vn)

    if len(not_found_list) > 0:

        msg = "The following variables could not be found in local or global namespace: {}".format(not_found_list)
        raise NameError(msg)

    if return_varnames:
        return results, varnames
    else:
        return results


def _tokenize(ustr1):
    """
    More convenient interface to tokenize.generate_tokens

    :param ustr1:   unicode-str to be tokenized
    :return: List of tokens
    """

    return list(tk.generate_tokens(io.StringIO(ustr1).readline))


def str_to_token_list(line, raise_TE=False):

    if sys.version_info[0] >= 3:
        # in python3 line is already unicode
        uline = line
    else:
        # uses sys.getdefaultencoding()
        uline = line.decode()

    try:
        tokens = _tokenize(line)
    except tk.TokenError as err:
        # this happens e.g. for a multi-line-string
        # ignore this line
        if raise_TE:
            raise err
        else:
            tokens = _tokenize(u"")

    def unpac_token_info(ti):
        ti_dict = dict(zip(["type", "string", "start", "end", "line"], ti))
        ti_dict["type_name"] = tk.tok_name[ti.type]
        return ti_dict

    tokens = [Container(**unpac_token_info(t)) for t in tokens]

    return tokens


# trivial helper function
# copied from https://github.com/pdbpp/pdbpp/
def always(*args, **kwargs):
    return True

# two class decorators which trigger IPS() if an attribute or an internal storrage changes


# copied from https://github.com/pdbpp/pdbpp/
def break_on_setattr(attrname, condition=always):
    def decorator(cls):
        old___setattr__ = cls.__setattr__

        def __setattr__(self, attr, value):
            if attr == attrname and condition(self, value):
                IPS()
            old___setattr__(self, attr, value)
        cls.__setattr__ = __setattr__
        return cls
    return decorator


class SurveiledDict(dict):
    """
    Dictionary which triggeres IPS if a value is set (and an optional condition is met)
    """

    def __init__(self, *args, **kwargs):
        self._set_condition(always)
        super().__init__(*args, **kwargs)

    def _set_condition(self, condition):
        self._condition_func = condition

    def __setitem__(self, key, value):
        if self._condition_func(self, key, value):
            IPS()
        super().__setitem__(key, value)

    def update(self, *args, **kwargs):
        if self._condition_func(self, *args, **kwargs):
            IPS()
        super().update(*args, **kwargs)

