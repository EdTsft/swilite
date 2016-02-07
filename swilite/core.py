# -*- coding: utf-8 -*-


# pyswip -- Python SWI-Prolog bridge
# Original Copyright (c) 2007-2012 Yüce Tekol
# Modifications Copyright (c) 2015 Eric Langlois
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import os
import re
import sys
import glob
import atexit
from subprocess import Popen, PIPE
from ctypes import (
    CDLL,
    CFUNCTYPE,
    POINTER,
    Structure,
    Union,
    c_char,
    c_char_p,
    c_double,
    c_int,
    c_int64,
    c_long,
    c_size_t,
    c_uint,
    c_void_p,
    c_wchar,
    c_wchar_p,
)
from ctypes.util import find_library


# To initialize the SWI-Prolog environment, two things need to be done: the
# first is to find where the SO/DLL is located and the second is to find the
# SWI-Prolog home, to get the saved state.
#
# The goal of the (entangled) process below is to make the library installation
# independent.


def _findSwiplPathFromFindLib():
    """
    This function resorts to ctype's find_library to find the path to the
    DLL. The biggest problem is that find_library does not give the path to the
    resource file.

    :returns:
        A path to the swipl SO/DLL or None if it is not found.

    :returns type:
        {str, None}
    """

    path = (find_library('swipl') or
            find_library('pl') or
            find_library('libswipl'))  # This last one is for Windows
    return path


def _findSwiplFromExec():
    """
    This function tries to use an executable on the path to find SWI-Prolog
    SO/DLL and the resource file.

    :returns:
        A tuple of (path to the swipl DLL, path to the resource file)

    :returns type:
        ({str, None}, {str, None})
    """

    platform = sys.platform[:3]

    fullName = None
    swiHome = None

    try:  # try to get library path from swipl executable.

        # We may have pl or swipl as the executable
        try:
            cmd = Popen(['swipl', '-dump-runtime-variables'], stdout=PIPE)
        except OSError:
            cmd = Popen(['pl', '-dump-runtime-variables'], stdout=PIPE)
        ret = cmd.communicate()

        # Parse the output into a dictionary
        ret = ret[0].decode().replace(';', '').splitlines()
        ret = [line.split('=', 1) for line in ret]
        # [1:-1] gets rid of the quotes
        rtvars = dict((name, value[1:-1]) for name, value in ret)

        if rtvars['PLSHARED'] == 'no':
            raise ImportError('SWI-Prolog is not installed as a shared '
                              'library.')
        else:  # PLSHARED == 'yes'
            swiHome = rtvars['PLBASE']   # The environment is in PLBASE
            if not os.path.exists(swiHome):
                swiHome = None

            # determine platform specific path
            if platform == "win":
                dllName = rtvars['PLLIB'][:-4] + '.' + rtvars['PLSOEXT']
                path = os.path.join(rtvars['PLBASE'], 'bin')
                fullName = os.path.join(path, dllName)

                if not os.path.exists(fullName):
                    fullName = None

            elif platform == "cyg":
                # e.g. /usr/lib/pl-5.6.36/bin/i686-cygwin/cygpl.dll

                dllName = 'cygpl.dll'
                path = os.path.join(rtvars['PLBASE'], 'bin', rtvars['PLARCH'])
                fullName = os.path.join(path, dllName)

                if not os.path.exists(fullName):
                    fullName = None

            elif platform == "dar":
                dllName = 'lib' + rtvars['PLLIB'][2:] + '.' + rtvars['PLSOEXT']
                path = os.path.join(rtvars['PLBASE'], 'lib', rtvars['PLARCH'])
                baseName = os.path.join(path, dllName)

                if os.path.exists(baseName):
                    fullName = baseName
                else:  # We will search for versions
                    fullName = None

            else:  # assume UNIX-like
                # The SO name in some linuxes is of the form libswipl.so.5.10.2,
                # so we have to use glob to find the correct one
                dllName = 'lib' + rtvars['PLLIB'][2:] + '.' + rtvars['PLSOEXT']
                path = os.path.join(rtvars['PLBASE'], 'lib', rtvars['PLARCH'])
                baseName = os.path.join(path, dllName)

                if os.path.exists(baseName):
                    fullName = baseName
                else:  # We will search for versions
                    pattern = baseName + '.*'
                    files = glob.glob(pattern)
                    if len(files) == 0:
                        fullName = None
                    elif len(files) == 1:
                        fullName = files[0]
                    else:  # Will this ever happen?
                        fullName = None

    except (OSError, KeyError):  # KeyError from accessing rtvars
        pass

    return (fullName, swiHome)


def _findSwiplWin():
    """
    This function uses several heuristics to gues where SWI-Prolog is installed
    in Windows. It always returns None as the path of the resource file because,
    in Windows, the way to find it is more robust so the SWI-Prolog DLL is
    always able to find it.

    :returns:
        A tuple of (path to the swipl DLL, path to the resource file)

    :returns type:
        ({str, None}, {str, None})
    """

    dllNames = ('swipl.dll', 'libswipl.dll')

    # First try: check the usual installation path (this is faster but
    # hardcoded)
    programFiles = os.getenv('ProgramFiles')
    paths = [os.path.join(programFiles, r'pl\bin', dllName)
             for dllName in dllNames]
    for path in paths:
        if os.path.exists(path):
            return (path, None)

    # Second try: use the find_library
    path = _findSwiplPathFromFindLib()
    if path is not None and os.path.exists(path):
        return (path, None)

    # Third try: use reg.exe to find the installation path in the registry
    # (reg should be installed in all Windows XPs)
    try:
        cmd = Popen(['reg', 'query',
                     r'HKEY_LOCAL_MACHINE\Software\SWI\Prolog',
                     '/v', 'home'], stdout=PIPE)
        ret = cmd.communicate()

        # Result is like:
        # ! REG.EXE VERSION 3.0
        #
        # HKEY_LOCAL_MACHINE\Software\SWI\Prolog
        #    home        REG_SZ  C:\Program Files\pl
        # (Note: spaces may be \t or spaces in the output)
        ret = ret[0].splitlines()
        ret = [line for line in ret if len(line) > 0]
        pattern = re.compile('[^h]*home[^R]*REG_SZ( |\t)*(.*)$')
        match = pattern.match(ret[-1])
        if match is not None:
            path = match.group(2)

            paths = [os.path.join(path, 'bin', dllName)
                     for dllName in dllNames]
            for path in paths:
                if os.path.exists(path):
                    return (path, None)

    except OSError:
        # reg.exe not found? Weird...
        pass

    # May the exec is on path?
    (path, swiHome) = _findSwiplFromExec()
    if path is not None:
        return (path, swiHome)

    # Last try: maybe it is in the current dir
    for dllName in dllNames:
        if os.path.exists(dllName):
            return (dllName, None)

    return (None, None)


def _findSwiplLin():
    """
    This function uses several heuristics to guess where SWI-Prolog is
    installed in Linuxes.

    :returns:
        A tuple of (path to the swipl so, path to the resource file)

    :returns type:
        ({str, None}, {str, None})
    """

    # Maybe the exec is on path?
    (path, swiHome) = _findSwiplFromExec()
    if path is not None:
        return (path, swiHome)

    # If it is not, use  find_library
    path = _findSwiplPathFromFindLib()
    if path is not None:
        return (path, swiHome)

    # Our last try: some hardcoded paths.
    paths = ['/lib', '/usr/lib', '/usr/local/lib', '.', './lib']
    names = ['libswipl.so', 'libpl.so']

    path = None
    for name in names:
        for try_ in paths:
            try_ = os.path.join(try_, name)
            if os.path.exists(try_):
                path = try_
                break

    if path is not None:
        return (path, swiHome)

    return (None, None)


