import errno
import json
import os
import random
import socket
import subprocess
import sys
import threading
import time

from lc2eSessionCleaner import _lc2eSessionCleaner
from utility_functions import readallText, getUnusedFileSimilarlyNamedTo, \
    writeallText
from CreaturesConfig import parseCreaturesConfig, serializeCreaturesConfig

class TransientLC2ESessionStateException(Exception):
    pass;


class TransientLC2ESessionCAOSConnectionRefused(Exception):
    pass;

class TransientLC2ESession(object):
    """Represents a Session of TransientLC2E"""
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

    # Intended-to-be class constants :>
    State_Unstarted = 0
    State_Running = 1
    State_Terminated = 2
    State_CleanedUp = 3
    State_CleanedUpNeverProperlyStarted = 4

    @classmethod
    def fmtstate(theClass, state):
        return ["unstarted", "running", "terminated", "cleaned-up", "cleaned-up-failed"][state]

    # Intended-to-be instance vars :>   (all the same in python XD')
    state = State_Unstarted
    capturedLog = ""

    "session.log: Set here and always used so you can make it whatever"
    "you want ^w^  (eg, replace the function with something that captures"
    "all the logging messages and stores them in memory!, writes to a file!"
    ", displays in a gui!, etc.c.c.c. :D     "
    "(this applies to all console/loggings things do ;D )"

    log = None
    # {Set beforehand
    # Config needed before starting! :D
    # note: don't set these after it's started / in State_Running; they won't have an effect x>'

    roEngineTemplateDir = None
    # The readonly directory holding the engine stuff for us to
    # link to!  (Type: string that is a pathname ^_^)

    rwActiveSessionEngineDir = None
    # The writeable directory for us to link the engine stuff
    # *into*!  (autonamed and autocreated if None ^w^ )
    # (Type: string that is a pathname ^_^)

    rwActiveSessionHomeDir = None
    # The writeable directory the engine does things in thinking
    # it's our home dir (aka "~")   ..it doesn't have to be our actual
    # home dir ;33   (esp. important if you want to, you know, run more
    # than a single individual instance of the engine throughout the ENTIRE
    # COMPUTER SYSTEM (for that user) at a time! XD''' )

    machineConfig = None  # a dict representing contents of maching.cfg  ^_^
    userConfig = None  # a dict representing contents of user.cfg  ^_^
    serverConfig = None  # a dict representing contents of server.cfg  ^_^
    passwordConfig = None  # a dict representing contents of password.cfg  ^_^
    languageConfig = None  # a dict representing contents of language.cfg  ^_^
    # Note: if a config dict is None, then that file just won't be generated :>
    # (eg, for optional ones like language.cfg or password.cfg ^_^ )

    libfilebasenamesInSameDirAsEngine = None
    # Note that mutable objects as variable-defaults in python class files are shared
    # amongst ALL INSTANCES FOR ALL OF TIME 0_0   (but we can set them in __init__
    # because literals are copied!  ^^'' )

    dataToFeedToStdin = None
    captureStdout = False
    captureStderr = False

    errorReportPackagesDirectory = Transient_LC2E_ErrorReportPackages_Directory
    # Set beforehand}

    # Valid only while in running state! :>
    process = None  # the python "subprocess" module's process object of the engine! :D

    # Valid only while in >= Terminated state!
    # The postXyzConfig's are parsed dicts, the postXyzConfigRaw's are the serialized raw form (str's!)  :>!
    postMachineConfig = None
    postMachineConfigRaw = None  # postXyzConfig's are re-read after the engine terminates! ^w^
    postUserConfig = None
    postUserConfigRaw = None
    postServerConfig = None
    postServerConfigRaw = None
    postPasswordConfig = None
    postPasswordConfigRaw = None
    postLanguageConfig = None
    postLanguageConfigRaw = None

    postLogfile = None
    # unmodified contents of "creatures_engine_logfile.txt" after the engine terminates ^_^
    postUnexpectedFileBasenames = None
    # a python 'set' object of all the files (basenames) which were in the active engine
    # session directory after it terminated, but that we *weren't* expecting to be there!
    # 0_0     (hey, I don't know everything about lc2e!  (#understatement) XD! )
    # The actual files will only still be around while in the Terminated state, until we're
    # cleaned up! (wherein they are deleted! :o ), but their names can still be used of
    # course! ^^

    postAbsentExpectedFileBasenames = None
    # like postUnexpectedFileBasenames but for things which we thought would be there
    # but weren't!  (*cough* don't forget about creatures_engine_logfile.txt *cough*
    # XD   (and optional config files like password.cfg, language.cfg, etc.! )  )

    postStdout = None  # if captureStdout was set to True when the engine started! :D
    postStderr = None  # if captureStderr was set to True when the engine started! :D

    exitStatus = None  # unix exit status of the engine! :D

    def __init__(self, ro_engine_template_dir=Transient_LC2E_ROEngineTemplateData_Directory,
                 rw_active_session_engine_dir=None,
                 rw_active_session_home_dir=None,
                 port=None,
                 read_initial_skeleton_config_file_data_from_engine_template: object = True):
        # {shhh, private things >,>
        self.waitLock = threading.Lock()
        self.cleaner = None
        # }

        self.setLogToNonVerbose()

        self.setState(TransientLC2ESession.State_Unstarted)

        self.libfilebasenamesInSameDirAsEngine = [
            "lc2e-netbabel.so"]
        # this lib has to be in the current dir (or just same dir as the engine?);
        # idk why :p  (but the others seem fine to separate out! so might as well
        # I guess..   *shrugs*  :>  )

        # All of the things has to be absolute pathnames here, since the engine will
        # be starting in the session dir, not wherever we are 'cd'd to!  0,0
        self.roEngineTemplateDir = os.path.abspath(ro_engine_template_dir) \
            if ro_engine_template_dir is not None else None

        if rw_active_session_engine_dir is None:  # ie, default :>
            self.setRWActiveSessionEngineDirToAutonameRightBeforeStart()
        else:
            self.setRWActiveSessionEngineDir(os.path.abspath(rw_active_session_engine_dir))

        if rw_active_session_home_dir is None:  # ie, default :>
            self.setRWActiveSessionHomeDirToAutocreateInsideEngineDirRightBeforeStart()
        else:
            self.setRWActiveSessionHomeDir(os.path.abspath(rw_active_session_home_dir))

        if port is None:  # ie, default :>
            self.setPortToAutofindRightBeforeStart()
        else:
            self.setPort(port)

        if read_initial_skeleton_config_file_data_from_engine_template:
            self.readInitialSkeletonConfigFileDataFromEngineTemplate()

    #

    def setLogToVerbose(self, out=sys.stdout):
        def verboseLog(msg):
            self.defaultLog(msg)
            out.write("TransientLC2E: " + msg + "\n")

        self.log = verboseLog

    def setLogToNonVerbose(self):
        self.log = self.defaultLog

    def defaultLog(self, msg):
        self.capturedLog += msg + "\n\n"

    def setRWActiveSessionEngineDirToAutonameRightBeforeStart(self):
        self.rwActiveSessionEngineDir = None

    def isRWActiveSessionEngineDirSetToAutonameRightBeforeStart(self):
        return self.rwActiveSessionEngineDir == None

    def setRWActiveSessionEngineDir(self, rwActiveSessionEngineDir):
        self.log("Setting rwActiveSessionEngineDir to: " + (
            repr(rwActiveSessionEngineDir) if rwActiveSessionEngineDir != None else "<autocreate>") + "  ^^")
        self.rwActiveSessionEngineDir = rwActiveSessionEngineDir

    def getRWActiveSessionEngineDir(self):
        return self.rwActiveSessionEngineDir

    def setRWActiveSessionHomeDirToAutocreateInsideEngineDirRightBeforeStart(self):
        self.rwActiveSessionHomeDir = None

    def isRWActiveSessionHomeDirSetToAutocreateInsideEngineDirRightBeforeStart(self):
        return self.rwActiveSessionHomeDir == None

    def setRWActiveSessionHomeDir(self, rwActiveSessionHomeDir):
        self.log("Setting rwActiveSessionHomeDir to: " + (
            repr(rwActiveSessionHomeDir) if rwActiveSessionHomeDir != None else "<autocreate>") + "  ^^")
        self.rwActiveSessionHomeDir = rwActiveSessionHomeDir

    def getRWActiveSessionHomeDir(self):
        return self.rwActiveSessionHomeDir

    def getMachineConfig(self):
        if self.machineConfig == None:
            self.machineConfig = {}
        return self.machineConfig

    def getUserConfig(self):
        if self.userConfig == None:
            self.userConfig = {}
        return self.userConfig

    def getServerConfig(self):
        if self.serverConfig == None:
            self.serverConfig = {}
        return self.serverConfig

    def getPasswordConfig(self):
        if self.passwordConfig == None:
            self.passwordConfig = {}
        return self.passwordConfig

    def getLanguageConfig(self):
        if self.languageConfig == None:
            self.languageConfig = {}
        return self.languageConfig

    def loadCreaturesFilesystemIntoMachineConfigAsThePrimaryReadwriteFilesystem(self, creaturesFilesystem):
        self.loadCreaturesFilesystemIntoMachineConfig(creaturesFilesystem, None)

    def loadCreaturesFilesystemIntoMachineConfigAsTheAuxiliaryReadonlyFilesystem(self, creaturesFilesystem):
        """Technically the engine supports more than one "Auxiliary" filesystem,
        but I don't think it does in practice X'D  (hence why the RO datas has to
        be merged into packs ;; )"""
        # Todo: set "Auxiliary 2 Images Directory" specificallies ???
        self.loadCreaturesFilesystemIntoMachineConfig(creaturesFilesystem, 1)

    def loadCreaturesFilesystemIntoMachineConfig(self, creaturesFilesystem, auxnum):
        """
        Loads all the 'Xyz Directory' config keys in from the CreaturesFilesystem object ^_^
        This is something you HAS ta call, otherwise there will be no data directories! D:

        The first arg is the CreaturesFilesystem instance,
        and the second arg is an integer,
            None makes for "Bootstrap Directory", "Images Directory", etc.
            1 makes for "Auxiliary 1 Bootstrap Directory", "Auxiliary 1 Images Directory", etc.
            2 makes for "Auxiliary 2 Bootstrap Directory", "Auxiliary 2 Images Directory", etc.
            etc.  :>
        """

        a = "Auxiliary " + repr(auxnum) + " " if auxnum != None else ""

        if self.machineConfig == None:
            self.machineConfig = {}

        self.machineConfig[a + "Main Directory"] = creaturesFilesystem.Main_Directory
        self.machineConfig[a + "Backgrounds Directory"] = creaturesFilesystem.Backgrounds_Directory
        self.machineConfig[a + "Body Data Directory"] = creaturesFilesystem.Body_Data_Directory
        self.machineConfig[a + "Bootstrap Directory"] = creaturesFilesystem.Bootstrap_Directory
        self.machineConfig[a + "Catalogue Directory"] = creaturesFilesystem.Catalogue_Directory
        self.machineConfig[a + "Creature Database Directory"] = creaturesFilesystem.Creature_Database_Directory
        self.machineConfig[a + "Exported Creatures Directory"] = creaturesFilesystem.Exported_Creatures_Directory
        self.machineConfig[a + "Genetics Directory"] = creaturesFilesystem.Genetics_Directory
        self.machineConfig[a + "Images Directory"] = creaturesFilesystem.Images_Directory
        self.machineConfig[a + "Journal Directory"] = creaturesFilesystem.Journal_Directory
        self.machineConfig[a + "Overlay Data Directory"] = creaturesFilesystem.Overlay_Data_Directory
        self.machineConfig[a + "Resource Files Directory"] = creaturesFilesystem.Resource_Files_Directory
        self.machineConfig[a + "Sounds Directory"] = creaturesFilesystem.Sounds_Directory
        self.machineConfig[a + "Users Directory"] = creaturesFilesystem.Users_Directory
        self.machineConfig[a + "Worlds Directory"] = creaturesFilesystem.Worlds_Directory

    #

    def readInitialSkeletonConfigFileDataFromEngineTemplate(self):
        """
        Read in basic skeleton config in from the files in self.roEngineTemplateDir  ^_^
        """

        def readConf(fileBasename, originalDict):
            p = os.path.join(self.roEngineTemplateDir,
                             fileBasename)  # NOTE the different dir here compared with readPostConf! :>

            if os.path.lexists(p):
                self.log("Reading skeleton config from: " + repr(p))

                c = readallText(p)
                newstuff = parseCreaturesConfig(c)

                if originalDict == None:
                    return newstuff
                else:
                    originalDict.update(newstuff)
                    return originalDict
            else:
                self.log("Skipping non-existant skeleton config file: " + repr(p))
                return originalDict

        self.machineConfig = readConf("machine-skel.cfg", self.machineConfig)
        self.userConfig = readConf("user-skel.cfg", self.userConfig)
        self.serverConfig = readConf("server-skel.cfg", self.serverConfig)
        self.passwordConfig = readConf("password-skel.cfg", self.passwordConfig)
        self.languageConfig = readConf("language-skel.cfg", self.languageConfig)

    #

    def setPort(self, port):
        if not (port == None or isinstance(port, int)):
            raise TypeError("Wrong type for port, should be an integer!  Instead got a " + repr(type(port)) + "  ;_;")

        self.log("Setting port to: " + (repr(port) if port != None else "<autofind>") + "  ^^")

        self.getUserConfig()["Port"] = repr(port) if port != None else None

    def setPortToAutofindRightBeforeStart(self):
        "note: this is the default ^_^"
        self.setPort(None)

    def isPortSetToAutofindRightBeforeStart(self):
        return self.getPort() == None

    def getPort(self):
        "note: if it was set to auto-find (setPortToAutofindRightBeforeStart()), then you can use this after the engine has been started to figure out which port it's using! ^w^"

        if self.userConfig == None:
            return None

        p = self.userConfig.get(
            "Port")  # not being there should count same as == None because autofind is a nice default /thinks :>'
        return int(p) if p != None else None

    def setAllowNetworkCaosConnections(self, insecureConnectionsEnabled):
        if insecureConnectionsEnabled:
            self.getUserConfig()["PortSecurity"] = "0"
        else:
            self.getUserConfig()["PortSecurity"] = "1"

    def isAllowingNetworkCaosConnections(self):
        if self.userConfig == None or not "PortSecurity" in self.userConfig:
            raise Exception("I dunno!  It hasn't been configured yet! :P")

        if self.userConfig["PortSecurity"] == "0":
            return True
        elif self.userConfig["PortSecurity"] == "1":
            return False
        else:
            raise Exception("Config error I think; PortSecurity should be either 0 or 1  (right?) ;_;")

    def setPrimaryGameName(self, primaryGameName):
        """eg, setPrimaryGameName("Docking Station", "Creatures 3")  :> """

        self.log("Setting primary game name to: " + repr(primaryGameName))

        self.getMachineConfig()["Game Name"] = primaryGameName

    def setAuxiliaryGameName(self, auxiliaryGameName):
        """eg, setAuxiliaryGameName("Creatures 3")  :> """

        self.log("Setting auxiliary game name to: " + repr(auxiliaryGameName))

        self.getMachineConfig()[
            "Win32 Auxiliary Game Name 1"] = auxiliaryGameName  # no earthly clue why "Win32" is in there XD'?!

    def getPrimaryGameName(self):
        if self.machineConfig == None:
            return None

        return self.machineConfig.get(
            "Game Name")  # get(), as opposed to [], returns None instead of raising KeyError  ^w^

    def getAuxiliaryGameName(self):
        if self.machineConfig == None:
            return None

        return self.machineConfig.get("Win32 Auxiliary Game Name 1")

    # Todo: more structured config things, mayhaps? :>?

    def _errWrongState(self):
        return TransientLC2ESessionStateException(
            "It's in the wrong state! ;_;   (it is currently " + TransientLC2ESession.fmtstate(self.state) + " ;; )")

    def start(self):
        """
        Start the lc2e engine!! :D!
        + If this *doesn't* throw/raise an error, then it will be properly in the Running state ^^'
        """

        if self.state != TransientLC2ESession.State_Unstarted:
            raise self._errWrongState()

        # Finish configuring! :D
        if self.isPortSetToAutofindRightBeforeStart():
            self.log("Autofinding port! :D")
            self.autoFindAndSetPort()

        if self.isRWActiveSessionEngineDirSetToAutonameRightBeforeStart():
            self.log("Autocreating session engine dir! :D")
            self.autoFindAndCreateSessionEngineDir()
            autocreatedEngineDir = True
        else:
            autocreatedEngineDir = False

        if self.isRWActiveSessionHomeDirSetToAutocreateInsideEngineDirRightBeforeStart():
            self.log("Autocreating session home dir! :D")
            self.autoCreateSessionHomeDir()
            autocreatedHomeDir = True
        else:
            autocreatedHomeDir = False

        # (important that registering cleaners for the just-created session dir comes right after making it ^^   since _actuallyStartXD() and autoFindAndSetPort() could fail/raise-exceptions! ;; )
        # Register an atexit and garbage collection hooks to clean up the state if somepony forgets to and the python virtual machine terminates ;3

        # Create a separate cleaner object which will be registered as a garbage collection listener here also, to same effect if we learn this object becomes lost *before* python actually terminates ;3
        self.cleaner = _lc2eSessionCleaner(self.rwActiveSessionEngineDir if autocreatedEngineDir else None,
                                           self.rwActiveSessionHomeDir if autocreatedHomeDir else None)  # PASS ALL THE THINGS NEEDED FOR CLEANING :>    (which turns out to just be the session dir XD)
        self.cleaner.registerAsGCListener()
        self.cleaner.registerAsAtExitHook()

        try:
            self._actuallyStartXD()
        except:
            self.cleaner.actuallyCleanUpXD()
            self.setState(
                TransientLC2ESession.State_CleanedUpNeverProperlyStarted)  # Always good to set state after cleaning up Ithinks, in case the cleanup fails XD'  :>
            raise  # re-raise the exception! :>

        self.setState(TransientLC2ESession.State_Running)  # don't mark it as running unless that succeeded YD

        # Start a thread to wait on the process and promptly switch state to Terminated as soon as the engine terminated! ^w^   (if it hasn't already! Ack!)
        processWaiterThread = threading.Thread(target=self.waitForEngineToTerminate,
                                               name="TransientLC2E Child Process Waiter")
        processWaiterThread.setDaemon(True)  # not an important thread >>
        processWaiterThread.start()

    #

    def autoFindAndSetPort(self):
        "Note: this is automatically called by start() if isPortSetToAutofindRightBeforeStart() is true, *right* before execution, to minimize chances of some other process snagging out port >,> xD'"

        # Try random numbers for awhile :>
        r = random.Random()  # I checked; it's initialized with different seeds or whatnot by default each construction ^w^   (so we all (python processes and/or TransientLC2ESession instances within a python process) won't all be trying the exact same "random" sequence each time! XD''! )
        for _ in range(1000):
            port = r.randint(49152,
                             65535)  # this is the official range ICANN specifies for randomly/automatically XD' picking ports, I think!  Yay standards! :D! (so it's supposed to not conflict with things that rigidly *need* a certain port to be available!!)    (there are exactly one fourth of all ports in this range! :D )
            if self._tryAcquireServerPort(port):
                self.setPort(port)
                return

        # If ALLLLLllll those were taken, just TRY ALL THE PORTS T-T
        for port in range(49152, 65535):
            if self._tryAcquireServerPort(port):
                self.setPort(port)
                return

        raise Exception("All ICANN dynamic/private ports ( [49152-65536) ) were taken! D:")

    #
    def _tryAcquireServerPort(self, port):
        # returns true if successful, false if port unavailable, or raises something if a different error occurs
        s = None
        try:
            s = socket.socket()  # default  Internet class,  TCP (server or client) socket
            s.bind(('localhost', port))
        except socket.error as exc:
            s.close()
            if exc.errno == errno.EADDRINUSE:  # Address already in use
                return False
            else:
                raise
        else:
            s.close()
            return True

    #

    def autoFindAndCreateSessionEngineDir(self, superDir=Transient_LC2E_TransientSessions_SuperDirectory):
        "Note: this is automatically called by start() if self.isRWActiveSessionEngineDirSetToAutonameRightBeforeStart() is true, *right* before execution, for convenience, and so it will be cleaned up as part of the normal cleanup cycle if something goes wrong ^_^"

        self.setRWActiveSessionEngineDir(getUnusedFileSimilarlyNamedTo(superDir, "autonamed-transient-lc2e-session"))

        os.mkdir(self.getRWActiveSessionEngineDir(), 0o755)

    #

    def autoCreateSessionHomeDir(self, parentDir=None):
        "Note: this is automatically called by start() if self.isRWActiveSessionHomeDirSetToAutocreateInsideEngineDirRightBeforeStart() is true, *right* before execution, for convenience, and so it will be cleaned up as part of the normal cleanup cycle if something goes wrong ^_^"

        if parentDir == None:
            parentDir = self.getRWActiveSessionEngineDir()

        self.setRWActiveSessionHomeDir(os.path.join(parentDir, "fakehome"))

        os.mkdir(self.getRWActiveSessionHomeDir(), 0o755)

    #

    def _actuallyStartXD(self):  # yes that's an emoticon in the function name      ..what?  I'm a puppy! ^w^

        # Okay so, FIRST
        # we link in the engine executable and lib[s] ^_^
        engineFilenamesToLinkIn = ["lc2e"] + self.libfilebasenamesInSameDirAsEngine

        self.log("Symlinking in the engine files and folders! :D")

        # Actually make teh links! :D
        for n in engineFilenamesToLinkIn:
            s = os.path.join(self.roEngineTemplateDir, n)
            d = os.path.join(self.rwActiveSessionEngineDir, n)

            if os.path.lexists(d):
                raise Exception("Symlink we tried to make already exists!? D:   (" + repr(s) + " -> " + repr(d) + ")")

            os.symlink(os.path.abspath(s), d)

        # And then figure out the library dirs and environment stuff! :D
        libdirs = list(filter(lambda bn: bn.startswith("lib"), os.listdir(self.roEngineTemplateDir)))
        print("after first filter")
        for e in libdirs:
            print(e)
        print("TemplateDir: " + self.roEngineTemplateDir)
        libdirs = list(
            map(lambda bn: os.path.join(self.roEngineTemplateDir, bn), libdirs))  # make them full paths! ^_^
        print("after second filter")
        for e in libdirs:
            print(e)
        libdirs = list(filter(lambda d: os.path.isdir(d), libdirs))
        print("after third filter")
        for e in libdirs:
            print(e)
        if any(map(lambda p: ":" in p, libdirs)):
            # Try the realpaths, maybe they're better! ;_;
            libdirs = map(os.path.realpath, libdirs)

            if any(map(lambda p: ":" in p, libdirs)):
                # Nope! T-T
                raise Exception(
                    "There are colons in the lib dirs, that makes UNIX explode D:  (because colons separate shared-library dirs in LD_LIBRARY_PATH and there isn't an escape syntax to my knowledge >,> )     Library dirs: " + repr(
                        libdirs))
        print("after realpaths-if")
        for e in libdirs:
            print(e)
        # Add the (future) current dir (eg, for lc2e-netbabel.so and others if someday there are others X3 )  ^_^
        allLibDirs = [
                         "."] + libdirs  # Note: "." will be a different place for the engine (rwActiveSessionEngineDir), when we start it in rwActiveSessionEngineDir ;>

        LD_LIBRARY_PATH = ":".join(allLibDirs)

        # Get the X11 display for, you know, graphics! XD   (that's important, don't forget that XD''')
        x11Display = os.getenv("DISPLAY")
        if x11Display == None:
            raise Exception(
                "There is no X11 display! D:   LC2E won't run without graphics!!  (although that might actually be useful for servers or stuff 8> )")

        # Write config files! :D!

        self.log("Writing engine configuration files! :D")

        def writeConf(fileBasename, configDict):
            if configDict == None:
                return  # skip! ^w^
            else:
                writeallText(os.path.join(self.rwActiveSessionEngineDir, fileBasename),
                             serializeCreaturesConfig(configDict))

        writeConf("machine.cfg", self.machineConfig)
        writeConf("user.cfg", self.userConfig)
        writeConf("server.cfg", self.serverConfig)
        writeConf("password.cfg", self.passwordConfig)
        writeConf("language.cfg", self.languageConfig)

        # ACTUALLY START! :D!!!
        exe = os.path.abspath(os.path.join(self.rwActiveSessionEngineDir,
                                           "lc2e"))  # EXEcutable in the general sense, not Microsoft Windows format XD'   (kind of like Dynamically Linked Library, or High-Definition DVD, etc.c.   .... #when companies grab generic names for their products >_>  XD' )

        env = {"LD_LIBRARY_PATH": LD_LIBRARY_PATH, "DISPLAY": x11Display, "HOME": self.rwActiveSessionHomeDir}

        cwd = self.rwActiveSessionEngineDir

        self.log("ACTUALLY STARTING THE ENGINE!! \\o/")
        self.log(repr(exe))
        self.log("\tCWD: " + repr(cwd))
        self.log("\tENV: " + json.dumps(env, indent=1, sort_keys=True))

        # None (python subprocess.Popen) = Inherit (java.lang.Process)  ^_^
        stdin = subprocess.PIPE if (self.dataToFeedToStdin != None and len(self.dataToFeedToStdin) > 0) else None
        stdout = subprocess.PIPE if self.captureStdout else None
        stderr = subprocess.PIPE if self.captureStderr else None

        self.process = subprocess.Popen([exe], executable=exe, cwd=cwd, env=env, stdin=stdin, stdout=stdout,
                                        stderr=stderr)  # the first arg here is arg0, which, as per Unix, is what the process will know itself as :>   (which is just exactly the same as the actual executable (symlink!) here XD   (but we still has to give it or things could explode D: )    the executable= part is prolly superfluous..but I like being explicits ^^' )

        if stdin != None:
            def feeder():
                self.process.stdin.write(self.dataToFeedToStdin)
                self.process.stdin.close()

            thread = threading.Thread(target=feeder, name="Dumper")
            thread.daemon = True
            thread.start()

        def spawnCollector(source, store, buffsize=4096):
            def run():
                captured = bytearray()

                while True:
                    b = source.read(buffsize)
                    if len(b) == 0:  # zero-length read means EOF in python and C but not Java :P
                        store(str(captured))  # meh, python likes str's over bytearrays, ohwells :P
                        source.close()
                        return
                    else:
                        captured += b

            #

            thread = threading.Thread(target=run, name="Collector")
            thread.daemon = True
            thread.start()
            return thread

        #

        if stdout != None:
            def setstdout(x): self.postStdout = x;

            self.stdoutCollector = spawnCollector(self.process.stdout, setstdout)

        if stderr != None:
            def setstderr(x): self.postStderr = x;

            self.stderrCollector = spawnCollector(self.process.stderr, setstderr)

    #

    def setState(self, newState):
        self.log("State set to: " + TransientLC2ESession.fmtstate(newState))

        self.state = newState

        if self.cleaner != None:
            self.cleaner.state = newState

        if newState == TransientLC2ESession.State_Terminated:
            self._reapThingsAfterTermination()  # :D

    #

    def waitForEngineToTerminate(self):
        # Todo add an optional timeout parameter? :p

        # I didn't add locks here..and this is what happened:
        # print("WAITING: STATE IS "+TransientLC2ESession.fmtstate(self.state));
        # (water thread started and called this in self.start())
        # (main thread called this in main())
        #   "WAITING: STATE IS running"
        #   "WAITING: STATE IS running"
        # Classic. Threading. Bug.  X'D'''

        self.waitLock.acquire()

        try:
            if self.state == TransientLC2ESession.State_Running:
                pass;
            elif (
                    self.state == TransientLC2ESession.State_Terminated or self.state == TransientLC2ESession.State_CleanedUp or self.state == TransientLC2ESession.State_CleanedUpNeverProperlyStarted):
                return
            else:
                raise self._errWrongState()

            self.exitStatus = self.process.wait()  # I checked!  It does return instantly if the process completes/terminates SUPERINCREDIBLYFAST before we even call this!!  ^w^

            self.log("LC2E terminated!, exit status: " + repr(self.exitStatus))

            # If we don't compleeeeteelyyyy wait for these to be all the dones, we can't guarantee that we'll have postStdout/postStderr! ;-;
            if self.captureStdout:
                self.stdoutCollector.join()

            if self.captureStderr:
                self.stderrCollector.join()

            self.setState(TransientLC2ESession.State_Terminated)  # will reap the things ^_^
        finally:
            self.waitLock.release()

    #

    def _reapThingsAfterTermination(self):
        # Read post-log file :>
        self.log("Reading the logfile the engine wrote, for explorative purposes :>")

        logfile = os.path.join(self.getRWActiveSessionEngineDir(), "creatures_engine_logfile.txt")
        if os.path.isfile(logfile):
            self.postLogfile = readallText(logfile)
        else:
            self.postLogfile = None

        # Read post-config files :>
        self.log("Re-reading the config files the engine rewrote, for explorative purposes :>")

        def readPostConf(fileBasename):
            p = os.path.join(self.getRWActiveSessionEngineDir(),
                             fileBasename)  # NOTE the different dir here compared with readConf! :>
            if os.path.lexists(p):
                c = readallText(p)
                return parseCreaturesConfig(c), c
            else:
                return None, None

        self.postMachineConfig, self.postMachineConfigRaw = readPostConf("machine.cfg")
        self.postUserConfig, self.postUserConfigRaw = readPostConf("user.cfg")
        self.postServerConfig, self.postServerConfigRaw = readPostConf("server.cfg")
        self.postPasswordConfig, self.postPasswordConfigRaw = readPostConf("password.cfg")
        self.postLanguageConfig, self.postLanguageConfigRaw = readPostConf("language.cfg")

        self.log("Checking to see if there are any *other* files we weren't expecting to be there! :o")
        expectedFileBasenames = set(
            ["lc2e"] + self.libfilebasenamesInSameDirAsEngine + ["machine.cfg", "user.cfg", "server.cfg",
                                                                 "password.cfg", "language.cfg"] + [
                "creatures_engine_logfile.txt"])
        if (os.path.dirname(os.path.abspath(self.getRWActiveSessionHomeDir())) == os.path.abspath(
                self.getRWActiveSessionEngineDir())):
            expectedFileBasenames.add(os.path.basename(self.getRWActiveSessionHomeDir()))

        actualFileBasenames = set(os.listdir(self.getRWActiveSessionEngineDir()))

        self.postUnexpectedFileBasenames = actualFileBasenames - expectedFileBasenames  # don't ya love operators! 8>    (when they are mapped, that is >,>    (*grumbles at lack of "+" for sets in python*   X'D )
        self.postAbsentExpectedFileBasenames = expectedFileBasenames - actualFileBasenames

        if self.didEngineCrash():
            # Note: musht be called afterwards, so it has alllll the happy postXYZ things! ^^
            self._produceCrashReportPackage()

    #

    def _produceCrashReportPackage(self):
        if self.errorReportPackagesDirectory != None:
            crashReportPackageDir = os.path.join(self.errorReportPackagesDirectory,
                                                 os.getenv("USER") + "@" + socket.gethostname() + ":" + repr(
                                                     time.time()))
            if os.path.lexists(crashReportPackageDir):
                # It already exists!? ;_;!?
                # ohwell; uhh, just silently do nothing.  If things are happening so much that multiple TransientLC2ESession's are doing things at the same *microsecond* (or milli or nano, or whatever precision time.time() happens to be on the current OS ^^' ), then there are many other things that would break XD''   Like checking for unique filenames *then* creating it (in which two people could 'discover' the same available name, then both try to create a file with that name ><!   Oh non-holistic operating systems..there are so many issues with yall X'D )
                return

            os.mkdir(crashReportPackageDir)

            if self.state == TransientLC2ESession.State_CleanedUpNeverProperlyStarted:
                writeallText(os.path.join(crashReportPackageDir, "never-started"), ";_;")

            else:
                writeallText(os.path.join(crashReportPackageDir, "exit-status"), repr(self.exitStatus))

                writeallText(os.path.join(crashReportPackageDir, "transientlc2e.log"), self.capturedLog)

                if self.dataToFeedToStdin != None:
                    writeallText(os.path.join(crashReportPackageDir, "provided-stdin"), self.dataToFeedToStdin)
                else:
                    writeallText(os.path.join(crashReportPackageDir, "didnt-provide-stdin"), "nope")

                if self.captureStdout:
                    if self.postStdout == None: raise AssertionError();
                    writeallText(os.path.join(crashReportPackageDir, "stdout.out"), self.postStdout)
                else:
                    writeallText(os.path.join(crashReportPackageDir, "didnt-capture-stdout"), "nope ,_,")

                if self.captureStderr:
                    if self.postStderr == None: raise AssertionError();
                    writeallText(os.path.join(crashReportPackageDir, "stderr.out"), self.postStderr)
                else:
                    writeallText(os.path.join(crashReportPackageDir, "didnt-capture-stderr"), "nope ,_,")

                if self.postLogfile == None:
                    writeallText(os.path.join(crashReportPackageDir, "there-was-no-creatures_engine_logfile.txt"),
                                 "nope")
                else:
                    writeallText(os.path.join(crashReportPackageDir, "creatures_engine_logfile.txt"), self.postLogfile)

                writeallText(os.path.join(crashReportPackageDir, "unexpected-files"),
                             repr(self.postUnexpectedFileBasenames))
                writeallText(os.path.join(crashReportPackageDir, "absent-expected-files"),
                             repr(self.postAbsentExpectedFileBasenames))

                def logAConfig(basename, preDict, postDict, postSer):
                    if preDict == None:
                        writeallText(os.path.join(crashReportPackageDir, "provided-" + basename + "-not-given"),
                                     "nope :p")
                    else:
                        preSer = serializeCreaturesConfig(
                            preDict)  # will produce exactly the same output as it did when we originally created the file to give to the engine (I DO SO HOPE XD'')
                        writeallText(os.path.join(crashReportPackageDir, "provided-" + basename), preSer)
                        writeallText(os.path.join(crashReportPackageDir, "provided-" + basename + ".pyrepr"),
                                     repr(preDict))

                    if postSer == None:
                        writeallText(os.path.join(crashReportPackageDir, "reaped-" + basename + "-not-detected"),
                                     "nope ._.")
                    else:
                        if preDict != None and postSer == preSer:
                            writeallText(os.path.join(crashReportPackageDir,
                                                      "reaped-" + basename + "-was-EXACTLY-equal-to-provided"), "yup!")
                        else:
                            writeallText(os.path.join(crashReportPackageDir, "reaped-" + basename), postSer)
                            writeallText(os.path.join(crashReportPackageDir, "reaped-" + basename + ".pyrepr"),
                                         repr(postDict))

                logAConfig("machine.cfg", self.machineConfig, self.postMachineConfig, self.postMachineConfigRaw)
                logAConfig("user.cfg", self.userConfig, self.postUserConfig, self.postUserConfigRaw)
                logAConfig("server.cfg", self.serverConfig, self.postServerConfig, self.postServerConfigRaw)
                logAConfig("password.cfg", self.passwordConfig, self.postPasswordConfig, self.postPasswordConfigRaw)
                logAConfig("language.cfg", self.languageConfig, self.postLanguageConfig, self.postLanguageConfigRaw)

            self.log("Error report package written to: " + repr(crashReportPackageDir))

    #

    def checkEngineTerminatedOrCleanedUp(self):
        if self.state != TransientLC2ESession.State_Terminated and self.state != TransientLC2ESession.State_CleanedUp:
            raise self._errWrongState()

    def didEngineCrash(self):
        self.checkEngineTerminatedOrCleanedUp()

        return self.exitStatus != 1  # apparently LC2E return a failure exit code (ie, anything but 0 XD, as per POSIX) even when it completes properly! o,0   Ohwells! Just go with it! XD

    #

    def runcaos(self, caoscode):
        if self.state != TransientLC2ESession.State_Running:
            raise self._errWrongState()

        try:
            s = socket.socket()
            s.connect(("localhost", self.getPort()))

            try:
                s.sendall((
                                  caoscode + "\r\nrscr\r\n").encode())  # we could use the fileything from s.makefile() but prolly fasters to use this nice thing here :3    (we are lazy to use the makefile down below >,> )
                f = s.makefile()
                response = f.read()

            finally:  # ie, make SURE this is called, even if it throws an exception! ;D
                s.close()

            return response
        except socket.error as e:
            if e.errno == errno.ECONNREFUSED:
                raise TransientLC2ESessionCAOSConnectionRefused()
            else:
                raise

    #

    def waitForEngineToBecomeCaosable(self):
        if self.state != TransientLC2ESession.State_Running:
            raise self._errWrongState()

        while True:
            try:
                r = self.runcaos("setv va00 9  mulv va00 va00  outv va00")
            except TransientLC2ESessionCAOSConnectionRefused:
                pass;
            else:
                return

            time.sleep(.1)

    #

    def quitWithoutSaving(self):
        #  ^_^
        self.runcaos("quit")
        self.waitForEngineToTerminate()

    def saveAndQuit(self):
        #  ^_^
        self.runcaos("save quit")
        self.waitForEngineToTerminate()

    def brutallyKillEngine(self):
        if self.state != TransientLC2ESession.State_Running:
            raise self._errWrongState()

        os.kill(self.pid,
                2)  # Signal 2 is SIGINT ("Interrupt" :> )   (ie, this is what the shell does when you press Ctrl-C in its terminal! :D )
        self.waitForEngineToTerminate()

    def viciouslyKillEngine(self):
        "I am traumatizing myself with these names T,T"

        if self.state != TransientLC2ESession.State_Running:
            raise self._errWrongState()

        os.kill(self.pid, 9)  # Signal 9 is SIGKILL ie, vicious (unignorable signal!) ;_;
        self.waitForEngineToTerminate()

    def cleanUp(self):
        "Remove the transient instance directory and etc. etc.! ^w^"

        if self.state != TransientLC2ESession.State_Terminated:
            raise self._errWrongState()

        self.cleaner.actuallyCleanUpXD()

        # Always good to set state to [completely-]cleaned-up after cleaning up Ithinks, in case the cleanup fails XD'  :>
        self.setState(TransientLC2ESession.State_CleanedUp)  # sets the cleaner's state too :3
    #