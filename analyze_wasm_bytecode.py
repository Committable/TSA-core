import global_params
from interpreter.wasmInterpreter import WASMInterpreter
from runtime.wasmRuntime import WASMRuntime
from inputDealer.inputHelper import InputHelper


def analyze_wasm_bytecode():
    helper = InputHelper(global_params.WASM_BYTECODE, source=global_params.SRC_DIR)
    inp = helper.get_wasm_inputs()[0]

    runtime = WASMRuntime(inp["module"])

    runtime.__repr__()
    engine = WASMInterpreter(runtime)
    engine.exec("_initialize")

    return