def _findSwiplDar():
    """
    This function uses several heuristics to guess where SWI-Prolog is
    installed in MacOS.

    :returns:
        A tuple of (path to the swipl so, path to the resource file)

    :returns type:
        ({str, None}, {str, None})
    """

    # If the exec is in path
    (path, swiHome) = _findSwiplFromExec()
    if path is not None:
        return (path, swiHome)

    # If it is not, use  find_library
    path = _findSwiplPathFromFindLib()
    if path is not None:
        return (path, swiHome)

    # Last guess, searching for the file
    paths = ['.', './lib', '/usr/lib/', '/usr/local/lib', '/opt/local/lib']
    names = ['libswipl.dylib', 'libpl.dylib']

    for name in names:
        for path in paths:
            path = os.path.join(path, name)
            if os.path.exists(path):
                return (path, None)

    return (None, None)


def _findSwipl():
    """
    This function makes a big effort to find the path to the SWI-Prolog shared
    library. Since this is both OS dependent and installation dependent, we may
    not aways succeed. If we do, we return a name/path that can be used by
    CDLL(). Otherwise we raise an exception.

    :return: Tuple. Fist element is the name or path to the library that can be
             used by CDLL. Second element is the path were SWI-Prolog resource
             file may be found (this is needed in some Linuxes)
    :rtype: Tuple of strings
    :raises ImportError: If we cannot guess the name of the library
    """

    # Now begins the guesswork
    platform = sys.platform[:3]
    if platform == "win":
        # In Windows, we have the default installer path and the registry to
        # look
        (path, swiHome) = _findSwiplWin()

    elif platform in ("lin", "cyg"):
        (path, swiHome) = _findSwiplLin()

    elif platform == "dar":  # Help with MacOS is welcome!!
        (path, swiHome) = _findSwiplDar()

    else:
        raise EnvironmentError('The platform %s is not supported by this '
                               'library. If you want it to be supported, '
                               'please open an issue.' % platform)

    # This is a catch all raise
    if path is None:
        raise ImportError('Could not find the SWI-Prolog library in this '
                          'platform. If you are sure it is installed, please '
                          'open an issue.')
    else:
        return (path, swiHome)


def _fixWindowsPath(dll):
    """
    When the path to the DLL is not in Windows search path, Windows will not be
    able to find other DLLs on the same directory, so we have to add it to the
    path. This function takes care of it.

    :parameters:
      -  `dll` (str) - File name of the DLL
    """

    if sys.platform[:3] != 'win':
        return  # Nothing to do here

    pathToDll = os.path.dirname(dll)
    currentWindowsPath = os.getenv('PATH')

    if pathToDll not in currentWindowsPath:
        # We will prepend the path, to avoid conflicts between DLLs
        newPath = pathToDll + ';' + currentWindowsPath
        os.putenv('PATH', newPath)

_stringMap = {}


def str_to_bytes(string):
    """
    Turns a string into a bytes if necessary (i.e. if it is not already a bytes
    object or None).
    If string is None, int or c_char_p it will be returned directly.

    :param string: The string that shall be transformed
    :type string: str, bytes or type(None)
    :return: Transformed string
    :rtype: c_char_p compatible object (bytes, c_char_p, int or None)
    """
    if string is None or isinstance(string, (int, c_char_p)):
        return string

    if not isinstance(string, bytes):
        if string not in _stringMap:
            _stringMap[string] = string.encode()
        string = _stringMap[string]

    return string


def list_to_bytes_list(strList):
    """
    This function turns an array of strings into a pointer array
    with pointers pointing to the encodings of those strings
    Possibly contained bytes are kept as they are.

    :param strList: List of strings that shall be converted
    :type strList: List of strings
    :returns: Pointer array with pointers pointing to bytes
    :raises: TypeError if strList is not list, set or tuple
    """
    pList = c_char_p * len(strList)

    # if strList is already a pointerarray or None, there is nothing to do
    if isinstance(strList, (pList, type(None))):
        return strList

    if not isinstance(strList, (list, set, tuple)):
        raise TypeError("strList must be list, set or tuple, not " +
                        str(type(strList)))

    pList = pList()
    for i, elem in enumerate(strList):
        pList[i] = str_to_bytes(elem)
    return pList


# Find the path and resource file. SWI_HOME_DIR shall be treated as a constant
# by users of this module
(_path, SWI_HOME_DIR) = _findSwipl()
_fixWindowsPath(_path)


# Load the library
_lib = CDLL(_path)

# PySWIP constants
PYSWIP_MAXSTR = 1024
c_int_p = c_void_p
c_long_p = c_void_p
c_double_p = c_void_p
c_uint_p = c_void_p

#                  /*******************************
#                  *      TERM-TYPE CONSTANTS        *
#                  *******************************/
#                                         /* PL_unify_term() arguments */
# define PL_VARIABLE      (1)             /* nothing */
PL_VARIABLE = 1
# define PL_ATOM          (2)             /* const char * */
PL_ATOM = 2
# define PL_INTEGER       (3)             /* int */
PL_INTEGER = 3
# define PL_FLOAT         (4)             /* double */
PL_FLOAT = 4
# define PL_STRING        (5)             /* const char * */
PL_STRING = 5
# define PL_TERM          (6)
PL_TERM = 6

# define PL_NIL           (7)             /* The constant [] */
PL_NIL = 7
# define PL_BLOB          (8)             /* non-atom blob */
PL_BLOB = 8
# define PL_LIST_PAIR     (9)             /* [_|_] term */
PL_LIST_PAIR = 9

#                                         /* PL_unify_term() */
# define PL_FUNCTOR       (10)            /* functor_t, arg ... */
PL_FUNCTOR = 10
# define PL_LIST          (11)            /* length, arg ... */
PL_LIST = 11
# define PL_CHARS         (12)            /* const char * */
PL_CHARS = 12
# define PL_POINTER       (13)            /* void * */
PL_POINTER = 13
#                                         /* PlArg::PlArg(text, type) */
# define PL_CODE_LIST     (14)            /* [ascii...] */
PL_CODE_LIST = 14
# define PL_CHAR_LIST     (15)            /* [h,e,l,l,o] */
PL_CHAR_LIST = 15
# define PL_BOOL          (16)            /* PL_set_prolog_flag() */
PL_BOOL = 16
# define PL_FUNCTOR_CHARS (17)            /* PL_unify_term() */
PL_FUNCTOR_CHARS = 17
# define _PL_PREDICATE_INDICATOR (18)     /* predicate_t (Procedure) */
_PL_PREDICATE_INDICATOR = 18
# define PL_SHORT         (19)            /* short */
PL_SHORT = 19
# define PL_INT           (20)            /* int */
PL_INT = 20
# define PL_LONG          (21)            /* long */
PL_LONG = 21
# define PL_DOUBLE        (22)            /* double */
PL_DOUBLE = 22
# define PL_NCHARS        (23)            /* size_t, const char * */
PL_NCHARS = 23
# define PL_UTF8_CHARS    (24)            /* const char * */
PL_UTF8_CHARS = 24
# define PL_UTF8_STRING   (25)            /* const char * */
PL_UTF8_STRING = 25
# define PL_INT64         (26)            /* int64_t */
PL_INT64 = 26
# define PL_NUTF8_CHARS   (27)            /* size_t, const char * */
PL_NUTF8_CHARS = 27
# define PL_NUTF8_CODES   (29)            /* size_t, const char * */
PL_NUTF8_CODES = 29
# define PL_NUTF8_STRING  (30)            /* size_t, const char * */
PL_NUTF8_STRING = 30
# define PL_NWCHARS       (31)            /* size_t, const wchar_t * */
PL_NWCHARS = 31
# define PL_NWCODES       (32)            /* size_t, const wchar_t * */
PL_NWCODES = 32
# define PL_NWSTRING      (33)            /* size_t, const wchar_t * */
PL_NWSTRING = 33
# define PL_MBCHARS       (34)            /* const char * */
PL_MBCHARS = 34
# define PL_MBCODES       (35)            /* const char * */
PL_MBCODES = 35
# define PL_MBSTRING      (36)            /* const char * */
PL_MBSTRING = 36
# define PL_INTPTR        (37)            /* intptr_t */
PL_INTPTR = 37
# define PL_CHAR          (38)            /* int */
PL_CHAR = 38
# define PL_CODE          (39)            /* int */
PL_CODE = 39
# define PL_BYTE          (40)            /* int */
PL_BYTE = 40
#                                         /* PL_skip_list() */
# define PL_PARTIAL_LIST  (41)            /* a partial list */
PL_PARTIAL_LIST = 41
# define PL_CYCLIC_TERM   (42)            /* a cyclic list/term */
PL_CYCLIC_TERM = 42
# define PL_NOT_A_LIST    (43)            /* Object is not a list */
PL_NOT_A_LIST = 43
#                                         /* dicts */
# define PL_DICT          (44)
PL_DICT = 44

