UNIT_TEST = 0

# timeout for z3 solver for every computation (in ms)
TIMEOUT = 1000

# timeout to run symbolic execution (in secs)
GLOBAL_TIMEOUT = 2000

# output dir
DEST_PATH = "./output"

# specify platform for analysis
PLATFORM = ""

# show compilation
COMPILATION_ERR = False

# DIR for temp files
TMP_DIR = "./tmp"

AST = "legacyAST"

# Source dir of analysied program
SRC_DIR = ""

# file for analysis
SRC_FILE = ""

IS_BEFORE = True
# difference for this file
DIFFS = []

# source file type
EVM_BYTECODE = 0
WASM_BYTECODE = 1
SOLIDITY = 2
CPP = 3
GO = 4
