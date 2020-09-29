import os

from utility_functions import readallText, writeallText, getUnusedFileSimilarlyNamedTo


class CreaturesFilesystem(object):
    base = None

    def __init__(self, base):
        base = os.path.abspath(base)

        self.base = base
        self.configureForDefaults()

    #

    def configureForDefaults(self):
        base = self.base  # shortness ^^

        # Standard creatures defaults! :D
        self.Main_Directory = os.path.join(base, "Main")  # ????
        self.Backgrounds_Directory = os.path.join(base, "Backgrounds")  # BLK background files :>
        self.Body_Data_Directory = os.path.join(base, "Body Data")  # Attachment files :3
        self.Bootstrap_Directory = os.path.join(base, "Bootstrap")  # Cos files! :D
        self.Catalogue_Directory = os.path.join(base, "Catalogue")  # Catalogue files! ^_^
        self.Creature_Database_Directory = os.path.join(base, "Creature Galleries")  # ????
        self.Exported_Creatures_Directory = os.path.join(base, "My Creatures")  # Pray files :3
        self.Genetics_Directory = os.path.join(base,
                                               "Genetics")  # GEN (genetics) and GNO (genetics annotation) files! :>
        self.Images_Directory = os.path.join(base, "Images")  # C16 and S16 files! :D
        self.Journal_Directory = os.path.join(base, "Journal")  # Journal text files! :D
        self.Overlay_Data_Directory = os.path.join(base, "Overlay Data")  # C16 and S16 files! :>
        self.Resource_Files_Directory = os.path.join(base, "My Agents")  # Pray files :3
        self.Sounds_Directory = os.path.join(base, "Sounds")  # (MS)Wave (sfx) and Munge (music) files! :D
        self.Users_Directory = os.path.join(base, "Users")  # ????
        self.Worlds_Directory = os.path.join(base, "My Worlds")  # Serialized, zlib-compressed world memoryimages! :D

    #

    def readJournalFile(self, journalFile):
        "Returns None if and only if the file doesn't exist (raises exceptions otherwise :> )"

        jf = os.path.abspath(os.path.join(self.Journal_Directory, journalFile))

        if not os.isfile(jf):
            return None
        else:
            return readallText(jf)

    #

    def writeJournalFile(self, journalFile, contents):
        "Write (overwrite if exists!) a journal file in the current session! ^w^"

        jf = os.path.abspath(os.path.join(self.Journal_Directory, journalFile))

        writeallText(journalFile, contents)

    #

    def linkInPrimaryDirectory(self, extantToplevelDirectory, pathnameInThisFilesystem=None):
        "For linking in eg, the ENTIRE IMAGES/ FOLDER :O   :> "

        if pathnameInThisFilesystem == None:
            pathnameInThisFilesystem = os.path.join(self.base, os.path.basename(extantToplevelDirectory))

        self.linkInAFileFailing(extantToplevelDirectory, pathnameInThisFilesystem)

    def linkInAgentFile(self, extantAgentFile):
        self.linkInAFileRenaming(extantAgentFile, self.Resource_Files_Directory)  # eg, "My Agents" :>

    def linkInExportedCreatureFile(self, extantCreatureFile):
        self.linkInAFileRenaming(extantCreatureFile, self.Exported_Creatures_Directory)  # eg, "My Creatures" :>

    def linkInWorld(self, extantWorldFolder):
        self.linkInAFileRenaming(extantWorldFolder, self.Worlds_Directory)  # eg, "My Worlds" :>

    def linkInWholeFolder_IgnoringConflicts(self, sourceFolder, destFolder):
        sourceFolder = os.path.abspath(sourceFolder)
        destFolder = os.path.abspath(destFolder)

        for n in os.listdir(sourceFolder):
            s = os.path.join(sourceFolder, n)
            d = os.path.join(destFolder, n)

            if os.path.lexists(d):
                continue

            os.symlink(s, d)

    #

    def linkInWholeFolder_ErringOnConflicts(self, sourceFolder, destFolder):
        sourceFolder = os.path.abspath(sourceFolder)
        destFolder = os.path.abspath(destFolder)

        for n in os.listdir(sourceFolder):
            s = os.path.join(sourceFolder, n)
            d = os.path.join(destFolder, n)

            if os.path.lexists(d):
                raise Exception("AHHHHHH CONFLICT!!  WE DON'T LIKE CONFLICT!!  T_T    (conflict between source " + repr(
                    s) + " and dest " + repr(d) + "  ;_; )")

            os.symlink(s, d)

    #

    def linkInWholeFolder_RenamingConflicts(self, source_folder, destFolder):
        source_folder = os.path.abspath(source_folder)
        destFolder = os.path.abspath(destFolder)

        for n in os.listdir(source_folder):
            s = os.path.join(source_folder, n)
            d = os.path.join(destFolder, n)

            if os.path.lexists(d):
                d = getUnusedFileSimilarlyNamedTo(os.path.dirname(d), n)

            os.symlink(s, d)

    #

    def linkInAFileRenaming(self, extantFile, directory):
        extantFile = os.path.abspath(extantFile)
        directory = os.path.abspath(directory)

        bn = os.path.basename(extantFile)

        newFile = getUnusedFileSimilarlyNamedTo(directory, bn)

        os.symlink(extantFile, newFile)

    #

    def linkInAFileFailing(self, extantFile, directory):
        extantFile = os.path.abspath(extantFile)
        directory = os.path.abspath(directory)

        bn = os.path.basename(extantFile)

        newFile = os.path.join(directory, bn)

        if os.path.lexists(newFile):
            raise Exception(
                "File we're trying to link already exists with same name in destination directory! D:   (tried to link " + repr(
                    extantFile) + " into " + repr(directory) + "  ;_; )")

        os.symlink(extantFile, newFile)
    #