#       /********************************
#       * NON-DETERMINISTIC CALL/RETURN *
#       *********************************/
#
#  Note 1: Non-deterministic foreign functions may also use the deterministic
#    return methods PL_succeed and PL_fail.
#
#  Note 2: The argument to PL_retry is a 30 bits signed integer (long).

PL_FIRST_CALL = 0
PL_CUTTED = 1
PL_PRUNED = 1
PL_REDO = 2

PL_FA_NOTRACE = 0x01  # foreign cannot be traced
PL_FA_TRANSPARENT = 0x02  # foreign is module transparent
PL_FA_NONDETERMINISTIC = 0x04  # foreign is non-deterministic
PL_FA_VARARGS = 0x08  # call using t0, ac, ctx
PL_FA_CREF = 0x10  # Internal: has clause-reference */


#        /*******************************
#        *         BLOBS        *
#        *******************************/

# define PL_BLOB_MAGIC_B 0x75293a00  /* Magic to validate a blob-type */
# define PL_BLOB_VERSION 1       /* Current version */
# define PL_BLOB_MAGIC   (PL_BLOB_MAGIC_B|PL_BLOB_VERSION)

# define PL_BLOB_UNIQUE  0x01        /* Blob content is unique */
# define PL_BLOB_TEXT    0x02        /* blob contains text */
# define PL_BLOB_NOCOPY  0x04        /* do not copy the data */
# define PL_BLOB_WCHAR   0x08        /* wide character string */

#        /*******************************
#        *      CHAR BUFFERS    *
#        *******************************/

CVT_ATOM = 0x0001
CVT_STRING = 0x0002
CVT_LIST = 0x0004
CVT_INTEGER = 0x0008
CVT_FLOAT = 0x0010
CVT_VARIABLE = 0x0020
CVT_NUMBER = CVT_INTEGER | CVT_FLOAT
CVT_ATOMIC = CVT_NUMBER | CVT_ATOM | CVT_STRING
CVT_WRITE = 0x0040  # as of version 3.2.10
CVT_ALL = CVT_ATOMIC | CVT_LIST
CVT_MASK = 0x00ff

BUF_DISCARDABLE = 0x0000
BUF_RING = 0x0100
BUF_MALLOC = 0x0200

CVT_EXCEPTION = 0x10000  # throw exception on error
CVT_VVARNOFAIL = 0x20000

REP_ISO_LATIN_1 = 0x0000
REP_UTF8 = 0x1000
REP_MB = 0x2000

argv = list_to_bytes_list(sys.argv + [None])
argc = len(sys.argv)

intptr_t = c_long
ssize_t = intptr_t
wint_t = c_uint

#                  /*******************************
#                  *             TYPES            *
#                  *******************************/
#
# typedef uintptr_t       atom_t;         /* Prolog atom */
# typedef uintptr_t       functor_t;      /* Name/arity pair */
# typedef void *          module_t;       /* Prolog module */
# typedef void *          predicate_t;    /* Prolog procedure */
# typedef void *          record_t;       /* Prolog recorded term */
# typedef uintptr_t       term_t;         /* opaque term handle */
# typedef uintptr_t       qid_t;          /* opaque query handle */
# typedef uintptr_t       PL_fid_t;       /* opaque foreign context handle */
# typedef void *          control_t;      /* non-deterministic control arg */
# typedef void *          PL_engine_t;    /* opaque engine handle */
# typedef uintptr_t       PL_atomic_t;    /* same a word */
# typedef uintptr_t       foreign_t;      /* return type of foreign functions */
# typedef wchar_t         pl_wchar_t;     /* Prolog wide character */
# typedef foreign_t       (*pl_function_t)(); /* foreign language functions */

atom_t = c_uint_p
functor_t = c_uint_p
module_t = c_void_p
predicate_t = c_void_p
record_t = c_void_p
term_t = c_uint_p
qid_t = c_uint_p
PL_fid_t = c_uint_p
fid_t = c_uint_p
control_t = c_void_p
PL_engine_t = c_void_p
PL_atomic_t = c_uint_p
foreign_t = c_uint_p
pl_wchar_t = c_wchar

#                 /********************************
#                 *      REGISTERING FOREIGNS     *
#                 *********************************/
# PL_EXPORT(int)        PL_register_foreign(const char *name, int arity,
#                                           pl_function_t func,
#                                           int flags, ...);
PL_register_foreign = _lib.PL_register_foreign
PL_register_foreign.restype = c_int

#                /********************************
#                *            MODULES            *
#                *********************************/
#
# PL_EXPORT(module_t)   PL_context(void);
PL_context = _lib.PL_context
PL_context.argtypes = []
PL_context.restype = module_t

# PL_EXPORT(atom_t)     PL_module_name(module_t module);
PL_module_name = _lib.PL_module_name
PL_module_name.argtypes = [module_t]
PL_module_name.restype = atom_t

# PL_EXPORT(module_t)   PL_new_module(atom_t name);
PL_new_module = _lib.PL_new_module
PL_new_module.argtypes = [atom_t]
PL_new_module.restype = module_t

# PL_EXPORT(int)        PL_strip_module(term_t in, module_t *m, term_t out);
PL_strip_module = _lib.PL_strip_module
PL_strip_module.argtypes = [term_t, POINTER(module_t), term_t]
PL_strip_module.restype = c_int


#                /*******************************
#                *           CALL-BACK          *
#                *******************************/

PL_Q_DEBUG = 0x01  # = TRUE for backward compatibility
PL_Q_NORMAL = 0x02  # normal usage
PL_Q_NODEBUG = 0x04  # use this one
PL_Q_CATCH_EXCEPTION = 0x08  # handle exceptions in C
PL_Q_PASS_EXCEPTION = 0x10  # pass to parent environment
PL_Q_DETERMINISTIC = 0x20  # call was deterministic

#                         /* Foreign context frames */
# PL_EXPORT(fid_t)         PL_open_foreign_frame(void);
PL_open_foreign_frame = _lib.PL_open_foreign_frame
PL_open_foreign_frame.argtypes = []
PL_open_foreign_frame.restype = fid_t

# PL_EXPORT(void)          PL_rewind_foreign_frame(fid_t cid);
PL_rewind_foreign_frame = _lib.PL_rewind_foreign_frame
PL_rewind_foreign_frame.argtypes = [fid_t]
PL_rewind_foreign_frame.restype = None

# PL_EXPORT(void)          PL_close_foreign_frame(fid_t cid);
PL_close_foreign_frame = _lib.PL_close_foreign_frame
PL_close_foreign_frame.argtypes = [fid_t]
PL_close_foreign_frame.restype = None

# PL_EXPORT(void)          PL_discard_foreign_frame(fid_t cid);
PL_discard_foreign_frame = _lib.PL_discard_foreign_frame
PL_discard_foreign_frame.argtypes = [fid_t]
PL_discard_foreign_frame.restype = None

