#!/usr/bin/env  python3

###############################################################################
##
##  FILE:  	refreshTestServer
##
##  NOTES: 	This script will download the production unloads from the server
##         	given on the command line, run doRestore to load the data, then
##         	configure the database so it's safe for feed testing
##
##  AUTHOR:	Ken Hughes
##
##  Copyright 2020 - Baxter Planning Systems, Inc. All rights reserved
##
###############################################################################

import io
import os
import sys
import logging

self = os.path.basename(__file__)

LOG_FILENAME = open("%s.log" % self, "w")

print (LOG_FILENAME)

LOG_FILENAME.close
