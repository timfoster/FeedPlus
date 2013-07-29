#!/bin/sh

#
# A simple shell wrapper to invoke feedplus with the
# correct environment.
#

export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export LC_CTYPE=en_US.UTF-8
FP_HOME=/home/timf/projects/feedplus
PROJ=$FP_HOME/feedplus.git
PROJ_LIBS=$FP_HOME/libs

# Set this to True if feedplus should update Twitter
WRITE_TO_TWITTER=True

export PYTHONPATH=$PROJ:$PROJ_LIBS/google-api-python-client-1.0:$PROJ_LIBS/python-twitter-1.0:$PROJ_LIBS/python-gflags-2.0:$PROJ_LIBS/oauth2client-1.0:$PROJ_LIBS/httplib2-0.7.6/python2:$PROJ_LIBS/oauth2-1.5.211
$PROJ/feedplus.py 107847990164269071741 $FP_HOME/share $WRITE_TO_TWITTER \
   > $FP_HOME/logs/feedplus_log 2>&1