#                         /* Finding predicates */
# PL_EXPORT(predicate_t)   PL_pred(functor_t f, module_t m);
PL_pred = _lib.PL_pred
PL_pred.argtypes = [functor_t, module_t]
PL_pred.restype = predicate_t

# PL_EXPORT(predicate_t)   PL_predicate(const char *name, int arity,
#                                       const char* module);
PL_predicate = _lib.PL_predicate
PL_predicate.argtypes = [c_char_p, c_int, c_char_p]
PL_predicate.restype = predicate_t

# PL_EXPORT(int)           PL_predicate_info(predicate_t pred,
#                                            atom_t *name, int *arity,
#                                            module_t *module);
PL_predicate_info = _lib.PL_predicate_info
PL_predicate_info.argtypes = [predicate_t, POINTER(atom_t), POINTER(c_int),
                              POINTER(module_t)]
PL_predicate_info.restype = c_int

#                         /* Call-back */
# PL_EXPORT(qid_t)         PL_open_query(module_t m, int flags,
#                                        predicate_t pred, term_t t0);
PL_open_query = _lib.PL_open_query
PL_open_query.argtypes = [module_t, c_int, predicate_t, term_t]
PL_open_query.restype = qid_t

# PL_EXPORT(int)           PL_next_solution(qid_t qid);
PL_next_solution = _lib.PL_next_solution
PL_next_solution.argtypes = [qid_t]
PL_next_solution.restype = c_int

# PL_EXPORT(void)          PL_close_query(qid_t qid);
PL_close_query = _lib.PL_close_query
PL_close_query.argtypes = [qid_t]
PL_close_query.restype = None

# PL_EXPORT(void)          PL_cut_query(qid_t qid);
PL_cut_query = _lib.PL_cut_query
PL_cut_query.argtypes = [qid_t]
PL_cut_query.restype = None

#                         /* Simplified (but less flexible) call-back */
# PL_EXPORT(int)           PL_call(term_t t, module_t m);
PL_call = _lib.PL_call
PL_call.argtypes = [term_t, module_t]
PL_call.restype = c_int

# PL_EXPORT(int)           PL_call_predicate(module_t m, int debug,
#                                            predicate_t pred, term_t t0);
PL_call_predicate = _lib.PL_call_predicate
PL_call_predicate.argtypes = [module_t, c_int, predicate_t, term_t]
PL_call_predicate.restype = c_int

#                         /* Handling exceptions */
# PL_EXPORT(term_t)        PL_exception(qid_t qid);
PL_exception = _lib.PL_exception
PL_exception.argtypes = [qid_t]
PL_exception.restype = term_t

# PL_EXPORT(int)           PL_raise_exception(term_t exception);
PL_raise_exception = _lib.PL_raise_exception
PL_raise_exception.argtypes = [term_t]
PL_raise_exception.restype = c_int

# PL_EXPORT(int)           PL_throw(term_t exception);
PL_throw = _lib.PL_throw
PL_throw.argtypes = [term_t]
PL_throw.restype = c_int

# PL_EXPORT(void)          PL_clear_exception(void);
PL_clear_exception = _lib.PL_clear_exception
PL_clear_exception.argtypes = []
PL_clear_exception.restype = None


#                  /*******************************
#                  *        TERM-REFERENCES        *
#                  *******************************/
#
#                         /* Creating and destroying term-refs */
# PL_EXPORT(term_t)        PL_new_term_refs(int n);
PL_new_term_refs = _lib.PL_new_term_refs
PL_new_term_refs.argtypes = [c_int]
PL_new_term_refs.restype = term_t

# PL_EXPORT(term_t)        PL_new_term_ref(void);
PL_new_term_ref = _lib.PL_new_term_ref
PL_new_term_ref.argtypes = []
PL_new_term_ref.restype = term_t

# PL_EXPORT(term_t)        PL_copy_term_ref(term_t from);
PL_copy_term_ref = _lib.PL_copy_term_ref
PL_copy_term_ref.argtypes = [term_t]
PL_copy_term_ref.restype = term_t

# PL_EXPORT(void)          PL_reset_term_refs(term_t r);
PL_reset_term_refs = _lib.PL_reset_term_refs
PL_reset_term_refs.argtypes = [term_t]
PL_reset_term_refs.restype = None

#                         /* Constants */
# PL_EXPORT(atom_t)        PL_new_atom(const char *s);
PL_new_atom = _lib.PL_new_atom
PL_new_atom.argtypes = [c_char_p]
PL_new_atom.restype = atom_t

# PL_EXPORT(atom_t)        PL_new_atom_nchars(size_t len, const char *s);
PL_new_atom_nchars = _lib.PL_new_atom_nchars
PL_new_atom_nchars.argtypes = [c_size_t, POINTER(c_char)]
PL_new_atom_nchars.restype = atom_t

# PL_EXPORT(atom_t)        PL_new_atom_wchars(size_t len, const pl_wchar_t *s);
PL_new_atom_wchars = _lib.PL_new_atom_wchars
PL_new_atom_wchars.argtypes = [c_size_t, POINTER(pl_wchar_t)]
PL_new_atom_wchars.restype = atom_t

# PL_EXPORT(const char *)  PL_atom_chars(atom_t a);
PL_atom_chars = _lib.PL_atom_chars
PL_atom_chars.argtypes = [atom_t]
PL_atom_chars.restype = c_char_p

# PL_EXPORT(const char *)  PL_atom_nchars(atom_t a, size_t *len);
PL_atom_nchars = _lib.PL_atom_nchars
PL_atom_nchars.argtypes = [atom_t, POINTER(c_size_t)]
PL_atom_nchars.restype = POINTER(c_char)

# PL_EXPORT(const wchar_t *)    PL_atom_wchars(atom_t a, size_t *len);
PL_atom_wchars = _lib.PL_atom_wchars
PL_atom_wchars.argtypes = [atom_t, POINTER(c_size_t)]
PL_atom_wchars.restype = c_wchar_p

# PL_EXPORT(void)          PL_register_atom(atom_t a);
PL_register_atom = _lib.PL_register_atom
PL_register_atom.argtypes = [atom_t]
PL_register_atom.restype = None

# PL_EXPORT(void)          PL_unregister_atom(atom_t a);
PL_unregister_atom = _lib.PL_unregister_atom
PL_unregister_atom.argtypes = [atom_t]
PL_unregister_atom.restype = None

# PL_EXPORT(functor_t)     PL_new_functor(atom_t f, int a);
PL_new_functor = _lib.PL_new_functor
PL_new_functor.argtypes = [atom_t, c_int]
PL_new_functor.restype = functor_t

# PL_EXPORT(atom_t)        PL_functor_name(functor_t f);
PL_functor_name = _lib.PL_functor_name
PL_functor_name.argtypes = [functor_t]
PL_functor_name.restype = atom_t

# PL_EXPORT(int)           PL_functor_arity(functor_t f);
PL_functor_arity = _lib.PL_functor_arity
PL_functor_arity.argtypes = [functor_t]
PL_functor_arity.restype = c_int

#                         /* Get C-values from Prolog terms */
# PL_EXPORT(int)           PL_get_atom(term_t t, atom_t *a);
PL_get_atom = _lib.PL_get_atom
PL_get_atom.argtypes = [term_t, POINTER(atom_t)]
PL_get_atom.restype = c_int

# PL_EXPORT(int)           PL_get_bool(term_t t, int *value);
PL_get_bool = _lib.PL_get_bool
PL_get_bool.argtypes = [term_t, POINTER(c_int)]
PL_get_bool.restype = c_int

# PL_EXPORT(int)           PL_get_atom_chars(term_t t, char **a);
PL_get_atom_chars = _lib.PL_get_atom_chars
PL_get_atom_chars.argtypes = [term_t, POINTER(c_char_p)]
PL_get_atom_chars.restype = c_int

