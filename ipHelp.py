# -*- coding: utf-8 -*-


import sys
import new

import inspect

__version__ = "0.4.1"



# Licence: GPLv3
#  (full text: http://www.gnu.org/licenses/gpl-3.0-standalone.html)
# Origin: a coobook example extended by Carsten Knoll for personal needs
# Please send bug reports via Email
# "Carsten.+".replace('+', 'Knoll@') + "tu-dresden.de"


"""
Module which quickly offers IPythons embedding functions.

In principle this module could be reduced to

from IPython import embed as IPS

but there are some additional features in this module


typical usage:

from ipHelp import ip_syshook, IPS, TracerFactory, dirsearch



IPS() # starts the ipython embedded shell
(with the ability to prevent further invocations with `_ips_exit = True`)

ST = TracerFactory()
...
ST() # starts the debugger prompt ("Start Trace"); type 'help' to get started
in contrast to the IPython Shell the debugger allows to go stepwise through
the following code.


ip_syshook(1) # starts debugger on exceptions and adds some infos
to tracebacks (like the values of calling args)

dirsearch # has nothing to do with ipython but may help to explore
the namespace. Example: import os; dirsearch('path', os)


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


def format_frameinfo(fi):
    """
    Takes a frameinfo object (from the inspect module)
    
    returns a properly formated string
    """
    s1 = "{0}:{1}".format(fi.filename, fi.lineno)
    s2 = "function:{0},    code_context:".format(fi.function)
    s3 = fi.code_context[0]
    
    return "\n".join([s1, s2, s3])
    

try:

    from IPython import embed
    from IPython.terminal.ipapp import load_default_config
    from IPython.terminal.embed import InteractiveShellEmbed    
    from IPython.core import ultratb
    
    def IPS():
        
        # let the user know, where this shell is 'waking up'
        # construct frame list
        # this will be printed in the header
        frame_info_list = []
        frame_list = []
        frame = inspect.currentframe()
        while not frame == None:
            frame_list.append(frame)
            info = inspect.getframeinfo(frame)
            frame_info_list.append(info)
            frame = frame.f_back

        frame_info_list.reverse()
        frame_list.reverse()
        frame_info_str_list = [format_frameinfo(fi) for fi in frame_info_list]
        
        custom_header1 = "----- frame list -----\n\n"
        frame_info_str = "\n--\n".join(frame_info_str_list[:-1])
        custom_header2 = "\n----- end of frame list -----\n"
        
        custom_header = "{0}{1}{2}".format(custom_header1, frame_info_str, custom_header2)
        
        
        # prevent IPython shell to be launched in IP-Notebook
        test_str = str(frame_info_list[0]) + str(frame_info_list[1])
        #print test_str
        if 'IPython' in test_str and 'zmq' in test_str:
            print "\n- Not entering IPython embedded shell  -\n"
            return
            
        # prevent IPython shell to be launched if the apropriate flag is set
        # (by the user during the last call)
        # This is usefull if the IPS()-call is placed within a loop
        if frame_list[0].f_locals.get('_ips_exit', False):
            print "\n- Not entering IPython embedded shell  -\n"
            return

        # copied (and modified) from IPython/terminal/embed.py
        config = load_default_config()
        config.InteractiveShellEmbed = config.TerminalInteractiveShell
        
        custom_ns = {'_ips_exit':False}
        shell = InteractiveShellEmbed.instance(user_ns=custom_ns)
        #shell(header=header, stack_depth=2, compile_flags=compile_flags)
        
        # finally call the shell
        shell(header=custom_header, stack_depth=2)
        
        ips_exit_flag = shell.user_ns.get('_ips_exit', False)
        
        # insert this flag to the actual namespace in the caller-scope 
        frame_list[0].f_locals['_ips_exit'] = ips_exit_flag

    def color_exepthook(pdb=0, mode=2):
        """
        Make tracebacks after exceptions colored, verbose, and/or call pdb
        (python cmd line debugger) at the place where the exception occurs
        """

        modus = ['Plain', 'Context', 'Verbose'][mode] # select the mode

        sys.excepthook = ultratb.FormattedTB(mode=modus,
                                        color_scheme='Linux', call_pdb=pdb)

    # for backward compatibiliy                                                    
    ip_syshook = color_exepthook
    
    # now, we immediately  apply this new excepthook.
    # consequence: often its sufficient jsut to import this module
    color_exepthook()
    

    def ip_extra_syshook(fnc, pdb=0, filename=None):
        """
	Extended system hook for exceptions.

	supports logging of tracebacks to a file

        lets fnc() be executed imediately before the IPython
        Verbose Traceback is started

        this can be used to pop up a QTMessageBox: "An exception occured"
        """

        assert callable(fnc)
        from IPython.core import ultratb
        import time

        if not filename == None:
            assert isinstance(filename, str)
            pdb = 0

        ip_excepthook = ultratb.FormattedTB(mode='Verbose',
                                        color_scheme='Linux', call_pdb=pdb)

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


#    from IPython.Debugger import Tracer
#    ST=Tracer() # "ST" = "start trace"

    from IPython.core.debugger import Tracer

    def TracerFactory():
    """
    Returns a callable `Tracer` object.
    When this object is called it starts the ipython commandline debugger
    in that place.
    """
        return Tracer(colors='Linux')

    # this has legacy reasons:
    def ST():
        a = " "*3
        print "\n"*5, a, "ST is dreprecated due to namespace problems."
        print a, "use: ST = TracerFactory() or"
        print a, "from IPython.core.debugger import Tracer"
        print a, "ST=Tracer(colors='Linux')"
        print a, "\n"*2
        print a , "<ENTER>"
        print a, "\n"*5
        try:
            raw_input()
        except:
            pass


except ImportError, E:
    # IPython seems not to be installed
    # create dummy functions

    print "ipython Import Error: ", E

    def IPS():
        print "(EE): IPython is not available"
        pass
    def ip_syshook(*args, **kwargs):
        pass

    def ip_extra_syshook(*args, **kwargs):
        pass

    def ST():
        pass


#################################

# The function below is just for convenience part of this module
# formally it would belong to its own module

###############################

def dirsearch(word, obj, only_keys = True, deep = 0):
    """
        search a string in dir(<some object>)
        if object is a dict, then search in keys

        optional arg only_keys: if False, returns also a str-version of
        the attribute (or dict-value) instead only the key

        this function is not case sensitive
    """
    word = word.lower()

    if isinstance(obj, dict):
        # only consider keys which are strings
        items = [(key, val) for key, val in obj.items() \
                                                if isinstance(key, str)]
    else:
        #d = dir(obj)

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
            if not isinstance(value, basestring):
                value = "" # only local change

            return (word in key.lower()) or (word in value.lower())

    res = [(k, maxlen(str(v), 20)) for k,v in items if match(word, k, v)]
    # res is a list of (key,value)-pairs

    if deep >0:

        def interesting(obj):
            module = type(sys)
            deep_types  = (module, type, dict)
            res = isinstance(type(obj), deep_types)
            #res = res and not (obj is type)
            return res

        deeper_items = [(name, obj) for name, obj in items \
                                    if interesting(obj)]

        for name, obj in deeper_items:
            deep_res = dirsearch(word, obj, only_keys=False, deep = deep-1)
            deep_res = [("%s.%s" %(name, d_name), d_obj)
                                        for d_name, d_obj in deep_res]
            res.extend(deep_res)


    if only_keys and len(res) >0:
        res = zip(*res)[0]
        # now res only contains the keys
    return res


