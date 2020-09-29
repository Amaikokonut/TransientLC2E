import atexit
import os
import weakref

import transientLC2ESession

_GlobalGCListeners = set()
class _lc2eSessionCleaner(object):
    """
    Note that this doesn't terminate the engine, so if we stop while it's still going, just leave it be and let the userpeoples worry about cleaning up the transient session directory and such X3

    TODO EXPLAIN WHY NECESSARY ;;''''
    """


    state = None

    # <All the things necessary for actually cleaning up! :D
    rwActiveSessionEngineDir = None
    rwActiveSessionHomeDir = None

    # All the things necessary for actually cleaning up! :D >

    def __init__(self, rwActiveSessionEngineDir, rwActiveSessionHomeDir):
        self.rwActiveSessionEngineDir = rwActiveSessionEngineDir
        self.rwActiveSessionHomeDir = rwActiveSessionHomeDir

    #

    def registerGCListener(referent, nullaryCallback):
        # "If callback is provided and not None, and the returned weakref object is still alive, the callback will be called when the object is about to be finalized"...
        # So python, like Java, *almost* provides garbage-collection listeners XD'
        # We just need to make sure the weak reference objects stay alive (which is kind of arbitrary; in a real GC-listener system like I made up (XD'), it wouldn't even require that :> )

        def gclistener(theweakref, _GlobalGCListeners=None):
            _GlobalGCListeners.remove(theweakref)  # how nice of them to provide it to us! :D
            nullaryCallback()

        # note: because we're currently holding a (strong) reference to the referent, the GC listener won't be called between when (after) the weakref.ref() is created but before it's added to the global listeners set!  ^_^
        r = weakref.ref(referent)

        _GlobalGCListeners.add(r)

    def registerAsGCListener(self):
        self.registerGCListener(self.cleanUpIfNeeded)

    def registerAsAtExitHook(self):
        atexit.register(self.cleanUpIfNeeded)

    def cleanUpIfNeeded(self):
        if self.state == transientLC2ESession.State_Terminated:
            self.actuallyCleanUpXD()
            self.state = transientLC2ESession.State_CleanedUp  # also set by the actual session if that's what called us, but if not then we need to set it on ourselves! (BECAUSE THE SESSION IS GONNEEEEE! ;_;   x3 )

    #

    def actuallyCleanUpXD(self):
        # I assume exceptions/errors raised/thrown to atexit hook callers and garbage collection listeners (weakref callbacks) aren't problems and handled nicelies? ^^''?

        def unlinkIfThere(x):
            if os.path.lexists(x) and not os.path.isdir(x):
                os.unlink(x)

        def rmdirIfThere(x):
            if os.path.isdir(x):
                os.rmdir(x)

        if self.rwActiveSessionHomeDir != None:
            unlinkIfThere(os.path.join(self.rwActiveSessionHomeDir, ".creaturesengine", "port"))
            rmdirIfThere(os.path.join(self.rwActiveSessionHomeDir, ".creaturesengine"))
            rmdirIfThere(self.rwActiveSessionHomeDir)

        if self.rwActiveSessionEngineDir != None:
            # Just simply unlink/delete all the symlinks and plain files (creatures_engine_logfile.txt and rewritten config files)  ^_^
            for n in os.listdir(self.rwActiveSessionEngineDir):
                p = os.path.join(self.rwActiveSessionEngineDir, n)
                os.unlink(p)

            # Then get rid of the whole dir! :D
            rmdirIfThere(self.rwActiveSessionEngineDir)
    #
