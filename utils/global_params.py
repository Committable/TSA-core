import enum


class LanguageType(enum.Enum):
    SOLIDITY = 1
    EVM = 2


# timeout to run analyse result (in secs)
SYM_TIMEOUT = 20000

# output dir
DEST_PATH = '../tmp'

# input dir
INPUT_PATH = '../tmp'

# show compilation
COMPILATION_ERR = False

# run in debug mod, which show more logs
DEBUG_MOD = False

# big int over 2^256, for not int
BIG_INT_256 = pow(2, 256)
