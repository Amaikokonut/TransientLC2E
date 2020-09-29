# Config file syntax! :D
#   + Just a bunch of lines of <key> + " " + <value> + linebreak  ^_^
#       + The key and value can be quoted with double-quotes to allow spaces and special characters, or not! ^_^
#       + Note: even if it is quoted, if a linebreak is inside a string, it will break (specifically, for values at least, it will just exactly stop reading it at the end of the line :3 )
#       + Linebreaks *CAN* be *encoded* into strings, though!  Just use the escape syntax below! :D
#   + Comments begin with "#" and last to the end of the line; they can happen anywhere in the file not just eg, at line start!! (although if it appears in a quoted string it will be part of the quotes!)   :D
#   + Empty lines are ignored :3
#   + Case SENSITIVE!
#   + Non-quoted strings interpret backslashes and double-quotes as just normal parts of the string!  (there are no escapes inside non-quoted strings!)
#
#   + Note: the engine checks that non-auxiliary directories exist before startup! (but not auxiliary ones!) (is usefuls for figuring out syntax ;}  XD  )

# Config file escape codes! :D
#   \\  \
#   \"  "
#   \n  <LF>
#   \r  <CR>
#   \t  <TAB>
#
# + Also, it is strict.  Any invalid escape codes produce a syntax error
#
# Not config file escape codes!
#   + I tried all individual lowercase latin letters and arabic numerals as escape codes, only the above work (which is enough! :> )
#   + I tried \x## \u## \u#### \u######## \U######## (and \0 as mentioned above) with no success

ConfigFileEscapeCodeDict = {
    "\\": "\\",
    "\"": "\"",
    "n": "\n",
    "r": "\r",
    "t": "\t",
}


