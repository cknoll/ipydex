# -*- coding: utf-8 -*-


import sys
import new

import inspect 

__version__ = "0.4"


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

from ipHelp import ip_syshook, IPS, ST, dirsearch



IPS() # starts the ipython embedded shell
(with the ability to prevent further invocations with `_ips_exit = True`)

ST() # starts the debugger prompt ("Start Trace"); type 'help' to get started 

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

-----------

The embedded IPython-Shell seems to conflict with output suppressing in
py.test. To avoid this disable the output suppressing via:
py.test -s <testfiles>
"""

# if IPython is not installed it is not that bad.
# It is just a usefull tool do interactive debugging.



# with ipython12 support

try:
    #from IPython.Shell import IPShellEmbed
    from IPython.frontend.terminal.embed import InteractiveShellEmbed
    #args = ['-pi1','In <\\#>: ','-pi2','   .\\D.: ',
                #'-po','Out<\\#>: ','-nosep']
    
    #the_user_ns = {'_exit': False}

    # workarround to the following problem:
    # if one calls IPS() from within a loop
    # it will be started again with every cycle
    # this may be very unwanted

    # the solution is to introtuce a boolean variable
    #  _ips_exit 
    # into the user namespace and after IPS is finished check its value

    # To achive this, the Embedded Shell Object modifies itself during runtime
    
    
    class AdaptedIPSE(InteractiveShellEmbed):
        
        def nest(self, **kwargs):
            """Problem: the normal invocation in inner frames gives no
            access to global namespace
            
            -> workarround:
            
            IPS.nest(glob=globals(), loc = locals())"""
            
            
            
            glob = kwargs.get('glob', {})
            loc = kwargs.get('loc', {})
            
            assert isinstance(glob, dict)
            
            old_interact = self.interact # save the real method
            
            def new_interact(self, *args, **kwargs):
                """ wrapper method which introduces some stuff to the
                user_ns
            
                """
            

                self.user_ns.update(glob)
                self.user_ns.update(loc)
                self.user_ns.update({'_ips_exit':False})

                old_interact(*args, **kwargs) # call the real interact method
                
                # now look if the user wants to stop
                
                if self.user_ns['_ips_exit']:
                    def do_nothing(*args, **kwargs):
                        pass
                    
                    # harakiri
                    # the calling method replaces itself with a the dummy
                    self.interact = do_nothing 
                
                
            # replace the original interact method with the wrapper 
            self.interact = new.instancemethod(new_interact, self,
                                                                  type(self))
    
            
            InteractiveShellEmbed.__call__(self)
            
        
        def __init__(self, *args, **kwargs):
            
            #!! hardcoded colors
            self.colors = 'Linux'
            
            
            InteractiveShellEmbed.__init__(self, *args, **kwargs)
            
            # now self.IP exisits

            
            #dd = dir(self)
            #dd.sort()
            #print dd
            
            
            
            
            old_interact = self.interact # save the real method
            
            
            
            
            def new_interact(self, *args, **kwargs):
                """ wrapper method which checks the user namespace
                """
                
                self.user_ns.update({'_ips_exit':False})

                old_interact(*args, **kwargs) # call the real interact method
                
                # now look if the user wants to stop
                if self.user_ns['_ips_exit']:
                    def do_nothing(*args, **kwargs):
                        pass
                    
                    # harakiri
                    # the calling method replaces itself with a the dummy
                    self.interact = do_nothing 
                
                
            # replace the original interact method with the wrapper 
            self.interact = new.instancemethod(new_interact, self,
                                                                  type(self))
    
# The old call    
#    IPS= IPShellEmbed(args,
#                           banner = 'Dropping into IPython',
#                           exit_msg = 'Leaving Interpreter, back to program.',
#                           user_ns = the_user_ns)
    
    IPS= AdaptedIPSE(banner1 = 'Dropping into IPython',
                     exit_msg = 'Leaving Interpreter, back to program.')
                           #user_ns = the_user_ns)
    
    def ip_syshook(pdb=0, mode=2):
        """
        Make exceptions verbose, and/or call pdb (python cmd line debugger)
        """
        
        
        from IPython.core import ultratb

        modus = ['Plain', 'Context', 'Verbose'][mode] # select the mode

        sys.excepthook = ultratb.FormattedTB(mode=modus,
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
    ST=Tracer(colors='Linux') # "ST" = "start trace"     

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
    
    if only_keys and len(res) >0:
        res = zip(*res)[0]
    return res

    