# #define PL_get_string_chars(t, s, l) PL_get_string(t,s,l)
# PL_EXPORT(int)         PL_get_string(term_t t, char **s, size_t *len);
PL_get_string = _lib.PL_get_string
PL_get_string.argtypes = [term_t, POINTER(POINTER(c_char)), POINTER(c_size_t)]
PL_get_string.restype = c_int
PL_get_string_chars = PL_get_string

# PL_EXPORT(int)           PL_get_chars(term_t t, char **s, unsigned int flags);
PL_get_chars = _lib.PL_get_chars
PL_get_chars.argtypes = [term_t, POINTER(c_char_p), c_uint]
PL_get_chars.restype = c_int

# PL_EXPORT(int)           PL_get_list_chars(term_t l, char **s,
#                                            unsigned int flags);
PL_get_list_chars = _lib.PL_get_list_chars
PL_get_list_chars.argtypes = [term_t, POINTER(c_char_p), c_uint]
PL_get_list_chars.restype = c_int

# PL_EXPORT(int)           PL_get_atom_nchars(term_t t, size_t *len, char **a);
PL_get_atom_nchars = _lib.PL_get_atom_nchars
PL_get_atom_nchars.argtypes = [term_t, POINTER(c_size_t),
                               POINTER(POINTER(c_char))]
PL_get_atom_nchars.restype = c_int

# PL_EXPORT(int)           PL_get_list_nchars(term_t l, size_t *len, char **s,
#                                             unsigned int flags);
PL_get_list_nchars = _lib.PL_get_list_nchars
PL_get_list_nchars.argtypes = [term_t, POINTER(c_size_t),
                               POINTER(POINTER(c_char)), c_uint]
PL_get_list_nchars.restype = c_int

# PL_EXPORT(int)           PL_get_nchars(term_t t, size_t *len, char **s,
#                                        unsigned int flags);
PL_get_nchars = _lib.PL_get_nchars
PL_get_nchars.argtypes = [term_t, POINTER(c_size_t), POINTER(POINTER(c_char)),
                          c_uint]
PL_get_nchars.restype = c_int

# PL_EXPORT(int)           PL_get_integer(term_t t, int *i);
PL_get_integer = _lib.PL_get_integer
PL_get_integer.argtypes = [term_t, POINTER(c_int)]
PL_get_integer.restype = c_int

# PL_EXPORT(int)           PL_get_long(term_t t, long *i);
PL_get_long = _lib.PL_get_long
PL_get_long.argtypes = [term_t, POINTER(c_long)]
PL_get_long.restype = c_int

# PL_EXPORT(int)           PL_get_intptr(term_t t, intptr_t *i);
PL_get_intptr = _lib.PL_get_intptr
PL_get_intptr.argtypes = [term_t, POINTER(intptr_t)]
PL_get_intptr.restype = c_int

# PL_EXPORT(int)           PL_get_pointer(term_t t, void **ptr);
PL_get_pointer = _lib.PL_get_pointer
PL_get_pointer.argtypes = [term_t, POINTER(c_void_p)]
PL_get_pointer.restype = c_int

# PL_EXPORT(int)           PL_get_float(term_t t, double *f);
PL_get_float = _lib.PL_get_float
PL_get_float.argtypes = [term_t, c_double_p]
PL_get_float.restype = c_int

# PL_EXPORT(int)           PL_get_functor(term_t t, functor_t *f);
PL_get_functor = _lib.PL_get_functor
PL_get_functor.argtypes = [term_t, POINTER(functor_t)]
PL_get_functor.restype = c_int

# PL_EXPORT(int)           PL_get_name_arity(term_t t, atom_t *name,
#                                            int *arity);
PL_get_name_arity = _lib.PL_get_name_arity
PL_get_name_arity.argtypes = [term_t, POINTER(atom_t), POINTER(c_int)]
PL_get_name_arity.restype = c_int

# PL_EXPORT(int)           PL_get_compound_name_arity(term_t t, atom_t *name,
#                                                     int *arity);
PL_get_compound_name_arity = _lib.PL_get_compound_name_arity
PL_get_compound_name_arity.argtypes = [term_t, POINTER(atom_t), c_int_p]
PL_get_compound_name_arity.restype = c_int

# PL_EXPORT(int)           PL_get_module(term_t t, module_t *module);
PL_get_module = _lib.PL_get_module
PL_get_module.argtypes = [term_t, POINTER(module_t)]
PL_get_module.restype = c_int

# PL_EXPORT(int)           PL_get_arg(int index, term_t t, term_t a);
PL_get_arg = _lib.PL_get_arg
PL_get_arg.argtypes = [c_int, term_t, term_t]
PL_get_arg.restype = c_int

# PL_EXPORT(int)           PL_get_list(term_t l, term_t h, term_t t);
PL_get_list = _lib.PL_get_list
PL_get_list.argtypes = [term_t, term_t, term_t]
PL_get_list.restype = c_int

# PL_EXPORT(int)           PL_get_head(term_t l, term_t h);
PL_get_head = _lib.PL_get_head
PL_get_head.argtypes = [term_t, term_t]
PL_get_head.restype = c_int

# PL_EXPORT(int)           PL_get_tail(term_t l, term_t t);
PL_get_tail = _lib.PL_get_tail
PL_get_tail.argtypes = [term_t, term_t]
PL_get_tail.restype = c_int

# PL_EXPORT(int)           PL_get_nil(term_t l);
PL_get_nil = _lib.PL_get_nil
PL_get_nil.argtypes = [term_t]
PL_get_nil.restype = c_int

# PL_EXPORT(int)           PL_get_term_value(term_t t, term_value_t *v);
# PL_get_term_value = _lib.PL_get_term_value
# PL_get_term_value.argtypes = [term_t, POINTER(term_value_t)]
# PL_get_term_value.restype = c_int

# PL_EXPORT(char *)        PL_quote(int chr, const char *data);
PL_quote = _lib.PL_quote
PL_quote.argtypes = [c_int, c_char_p]
PL_quote_restype = c_char_p

#                         /* Verify types */
# PL_EXPORT(int)                PL_term_type(term_t t);
PL_term_type = _lib.PL_term_type
PL_term_type.argtypes = [term_t]
PL_term_type.restype = c_int

# PL_EXPORT(int)                PL_is_variable(term_t t);
PL_is_variable = _lib.PL_is_variable
PL_is_variable.argtypes = [term_t]
PL_is_variable.restype = c_int

# PL_EXPORT(int)                PL_is_ground(term_t t);
PL_is_ground = _lib.PL_is_ground
PL_is_ground.argtypes = [term_t]
PL_is_ground.restype = c_int

# PL_EXPORT(int)                PL_is_atom(term_t t);
PL_is_atom = _lib.PL_is_atom
PL_is_atom.argtypes = [term_t]
PL_is_atom.restype = c_int

# PL_EXPORT(int)                PL_is_integer(term_t t);
PL_is_integer = _lib.PL_is_integer
PL_is_integer.argtypes = [term_t]
PL_is_integer.restype = c_int

# PL_EXPORT(int)                PL_is_string(term_t t);
PL_is_string = _lib.PL_is_string
PL_is_string.argtypes = [term_t]
PL_is_string.restype = c_int

# PL_EXPORT(int)                PL_is_float(term_t t);
PL_is_float = _lib.PL_is_float
PL_is_float.argtypes = [term_t]
PL_is_float.restype = c_int

# PL_EXPORT(int)                PL_is_rational(term_t t);
PL_is_rational = _lib.PL_is_rational
PL_is_rational.argtypes = [term_t]
PL_is_rational.restype = c_int

# PL_EXPORT(int)                PL_is_compound(term_t t);
PL_is_compound = _lib.PL_is_compound
PL_is_compound.argtypes = [term_t]
PL_is_compound.restype = c_int

# PL_EXPORT(int)                PL_is_callable(term_t t);
PL_is_callable = _lib.PL_is_callable
PL_is_callable.argtypes = [term_t]
PL_is_callable.restype = c_int

