#!/usr/bin/env python
import time
import traceback

from ant.core import driver
from ant.core import node
from ant.core import log

try:
    stick = driver.USB2Driver(None, debug=True, log=log.LogWriter())
    antnode = node.Node(stick)

    antnode.start()
    antnode.stop()

except Exception as e:
    print "Caught exception: " + repr(e)
    traceback.print_exc()

    
