import os

MACROS = {
    "$(MYPVPREFIX)": os.environ['MYPVPREFIX'],
    "$(EPICS_KIT_ROOT)": os.environ['EPICS_KIT_ROOT'],
    "$(ICPCONFIGROOT)": os.environ['ICPCONFIGROOT'],
    "$(ICPVARDIR)": os.environ['ICPVARDIR']
}

BLOCK_PREFIX = "CS:SB:"
BLOCKSERVER_PREFIX = MACROS["$(MYPVPREFIX)"] + "CS:BLOCKSERVER:"
PVPREFIX_MACRO = "$(MYPVPREFIX)"