def parseCreaturesConfig(configFileContents):
    source = configFileContents

    try:
        configDict = {}

        _Key = 0
        _Value = 1
        _LineEnd = 2
        which = _Key

        _BeforeString = 0
        _InQuotedString = 1
        _InQuotedString_InEscape = 2
        _InNonquotedString = 3
        _InComment = 4
        where = _BeforeString

        start = None
        currKey = None

        # Note: some of the "continue"s are superfluous; I just like being explicits sometimes ^^'

        def descapestr(s):
            if not "\\" in s:  # superfast check! :D
                # there are no escapes! we don't need to descape! :D

                # print("DEBUGPARSER) descapestr(): passthrough, no descaping! ^w^  "+repr(s));

                return s
            else:
                # aw ._.  XD

                descapedStr = ""

                st = 0  # can't use 'start', that would conflict! ><  X'D
                while True:
                    # s.index would throw exception instead of returning special value (-1)  ;>'
                    e = s.find("\\", st)  # can't use 'i', that would conflict! ><  X'D

                    if e == -1:
                        break
                    else:
                        if (
                                st != e):  # ie, not-empty string between start of last run of clear text (st) and the next backslash (e)  ^w^
                            if st > e: raise AssertionError();
                            descapedStr += s[st:e]

                        if not (e + 1 < len(s)):
                            raise AssertionError()  # we should never have been passed one with a trailing backslash! ;-;
                        else:
                            escapeCode = s[e + 1]

                            if not escapeCode in ConfigFileEscapeCodeDict:
                                raise Exception("Syntax error!: bad escape code " + repr(escapeCode) + " !")

                            descapedStr += ConfigFileEscapeCodeDict[escapeCode]

                            st = e + 2  # after the escape char (backslash) AND the escape code! :3   (which may be EOF, but that's okay, we check for that down there! and x[len(x):len(x)] is valid in python anyways, returning empty string! ^w^ )

                if (st != len(
                        s)):  # ie, not-empty string between start of last run of clear text (st) and the end of the string!  ^w^
                    if st > len(s): raise AssertionError();
                    descapedStr += s[st:]

                # print("DEBUGPARSER) descapestr(): descaped "+repr(s)+" into "+repr(descapedStr)+"  :D");

                return descapedStr

        def consumestr(s, descapeit):
            if which == _Key:
                _currKey = descapestr(s) if descapeit else s
                _which = _Value

            elif which == _Value:
                value = descapestr(s) if descapeit else s
                if currKey in configDict:
                    raise Exception("Syntax error!: duplicate key " + repr(currKey) + " ;_;")
                configDict[currKey] = value

                _currKey = None
                _which = _LineEnd

            elif which == _LineEnd:
                raise Exception("Syntax error!: more than two strings on one line! o,0")
            else:
                raise AssertionError()

            return _which, _currKey  # python functions-in-functions can read their parent function's variables, but not write them ;-;   (so this is a general workaround :P )

        for i in range(len(source)):
            c = source[i]

            # print("DEBUGPARSER) "+repr(i)+" : "+repr(c)+"   which="+repr(which)+", where="+repr(where)+", currKey="+repr(currKey));

            if where == _BeforeString:
                if c == "\"":
                    if which == _LineEnd:
                        raise Exception("Syntax error!: more than two strings on one line!  o,0")
                    start = i + 1  # skip the quote ;3
                    where = _InQuotedString
                elif c.isspace() and c != "\n" and c != "\n":
                    continue
                elif c == "#":
                    if which == _Value:
                        raise Exception(
                            "Syntax error!: Comment started between key and value! (which would gobble up any value!)  D:")
                    where = _InComment
                elif c == "\n" or c == "\r":
                    if which == _Key:
                        continue  # empty line :3
                    elif which == _Value:
                        raise Exception("Syntax error?: Line break between key and value! D:")
                    elif which == _LineEnd:
                        which = _Key
                        continue  # properly full line :3
                    else:
                        raise AssertionError()
                else:
                    if which == _LineEnd:
                        raise Exception("Syntax error!: more than two strings on one line!  o,0")
                    start = i  # don't skip the first char here! it's not a quote, it's actually part of the string! XD
                    where = _InNonquotedString

            elif where == _InComment:
                if c == "\r" or c == "\n":
                    where = _BeforeString

                    if which == _Key:
                        continue  # just-comment line :3
                    elif which == _Value:
                        raise AssertionError()  # it should have triggered a syntax error before this! :[
                    elif which == _LineEnd:
                        # properly full line with comment after it :3
                        which = _Key
                        continue
                    else:
                        raise AssertionError()
                else:
                    continue

            elif where == _InNonquotedString:
                if c.isspace() and c != "\n" and c != "\n":
                    # end of nonquoted string! ^w^
                    if start == None: raise AssertionError();
                    if which != _Key and which != _Value: raise AssertionError();
                    which, currKey = consumestr(source[start:i],
                                                False)  # do NOT include the last char, it's the space delimiter!  (don't forget that XD' )
                    start = None  # for bugchecking ^,^
                    where = _BeforeString

                elif c == "\n" or c == "\r":
                    # end of nonquoted string AND line! ^^?
                    if which == _Key:
                        raise Exception("Syntax error?: Line break between key and value!  D:")
                    elif which == _Value:
                        # normal full line with nonquoted value :>
                        which, currKey = consumestr(source[start:i],
                                                    False)  # DON'T include the last char--the newline! XD'
                        start = None  # for bugchecking ^,^
                        which = _Key  # jump straight to start state for next line! ^w^
                        where = _BeforeString
                    elif which == _LineEnd:
                        raise AssertionError()
                    else:
                        raise AssertionError()
                elif c == "#":
                    if which == _Value:
                        raise Exception(
                            "Syntax error!: Comment started between key and value! (which would gobble up any value!)  D:")
                    where = _InComment
                else:
                    continue  # :3

            elif where == _InQuotedString:
                if c == "\"":
                    # end of yesquoted string! ^w^
                    if start == None: raise AssertionError();
                    if which != _Key and which != _Value: raise AssertionError();
                    which, currKey = consumestr(source[start:i], True)  # DON'T include the last char, it is a quote!
                    start = None  # for bugchecking ^,^
                    where = _BeforeString
                elif c == "\\":
                    where = _InQuotedString_InEscape  # :3
                elif c == "\n" or c == "\r":
                    # engine behavior is to act like a proper closing quote was there :>

                    # end of yesquoted string! ^w^
                    if start == None: raise AssertionError();
                    if which != _Key and which != _Value: raise AssertionError();
                    which, currKey = consumestr(source[start:i], True)  # DON'T include the last char--the newline! XD'
                    start = None  # for bugchecking ^,^
                    where = _BeforeString
                else:
                    continue  # :3

            elif where == _InQuotedString_InEscape:
                if c == "\n" or c == "\r":
                    # engine behavior is to act like it wasn't there, and also that a proper closing quote was there :>

                    # end of yesquoted string! ^w^
                    if start == None: raise AssertionError();
                    if which != _Key and which != _Value: raise AssertionError();
                    which, currKey = consumestr(source[start:i],
                                                True)  # DON'T include the last char, it is that bad trailing backslash!
                    start = None  # for bugchecking ^,^
                    where = _BeforeString

                else:
                    # Note: we descape in a separate step rather than on-the-fly for simplicity+speeds ^_^   (rather than build up an eagerly descaped string char by char, which is slow if no escapes :p, and rather than a hybrid of the two approaches..which is complicated (and this is already complicated enough!) XD' )
                    where = _InQuotedString

            else:
                raise AssertionError()
        #

        # EOF inside quoted string is fine with lc2e (string is consumed just like end-of-line :> )
        # EOF on escape inside quoted string makes the escape ignored, and the string consumed by lc2e
        # EOF on nonquoted string is fine with lc2e :>
        # EOF on comment is fine; no effect different than linebreak :>

        if where == _BeforeString:
            # Normal EOF; no problems! ^w^
            pass;
        elif where == _InComment:
            pass;
        elif where == _InNonquotedString:
            # end of nonquoted string! ^w^
            if start == None: raise AssertionError();
            if which != _Key and which != _Value: raise AssertionError();
            consumestr(source[start:len(source)],
                       False)  # do include the last char like normal, since it's a nonquoted! ^w^
        elif where == _InQuotedString:
            if start == None: raise AssertionError();
            if which != _Key and which != _Value: raise AssertionError();
            consumestr(source[start:len(source)], True)  # DO include the last char, it is a broken quoted string! XD'
        elif where == _InQuotedString_InEscape:
            if start == None: raise AssertionError();
            if which != _Key and which != _Value: raise AssertionError();
            consumestr(source[start:len(source) - 1],
                       True)  # DON'T include the last char--the (imo erroneous :P) trailing backslash!
        else:
            raise AssertionError()

        return configDict

    except AssertionError as exc:
        exc.message = "Pleases to let the puppy of codes know about this! (puppyofcodez@gmail.com)  I'll fix it right away ;_;  (just be sures to send the *exact* input config file source text!: " + repr(
            source) + " )   MANY SORRIES T_T"
        raise


