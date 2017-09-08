# -*- coding: utf8 -*-


from math import sin, cos


from ipydex import IPS, ip_syshook, ST

"""
This example shows how the tools from module ipydex may be used.
"""


ip_syshook(1) # enable debugger on exception



def func1(q):
    return cos(q) + 5


def func2(q1, q2):
    """
    to demonstrate debugging on exception
    """

    a = q1/q2
    
    if q2 == 5:
        z = 100
        IPS() # start embedded ipython shell in the local scope
        # -> explore global namespace

    
    return a



# ST() # start tracicing start command line debugger here
# presse h <Enter> for help
# n <Enter> to execute next line
# q <Enter> to quit


# create some objects to play around with 
x = [0, 1, 2, 3, 4]

y = sin(3.14)

z = func1(0) - 5

s = "teststring"


b1 = func2(1.0, 2.0) # nothing happens


#b2 = func2(1.0, 0)  # ZeroDivisionError -> start interactive debugger


IPS() # start embedded ipython shell on top level scope
# -> explore global namespace (e.g. type s.<TAB> or s.lower?)


# type CTRL-D to exit


b2 = func2(1.0, 5)  # start IPS inside func2
# not the difference e.g. the local value of z


