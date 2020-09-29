#!/usr/bin/env python

import sys
import threading
import weakref
import atexit
import random
import time
import errno
import os
import subprocess
import socket
import json
import collections

# Known transience sandbox failures!:
# + Main Directory / "port"
# + Main Directory / "caos.syntax"
# But these seem not to cause much problem :>'
# If it does, we can make TransientLC2E take over this like it does the home
# directory ^w^
from transientLC2ESession import TransientLC2ESession
from creaturesFilesystem import CreaturesFilesystem
from utility_functions import getsize, isany

_ourdir = os.path.dirname(os.path.realpath(__file__))

Transient_LC2E_TransientSessions_SuperDirectory = os.path.join(
    _ourdir, "running-transient-sessions")
Transient_LC2E_RWDataInstances_SuperDirectory = os.path.join(
    _ourdir, "rw-instances")
Transient_LC2E_RODataPacks_SuperDirectory = os.path.join(
    _ourdir, "ro-datapacks")
Transient_LC2E_ROEngineTemplateData_Directory = os.path.join(
    _ourdir, "ro-engine")
Transient_LC2E_ErrorReportPackages_Directory = os.path.join(
    _ourdir, "error-reports")


def configureTransientLC2ESessionForStandardDockingStation(sessionObject):
    """Sets Primary/Aux game names, and user configs"""
    # Note: we're horribly game neutral, so this is a separate convenience
    # function, and you has to explicitly call it by default :P
    # unless the skeleton config files are used and include the stuff! :> )
    sessionObject.setPrimaryGameName("Docking Station")
    sessionObject.setAuxiliaryGameName("Creatures 3")
    sessionObject.getUserConfig()["Default Background"] = "ds_splash"
    sessionObject.getUserConfig()["Default Munge"] = "ds_music.mng"







#


# Dynamic CAOS-writing helper functions! :D
def caosEscape(s):
    s = s.replace("\\", "\\\\")
    s = s.replace("\"", "\\\"")
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    s = s.replace("\t", "\\t")
    return s

# Todo: def caosDescape(s)


def toCAOSString(s):
    return "\"" + caosEscape(s) + "\""


def toCAOSByteArray(b):
    # Heavily checked ^^", so you doesn't have to worry about using the wrong type of input and it invisibly breaking somewhere in caos construction! XD''
    if isinstance(b, bytearray):
        return "[" + (" ".join(map(repr, b))) + "]"
    elif isinstance(b, str):
        return "[" + (" ".join(map(lambda c: repr(ord(c)), b))) + "]"
    elif isinstance(b, collections.Iterable):
        if isany(lambda v: v < 0 or v > 255, b): raise Exception(
            "At least one of the bytes was outside the range [0, 255], which is the range an (unsigned) byte can take! D:");
        if isany(lambda v: not (isinstance(v, int), b)): raise TypeError(
            "Argument must be a python bytearray, iterable of *integers*, or str, sorries ;;");
        return "[" + (" ".join(map(repr, b))) + "]"
    else:
        raise TypeError("Argument must be a python bytearray, iterable of integers, or str, sorries ;;")


def transientLC2EDefaultMain(args):
    Default = object()

    if len(args) == 0:
        rwdataInstanceDir = Default
        rodataPackDir = Default
    elif len(args) == 1:
        rwdataInstanceDir = args[0]
        rodataPackDir = None
    elif len(args) == 2:
        rwdataInstanceDir = args[0]
        rodataPackDir = args[1]
    else:
        print("Usage: " + os.path.basename(sys.argv[0]) + " [<rwdata-instance-dir> [<rodata-pack-dir>]]")
        return 1

    if rwdataInstanceDir == Default:
        rwdataInstanceDir = "default"
    if rodataPackDir == Default:
        rodataPackDir = "default"

    rwdataInstanceDir = os.path.join(Transient_LC2E_RWDataInstances_SuperDirectory,
                                     rwdataInstanceDir) if not "/" in rwdataInstanceDir else os.path.abspath(
        rwdataInstanceDir)
    if rodataPackDir != None: rodataPackDir = os.path.join(Transient_LC2E_RODataPacks_SuperDirectory,
                                                           rodataPackDir) if not "/" in rodataPackDir else os.path.abspath(
        rodataPackDir);

    session = TransientLC2ESession()

    # Be very wordy :3
    session.setLogToVerbose()

    session.loadCreaturesFilesystemIntoMachineConfigAsThePrimaryReadwriteFilesystem(
        CreaturesFilesystem(rwdataInstanceDir))
    if rodataPackDir != None: session.loadCreaturesFilesystemIntoMachineConfigAsTheAuxiliaryReadonlyFilesystem(
        CreaturesFilesystem(rodataPackDir));

    configureTransientLC2ESessionForStandardDockingStation(session)

    # Sometimes needed!?
    session.getMachineConfig()["Bootstrap Directory"] = session.getMachineConfig()["Auxiliary 1 Bootstrap Directory"]
    # session.getMachineConfig()["Auxiliary 2 Images Directory"] = session.getMachineConfig()["Auxiliary 1 Images Directory"];

    session.start()

    session.waitForEngineToBecomeCaosable()
    print("CAOS Test! :D     Gnam: " + session.runcaos("outs gnam"))
    print("CAOS Test! :D     Square of 9: " + session.runcaos("setv va00 9  mulv va00 va00  outv va00"))

    session.waitForEngineToTerminate()

    session.cleanUp()

    if session.didEngineCrash():
        print("It crashed! D:!!")
    else:
        print("Iiiit'ssss donnneeeeeeee! :>")


#






#





# Necessary hook-thing in python codes to make it both an importable
# library module, *and* an executable program in its own right! :D
# (like C and Java come with by default :P   which has good things and bad things :> )
if __name__ == "__main__":
    sys.exit(transientLC2EDefaultMain(sys.argv[1:]))
