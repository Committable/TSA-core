import unittest
import time
import os
import json
import pyevmasm

from interpreter.evm_interpreter import EVMInterpreter
from utils import context as ctx
from utils import global_params, log
from runtime import evm_runtime as rt

global_params.DEST_PATH = "./tmp"

log.mylogger = log.get_logger()

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class TestEvmInterpreter(unittest.TestCase):
    BASE_PATH = os.path.join(THIS_DIR, "./test_data")

    def _storage(self, data):
        storage = list(data['post'].values())[0]['storage']
        return storage if storage is not None else {"0": "0"}

    def _compare_storage_value(self, data, global_state):
        hex_storage = self._storage(data)
        storage = {}
        for x in hex_storage:
            storage[int(x, 0)] = int(hex_storage[x], 0)
        self.assertDictEqual(storage, global_state["storage"])

    def _test_opcode(self, name):
        with open(os.path.join(self.BASE_PATH, name+".json")) as json_file:
            all_data = json.load(json_file)
        for x in all_data:
            data = all_data[x]
            cname = x
            context = ctx.Context(time.time(), "", "", "", "", "")
            runtime = rt.EvmRuntime(context,
                                    opcodes=pyevmasm.disassemble_hex(data['exec']['code']).replace('\n', ' '),
                                    input_type=global_params.LanguageType.SOLIDITY,
                                    binary=data['exec']['code'][2:])
            runtime.build_cfg()
            interpreter = EVMInterpreter(runtime, cname, context)
            params = interpreter.sym_exec()
            self._compare_storage_value(data, params.global_state)

    def test_msize0(self):
        self._test_opcode("msize0")

    def test_msize1(self):
        self._test_opcode("msize1")

    def test_msize2(self):
        self._test_opcode("msize2")

    def test_msize3(self):
        self._test_opcode("msize3")

    def test_mstore0(self):
        self._test_opcode("mstore0")

    def test_mstore1(self):
        self._test_opcode("mstore1")

    def test_mstore8_0(self):
        self._test_opcode("mstore8_0")

    def test_mstore8_1(self):
        self._test_opcode("mstore8_1")

if __name__ == "__main__":
    unittest.main()