#


def serializeCreaturesConfig(configDict):
    # Serializing is almost *always* easier than parsing XD    (probably largely because there are so many more possible states you can start with in parsing, and that much more situations to have to handle!   but I think there's more to it than that -,-   (wonderful things to explore!! 8> )  )

    def containsspecials(s):
        if len(s) == 0:
            return True  # should be quoted if this somehow is used! XD'?

        if (
                "\"" in s or "#" in s or "\\" in s or " " in s or "\n" in s or "\r" in s or "\t" in s):  # prolly fasters than doing it in the loop!
            return True

        # check other whitespace just to make sures :>
        for c in s:
            if c.isspace():
                return True

        return False

    def escapestr(s):
        s = s.replace("\\", "\\\\")
        s = s.replace("\"", "\\\"")
        s = s.replace("\n", "\\n")
        s = s.replace("\r", "\\r")
        s = s.replace("\t", "\\t")
        return s

    def serstr(s):
        if containsspecials(s):
            return "\"" + escapestr(s) + "\""
        else:
            return s

    serializedForm = ""

    for key in sorted(configDict.keys()):
        value = configDict.get(key)
        if value != None:  # not-present OR actually-None!  ..don't forget that :>' XD'
            serializedForm += serstr(key)
            serializedForm += " "
            serializedForm += serstr(value)
            serializedForm += "\n"

    return serializedForm