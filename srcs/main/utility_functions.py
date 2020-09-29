import errno
import os


def isany(predicate, iterable):
    for x in iterable:
        if predicate(x):
            return True
    return False


def isall(predicate, iterable):
    for x in iterable:
        if not predicate(x):
            return False
    return True

def getsize(f, derefSymlinks=True):
    """
    find the size of the given file.
    If the file is not a file or is not accessible, 0 is returned.
    """
    try:
        if derefSymlinks:
            if os.path.isfile(f):
                return os.path.getsize(f)
            else:
                return 0
        else:
            if os.path.islink(f) or os.path.isfile(f):
                return os.lstat(f).st_size
            else:
                return 0
    except OSError as exc:
        if exc.errno == errno.EACCES:  # Permission denied
            return 0
        elif exc.errno == errno.ENOENT:  # File not found
            return 0
        else:
            raise

def writeallText(f, content, append=False):
    if os.path.lexists(f):
        raise OSError("Can't overwrite: file node exists: " + f)
    else:
        p = open(f, "w" if not append else "a")

        try:
            if not append:
                p.truncate(
                    0)  # be explicit!  (this step is normally done automatically in unix at least; but lets be allll the explicits! ^w^ )
            p.write(content)
        finally:
            p.close()


#
def readallText(f, sanityLimit=16777216):
    if getsize(f, derefSymlinks=True) > sanityLimit:
        raise Exception("File " + f + " is larger than sanityLimit " + repr(sanityLimit) + " :O")

    p = open(f, "rU")

    try:
        c = p.read(sanityLimit)
    finally:
        p.close()

    return c

def getUnusedFileSimilarlyNamedTo(directory, similarlyNamedToThisBasename):
    "Note: takes a Basename, returns a Pathname!"

    # If that name actually isn't taken up, then use that of course! :D
    f = os.path.join(directory, similarlyNamedToThisBasename)

    if not os.path.lexists(f):
        return os.path.abspath(f)

    # But if not then we'll haves to find an unused name >,>
    if ("." in similarlyNamedToThisBasename and similarlyNamedToThisBasename.rindex(
            ".") == 0):  # and not starts with "." (which means hidden-file on unixen, not extension :3 )
        stemName, extension = similarlyNamedToThisBasename.rsplit(".", 1)
        suffix = "." + extension
    else:
        stemName = similarlyNamedToThisBasename
        suffix = ""

    i = 2
    while True:
        f = os.path.join(directory, stemName + " " + repr(i) + suffix)

        if not os.path.lexists(f):
            return os.path.abspath(f)

        i += 1