# PL_EXPORT(int)                PL_is_functor(term_t t, functor_t f);
PL_is_functor = _lib.PL_is_functor
PL_is_functor.argtypes = [term_t, functor_t]
PL_is_functor.restype = c_int

# PL_EXPORT(int)                PL_is_list(term_t t);
PL_is_list = _lib.PL_is_list
PL_is_list.argtypes = [term_t]
PL_is_list.restype = c_int

# PL_EXPORT(int)                PL_is_pair(term_t t);
PL_is_pair = _lib.PL_is_pair
PL_is_pair.argtypes = [term_t]
PL_is_pair.restype = c_int

# PL_EXPORT(int)                PL_is_atomic(term_t t);
PL_is_atomic = _lib.PL_is_atomic
PL_is_atomic.argtypes = [term_t]
PL_is_atomic.restype = c_int

# PL_EXPORT(int)                PL_is_number(term_t t);
PL_is_number = _lib.PL_is_number
PL_is_number.argtypes = [term_t]
PL_is_number.restype = c_int

# PL_EXPORT(int)                PL_is_acyclic(term_t t);
PL_is_acyclic = _lib.PL_is_acyclic
PL_is_acyclic.argtypes = [term_t]
PL_is_acyclic.restype = c_int

#                         /* Assign to term-references */
# PL_EXPORT(int)                PL_put_variable(term_t t);
PL_put_variable = _lib.PL_put_variable
PL_put_variable.argtypes = [term_t]
PL_put_variable.restype = c_int

# PL_EXPORT(int)                PL_put_atom(term_t t, atom_t a);
PL_put_atom = _lib.PL_put_atom
PL_put_atom.argtypes = [term_t, atom_t]
PL_put_atom.restype = c_int

# PL_EXPORT(int)                PL_put_bool(term_t t, int val);
PL_put_bool = _lib.PL_put_bool
PL_put_bool.argtypes = [term_t, c_int]
PL_put_bool.restype = c_int

# PL_EXPORT(int)                PL_put_atom_chars(term_t t, const char *chars);
PL_put_atom_chars = _lib.PL_put_atom_chars
PL_put_atom_chars.argtypes = [term_t, c_char_p]
PL_put_atom_chars.restype = c_int

# PL_EXPORT(int)                PL_put_string_chars(term_t t,
#                                                   const char *chars);
PL_put_string_chars = _lib.PL_put_string_chars
PL_put_string_chars.argtypes = [term_t, c_char_p]
PL_put_string_chars.restype = c_int

# PL_EXPORT(int)                PL_put_list_chars(term_t t, const char *chars);
PL_put_list_chars = _lib.PL_put_list_chars
PL_put_list_chars.argtypes = [term_t, c_char_p]
PL_put_list_chars.restype = c_int

# PL_EXPORT(int)                PL_put_list_codes(term_t t, const char *chars);
PL_put_list_codes = _lib.PL_put_list_codes
PL_put_list_codes.argtypes = [term_t, c_char_p]
PL_put_list_codes.restype = c_int

# PL_EXPORT(int)                PL_put_atom_nchars(term_t t, size_t l,
#                                                  const char *chars);
PL_put_atom_nchars = _lib.PL_put_atom_nchars
PL_put_atom_nchars.argtypes = [term_t, c_size_t, POINTER(c_char)]
PL_put_atom_nchars.restype = c_int

# PL_EXPORT(int)                PL_put_string_nchars(term_t t, size_t len,
#                                                    const char *chars);
PL_put_string_nchars = _lib.PL_put_string_nchars
PL_put_string_nchars.argtypes = [term_t, c_size_t, POINTER(c_char)]
PL_put_string_nchars.restype = c_int

# PL_EXPORT(int)                PL_put_list_nchars(term_t t, size_t l,
#                                                  const char *chars);
PL_put_list_nchars = _lib.PL_put_list_nchars
PL_put_list_nchars.argtypes = [term_t, c_size_t, POINTER(c_char)]
PL_put_list_nchars.restype = c_int

# PL_EXPORT(int)                PL_put_list_ncodes(term_t t, size_t l,
#                                                  const char *chars);
PL_put_list_ncodes = _lib.PL_put_list_ncodes
PL_put_list_ncodes.argtypes = [term_t, c_size_t, POINTER(c_char)]
PL_put_list_ncodes.restype = c_int

# PL_EXPORT(int)                PL_put_integer(term_t t, long i);
PL_put_integer = _lib.PL_put_integer
PL_put_integer.argtypes = [term_t, c_long]
PL_put_integer.restype = c_int

# PL_EXPORT(int)                PL_put_pointer(term_t t, void *ptr);
PL_put_pointer = _lib.PL_put_pointer
PL_put_pointer.argtypes = [term_t, c_void_p]
PL_put_pointer.restype = c_int

# PL_EXPORT(int)                PL_put_float(term_t t, double f);
PL_put_float = _lib.PL_put_float
PL_put_float.argtypes = [term_t, c_double]
PL_put_float.restype = c_int

# PL_EXPORT(int)                PL_put_functor(term_t t, functor_t functor);
PL_put_functor = _lib.PL_put_functor
PL_put_functor.argtypes = [term_t, functor_t]
PL_put_functor.restype = c_int

# PL_EXPORT(int)                PL_put_list(term_t l);
PL_put_list = _lib.PL_put_list
PL_put_list.argtypes = [term_t]
PL_put_list.restype = c_int

# PL_EXPORT(int)                PL_put_nil(term_t l);
PL_put_nil = _lib.PL_put_nil
PL_put_nil.argtypes = [term_t]
PL_put_nil.restype = c_int

# PL_EXPORT(int)                PL_put_term(term_t t1, term_t t2);
PL_put_term = _lib.PL_put_term
PL_put_term.argtypes = [term_t, term_t]
PL_put_term.restype = c_int

#                         /* construct a functor or list-cell */
# PL_EXPORT(int)                PL_cons_functor(term_t h, functor_t f, ...);
PL_cons_functor = _lib.PL_cons_functor
PL_cons_functor.restype = c_int

# PL_EXPORT(int)                PL_cons_functor_v(term_t h, functor_t fd,
#                                                 term_t a0);
PL_cons_functor_v = _lib.PL_cons_functor_v
PL_cons_functor_v.argtypes = [term_t, functor_t, term_t]
PL_cons_functor_v.restype = c_int

# PL_EXPORT(int)                PL_cons_list(term_t l, term_t h, term_t t);
PL_cons_list = _lib.PL_cons_list
PL_cons_list.argtypes = [term_t, term_t, term_t]
PL_cons_list.restype = c_int

#                         /* Unify term-references */
# PL_EXPORT(int)        PL_unify(term_t t1, term_t t2);
PL_unify = _lib.PL_unify
PL_unify.argtypes = [term_t, term_t]
PL_unify.restype = c_int

# PL_EXPORT(int)        PL_unify_atom(term_t t, atom_t a);
PL_unify_atom = _lib.PL_unify_atom
PL_unify_atom.argtypes = [term_t, atom_t]
PL_unify_atom.restype = c_int

# PL_EXPORT(int)        PL_unify_atom_chars(term_t t, const char *chars);
PL_unify_atom_chars = _lib.PL_unify_atom_chars
PL_unify_atom_chars.argtypes = [term_t, c_char_p]
PL_unify_atom_chars.restype = c_int

# PL_EXPORT(int)        PL_unify_list_chars(term_t t, const char *chars);
PL_unify_list_chars = _lib.PL_unify_list_chars
PL_unify_list_chars.argtypes = [term_t, c_char_p]
PL_unify_list_chars.restype = c_int

# PL_EXPORT(int)        PL_unify_list_codes(term_t t, const char *chars);
PL_unify_list_codes = _lib.PL_unify_list_codes
PL_unify_list_codes.argtypes = [term_t, c_char_p]
PL_unify_list_codes.restype = c_int

