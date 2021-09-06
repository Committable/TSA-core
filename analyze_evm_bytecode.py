import global_params
from inputDealer.inputHelper import InputHelper
from interpreter.evmInterpreter import EVMInterpreter
from runtime.evmRuntime import EvmRuntime


def analyze_evm_bytecode():
    helper = InputHelper(global_params.EVM_BYTECODE, source=global_params.SRC_DIR)
    inp = helper.get_evm_inputs()[0]

    env = EvmRuntime(platform=global_params.PLATFORM, disasm_file=inp['disasm_file'])
    env.build_runtime_env()

    interpreter = EVMInterpreter(env)
    exit_code = interpreter.sym_exec()

    InputHelper.rm_tmp_files()

    return exit_code
