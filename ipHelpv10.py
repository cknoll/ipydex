# -*- coding: utf-8 -*-


# Licence: GPLv3
#  (full text: http://www.gnu.org/licenses/gpl-3.0-standalone.html)

# Origin: a coobook example extended by Carsten Knoll for personal needs


"""
Module which quickly offers IPythons embedding functions.

typical usage:

from ipHelp import ip_syshook, IPS, ST

ip_syshook(1) # starts debugger on exceptions and adds some infos to tracebacks

IPS() # starts the ipython embedded shell

ST() # starts the debugger prompt ("Start Trace"); type 'help' to get started 


known bugs:
- - - - - - 

if used from within a PyQt app: annoying meassages

  "QCoreApplication::exec: The event loop is already running"

solution:
QtCore.pyqtRemoveInputHook() # to be called in __init__ of main-dialog-class


------------

the way colors are represented in a "normal" shell conflicts with embedded
shells in eclipse or spyder; result: ugly control characters

-----------

The embedded IPython-Shell seems to conflict with output suppressing in
py.test. To avoid this disable the output suppressing via:
py.test -s <testfiles>
"""

# if IPython is not installed it is not that bad.
# It is just a usefull tool do interactive debugging.

import sys
import new

__version__ = "0.3"

try:
    from IPython.Shell import IPShellEmbed
    args = ['-pi1','In <\\#>: ','-pi2','   .\\D.: ',
                '-po','Out<\\#>: ','-nosep']
    
    #the_user_ns = {'_exit': False}

    # workarround to the following problem:
    # if one calls IPS() from within a loop
    # it will be started again with every cycle
    # this may be very unwanted

    # the solution is to introtuce a boolean variable
    #  _ips_exit 
    # into the user namespace and after IPS is finished check its value

    # To achive this, the Embedded Shell Object modifies itself during runtime
    
    class AdaptedIPSE(IPShellEmbed):
        def __init__(self, *args, **kwargs):
            
            IPShellEmbed.__init__(self, *args, **kwargs)
            
            # now self.IP exisits

            
            old_interact = self.IP.interact # save the real method
            
            def new_interact(self, *args):
                """ wrapper method which checks the user namespace
                """
                
                self.IP.user_ns.update({'_ips_exit':False})

                old_interact(*args) # call the real interact method
                
                # now look if the user wants to stop
                if self.IP.user_ns['_ips_exit']:
                    def do_nothing(*args, **kwargs):
                        pass
                    
                    # harakiri
                    # the calling method replaces itself with a the dummy
                    self.IP.interact = do_nothing 
                
                
            # replace the original interact method with the wrapper 
            self.IP.interact = new.instancemethod(new_interact, self,
                                                                  type(self))
    
# The old call    
#    IPS= IPShellEmbed(args,
#                           banner = 'Dropping into IPython',
#                           exit_msg = 'Leaving Interpreter, back to program.',
#                           user_ns = the_user_ns)
    
    IPS= AdaptedIPSE(args,
                           banner = 'Dropping into IPython',
                           exit_msg = 'Leaving Interpreter, back to program.')
                           #user_ns = the_user_ns)
    
    def ip_syshook(pdb=0, mode=2):
        """
        Make exceptions verbose, and/or call pdb (python cmd line debugger)
        """
        import IPython.ultraTB

        modus = ['Plain', 'Context', 'Verbose'][mode] # select the mode

        sys.excepthook = IPython.ultraTB.FormattedTB(mode=modus,
                                        color_scheme='Linux', call_pdb=pdb)


    def ip_extra_syshook(fnc, pdb=0, filename=None):
        """
	Extended system hook for exceptions.

	supports logging of tracebacks to a file 

        lets fnc() be executed imediately before the IPython
        Verbose Traceback is started

        this can be used to pop up a QTMessageBox: "An exception occured"
        """

        assert callable(fnc)
        import IPython.ultraTB
        import time

        if not filename == None:
            assert isinstance(filename, str)
            pdb = 0

        ip_excepthook = IPython.ultraTB.FormattedTB(mode='Verbose',
                                        color_scheme='Linux', call_pdb=pdb)

        fileTraceback = IPython.ultraTB.FormattedTB(mode='Verbose',
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

    
    from IPython.Debugger import Tracer
    ST=Tracer() # "ST" = "start trace"

except ImportError:
    # IPython seems not to be installed
    # create dummy functions
    def IPS():
        print "(EE): IPython is not available"
        pass
    def ip_syshook(*args, **kwargs):
        pass

    def ST():
        pass


#################################

# The function below is just for convenience part of this module
# formally it would belong to its own one

###############################

def dirsearch(word, obj, only_keys = True):
    """
        search a string in dir(<some object>)
        if object is a dict, then search in keys

        optional arg only_keys: if False, returns also a str-version of
        the attribute (or dict-value) instead only the key
        
        this function is case insensitive
    """
    word = word.lower()

    if isinstance(obj, dict):
        d = obj
    else:
        #d = dir(obj)
        d = dict([(a, getattr(obj, a)) for a in dir(obj)])

    def maxlen(s, n):
        s = s.replace("\n", " ")
        if len(s) > n:
            s = s[:n-2]+'..'
        return s

    res = [(k, maxlen(str(v), 20)) for k,v in d.items() if word in k.lower()]
    # res is a list of (key,value)-pairs
    
    if only_keys:
        res = zip(*res)[0]
    return res