# PL_EXPORT(int)        PL_unify_string_chars(term_t t, const char *chars);
PL_unify_string_chars = _lib.PL_unify_string_chars
PL_unify_string_chars.argtypes = [term_t, c_char_p]
PL_unify_string_chars.restype = c_int

# PL_EXPORT(int)        PL_unify_atom_nchars(term_t t, size_t l, const char *s);
PL_unify_atom_nchars = _lib.PL_unify_atom_nchars
PL_unify_atom_nchars.argtypes = [term_t, c_size_t, POINTER(c_char)]
PL_unify_atom_nchars.restype = c_int

# PL_EXPORT(int)        PL_unify_list_ncodes(term_t t, size_t l, const char *s);
PL_unify_list_ncodes = _lib.PL_unify_list_ncodes
PL_unify_list_ncodes.argtypes = [term_t, c_size_t, POINTER(c_char)]
PL_unify_list_ncodes.restype = c_int

# PL_EXPORT(int)        PL_unify_list_nchars(term_t t, size_t l, const char *s);
PL_unify_list_nchars = _lib.PL_unify_list_nchars
PL_unify_list_nchars.argtypes = [term_t, c_size_t, POINTER(c_char)]
PL_unify_list_nchars.restype = c_int

# PL_EXPORT(int)        PL_unify_string_nchars(term_t t, size_t len,
#                                              const char *chars);
PL_unify_string_nchars = _lib.PL_unify_string_nchars
PL_unify_string_nchars.argtypes = [term_t, c_size_t, POINTER(c_char)]
PL_unify_string_nchars.restype = c_int

# PL_EXPORT(int)        PL_unify_bool(term_t t, int n);
PL_unify_bool = _lib.PL_unify_bool
PL_unify_bool.argtypes = [term_t, c_int]
PL_unify_bool.restype = c_int

# PL_EXPORT(int)        PL_unify_integer(term_t t, intptr_t n);
PL_unify_integer = _lib.PL_unify_integer
PL_unify_integer.argtypes = [term_t, intptr_t]
PL_unify_integer.restype = c_int

# PL_EXPORT(int)        PL_unify_float(term_t t, double f);
PL_unify_float = _lib.PL_unify_float
PL_unify_float.argtypes = [term_t, c_double]
PL_unify_float.restype = c_int

# PL_EXPORT(int)        PL_unify_pointer(term_t t, void *ptr);
PL_unify_pointer = _lib.PL_unify_pointer
PL_unify_pointer.argtypes = [term_t, c_void_p]
PL_unify_pointer.restype = c_int

# PL_EXPORT(int)        PL_unify_functor(term_t t, functor_t f);
PL_unify_functor = _lib.PL_unify_functor
PL_unify_functor.argtypes = [term_t, functor_t]
PL_unify_functor.restype = c_int

# PL_EXPORT(int)        PL_unify_compound(term_t t, functor_t f);
PL_unify_compound = _lib.PL_unify_compound
PL_unify_compound.argtypes = [term_t, functor_t]
PL_unify_compound.restype = c_int

# PL_EXPORT(int)        PL_unify_list(term_t l, term_t h, term_t t);
PL_unify_list = _lib.PL_unify_list
PL_unify_list.argtypes = [term_t, term_t, term_t]
PL_unify_list.restype = c_int

# PL_EXPORT(int)        PL_unify_nil(term_t l);
PL_unify_nil = _lib.PL_unify_nil
PL_unify_nil.argtypes = [term_t]
PL_unify_nil.restype = c_int

# PL_EXPORT(int)        PL_unify_arg(int index, term_t t, term_t a);
PL_unify_arg = _lib.PL_unify_arg
PL_unify_arg.argtypes = [c_int, term_t, term_t]
PL_unify_arg.restype = c_int

# PL_EXPORT(int)        PL_unify_term(term_t t, ...);
PL_unify_term = _lib.PL_unify_term
PL_unify_term.restype = c_int

# PL_EXPORT(int)        PL_unify_chars(term_t t, int flags, size_t len,
#                                      const char *s);
PL_unify_chars = _lib.PL_unify_chars
PL_unify_chars.argtypes = [term_t, c_int, c_size_t, POINTER(c_char)]
PL_unify_chars.restype = c_int


#                  /*******************************
#                  *               LISTS                *
#                  *******************************/
#
# PL_EXPORT(int)        PL_skip_list(term_t list, term_t tail, size_t *len);
PL_skip_list = _lib.PL_skip_list
PL_skip_list.argtypes = [term_t, term_t, POINTER(c_size_t)]
PL_skip_list.restype = c_int


#                  /*******************************
#                  *    WIDE CHARACTER VERSIONS        *
#                  *******************************/
#
# PL_EXPORT(int)        PL_unify_wchars(term_t t, int type,
#                                 size_t len, const pl_wchar_t *s);
PL_unify_wchars = _lib.PL_unify_wchars
PL_unify_wchars.argtypes = [term_t, c_int, c_size_t, POINTER(pl_wchar_t)]
PL_unify_wchars.restype = c_int

# PL_EXPORT(int)        PL_unify_wchars_diff(term_t t, term_t tail, int type,
#                                 size_t len, const pl_wchar_t *s);
PL_unify_wchars_diff = _lib.PL_unify_wchars_diff
PL_unify_wchars_diff.argtypes = [term_t, term_t, c_int, c_size_t,
                                 POINTER(pl_wchar_t)]
PL_unify_wchars_diff.restype = c_int

# PL_EXPORT(int)        PL_get_wchars(term_t l,
#                               size_t *length, pl_wchar_t **s,
#                               unsigned flags);
PL_get_wchars = _lib.PL_get_wchars
PL_get_wchars.argtypes = [term_t, POINTER(c_size_t),
                          POINTER(POINTER(pl_wchar_t)), c_uint]
PL_get_wchars.restype = c_int

# PL_EXPORT(size_t)     PL_utf8_strlen(const char *s, size_t len);
PL_utf8_strlen = _lib.PL_utf8_strlen
PL_utf8_strlen.argtypes = [POINTER(c_char), c_size_t]
PL_utf8_strlen.restype = c_size_t


#          /*******************************
#          *           WIDE INTEGERS        *
#          *******************************/
#
#
# PL_EXPORT(int)        PL_get_int64(term_t t, int64_t *i) WUNUSED;
PL_get_int64 = _lib.PL_get_int64
PL_get_int64.argtypes = [term_t, POINTER(c_int64)]
PL_get_int64.restype = c_int

# PL_EXPORT(int)        PL_unify_int64(term_t t, int64_t value) WUNUSED;
PL_unify_int64 = _lib.PL_unify_int64
PL_unify_int64.argtypes = [term_t, c_int64]
PL_unify_int64.restype = c_int

# PL_EXPORT(int)        PL_put_int64(term_t t, int64_t i) WUNUSED;
PL_put_int64 = _lib.PL_put_int64
PL_put_int64.argtypes = [term_t, c_int64]
PL_put_int64.restype = c_int


#                /*******************************
#                *           COMPARE            *
#                *******************************/
#
# PL_EXPORT(int)        PL_compare(term_t t1, term_t t2);
PL_compare = _lib.PL_compare
PL_compare.argtypes = [term_t, term_t]
PL_compare.restype = c_int

# PL_EXPORT(int)        PL_same_compound(term_t t1, term_t t2);
PL_same_compound = _lib.PL_same_compound
PL_same_compound.argtypes = [term_t, term_t]
PL_same_compound.restype = c_int


#                /*******************************
#                *      RECORDED DATABASE       *
#                *******************************/
#
# PL_EXPORT(record_t)   PL_record(term_t term);
PL_record = _lib.PL_record
PL_record.argtypes = [term_t]
PL_record.restype = record_t

# PL_EXPORT(int)        PL_recorded(record_t record, term_t term);
PL_recorded = _lib.PL_recorded
PL_recorded.argtypes = [record_t, term_t]
PL_recorded.restype = c_int

# PL_EXPORT(void)       PL_erase(record_t record);
PL_erase = _lib.PL_erase
PL_erase.argtypes = [record_t]
PL_erase.restype = None

# PL_EXPORT(char *)     PL_record_external(term_t t, size_t *size);
PL_record_external = _lib.PL_record_external
PL_record_external.argtypes = [term_t, POINTER(c_size_t)]
PL_record_external.restype = POINTER(c_char)

# PL_EXPORT(int)        PL_recorded_external(const char *rec, term_t term);
PL_recorded_external = _lib.PL_recorded_external
PL_recorded_external.argtypes = [POINTER(c_char), term_t]
PL_recorded_external.restype = c_int

# PL_EXPORT(int)        PL_erase_external(char *rec);
PL_erase_external = _lib.PL_erase_external
PL_erase_external.argtypes = [POINTER(c_char)]
PL_erase_external.restype = c_int


# PL_EXPORT(int)        PL_chars_to_term(const char *chars, term_t term);
PL_chars_to_term = _lib.PL_chars_to_term
PL_chars_to_term.argtypes = [c_char_p, term_t]
PL_chars_to_term.restype = c_int

# PL_EXPORT(int)        PL_wchars_to_term(const pl_wchar_t *chars, term_t term);
PL_wchars_to_term = _lib.PL_wchars_to_term
PL_wchars_to_term.argtypes = [POINTER(pl_wchar_t), term_t]
PL_wchars_to_term.restype = c_int

#                  /*******************************
#                  *          EMBEDDING           *
#                  *******************************/
#
# PL_EXPORT(int)                PL_initialise(int argc, char **argv);
PL_initialise = _lib.PL_initialise
PL_initialise.argtypes = [c_int, POINTER(c_char_p)]
PL_initialise.restype = c_int

# PL_EXPORT(int)                PL_is_initialised(int *argc, char ***argv);
PL_is_initialised = _lib.PL_is_initialised
PL_is_initialised.argtypes = [POINTER(c_int), POINTER(POINTER(c_char_p))]
PL_is_initialised.restype = c_int

# PL_EXPORT(int)                PL_toplevel(void);
PL_toplevel = _lib.PL_toplevel
PL_toplevel.argtypes = []
PL_toplevel.restype = c_int

# PL_EXPORT(int)                PL_cleanup(int status);
PL_cleanup = _lib.PL_cleanup
PL_cleanup.argtypes = [c_int]
PL_cleanup.restype = c_int

# PL_EXPORT(void)               PL_cleanup_fork();
PL_cleanup_fork = _lib.PL_cleanup_fork
PL_cleanup_fork.argtypes = []
PL_cleanup_fork.restype = None

# PL_EXPORT(int)                PL_halt(int status);
PL_halt = _lib.PL_halt
PL_halt.argtypes = [c_int]
PL_halt.restype = None


# typedef struct
# {
#   int __count;
#   union
#   {
#     wint_t __wch;
#     char __wchb[4];
#   } __value;            /* Value so far.  */
# } __mbstate_t;


class _mbstate_t_value(Union):
    _fields_ = [("__wch", wint_t),
                ("__wchb", c_char*4)]


class mbstate_t(Structure):
    _fields_ = [("__count", c_int),
                ("__value", _mbstate_t_value)]

# stream related funcs
Sread_function = CFUNCTYPE(ssize_t, c_void_p, c_char_p, c_size_t)
Swrite_function = CFUNCTYPE(ssize_t, c_void_p, c_char_p, c_size_t)
Sseek_function = CFUNCTYPE(c_long, c_void_p, c_long, c_int)
Sseek64_function = CFUNCTYPE(c_int64, c_void_p, c_int64, c_int)
Sclose_function = CFUNCTYPE(c_int, c_void_p)
Scontrol_function = CFUNCTYPE(c_int, c_void_p, c_int, c_void_p)

# IOLOCK
IOLOCK = c_void_p

# IOFUNCTIONS


class IOFUNCTIONS(Structure):
    _fields_ = [("read", Sread_function),
                ("write", Swrite_function),
                ("seek", Sseek_function),
                ("close", Sclose_function),
                ("seek64", Sseek64_function),
                ("reserved", intptr_t*2)]

# IOENC
(ENC_UNKNOWN, ENC_OCTET, ENC_ASCII, ENC_ISO_LATIN_1, ENC_ANSI, ENC_UTF8,
 ENC_UNICODE_BE, ENC_UNICODE_LE, ENC_WCHAR) = tuple(range(9))
IOENC = c_int

# IOPOS


class IOPOS(Structure):
    _fields_ = [("byteno", c_int64),
                ("charno", c_int64),
                ("lineno", c_int),
                ("linepos", c_int),
                ("reserved", intptr_t*2)]

# IOSTREAM


class IOSTREAM(Structure):
    _fields_ = [("bufp", c_char_p),
                ("limitp", c_char_p),
                ("buffer", c_char_p),
                ("unbuffer", c_char_p),
                ("lastc", c_int),
                ("magic", c_int),
                ("bufsize", c_int),
                ("flags", c_int),
                ("posbuf", IOPOS),
                ("position", POINTER(IOPOS)),
                ("handle", c_void_p),
                ("functions", IOFUNCTIONS),
                ("locks", c_int),
                ("mutex", IOLOCK),
                ("closure_hook", CFUNCTYPE(None, c_void_p)),
                ("closure", c_void_p),
                ("timeout", c_int),
                ("message", c_char_p),
                ("encoding", IOENC)]
IOSTREAM._fields_.extend([("tee", IOSTREAM),
                          ("mbstate", POINTER(mbstate_t)),
                          ("reserved", intptr_t*6)])


# PL_EXPORT(IOSTREAM *)  Sopen_string(IOSTREAM *s, char *buf, size_t sz,
# const char *m);
Sopen_string = _lib.Sopen_string
Sopen_string.argtypes = [POINTER(IOSTREAM), c_char_p, c_size_t, c_char_p]
Sopen_string.restype = POINTER(IOSTREAM)

# PL_EXPORT(int)         Sclose(IOSTREAM *s);
Sclose = _lib.Sclose
Sclose.argtypes = [POINTER(IOSTREAM)]


# PL_EXPORT(int)         PL_unify_stream(term_t t, IOSTREAM *s);
PL_unify_stream = _lib.PL_unify_stream
PL_unify_stream.argtypes = [term_t, POINTER(IOSTREAM)]


class _State(object):
    """Module state."""
    is_available = False  # True if prolog engine can accept API calls.

# External code can monitor this to ensure API calls are not made after
# the Prolog session is cleaned up.
state = _State()


class PrologError(Exception):
    pass


def _initialize():
    args = []
    args.append("./")
    args.append("-q")          # --quiet
    args.append("-nosignals")  # "Inhibit any signal handling by Prolog"
    if SWI_HOME_DIR is not None:
        args.append("--home=%s" % SWI_HOME_DIR)

    result = PL_initialise(len(args), list_to_bytes_list(args))
    # result is a boolean variable (i.e. 0 or 1) indicating whether the
    # initialisation was successful or not.
    if not result:
        raise PrologError("Could not initialize Prolog environment."
                          "PL_initialise returned %d" % result)

    swipl_fid = PL_open_foreign_frame()
    swipl_load = PL_new_term_ref()
    PL_chars_to_term(
        "asserta(pyrun(GoalString,BindingList) :- "
        "(atom_chars(A,GoalString),"
        "atom_to_term(A,Goal,BindingList),"
        "call(Goal))).".encode(), swipl_load)
    PL_call(swipl_load, None)
    PL_discard_foreign_frame(swipl_fid)
    global state
    state.is_available = True

_initialize()


@atexit.register
def cleanup_prolog():
    # There is a PL_cleanup function but according to the SWI documentation,
    # it does nothing useful.
    global state
    state.is_available = False
