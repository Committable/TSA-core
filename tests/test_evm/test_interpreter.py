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
        storage = None
        if 'post' in data and 'storage' in list(data['post'].values())[0]:
            storage = list(data['post'].values())[0]['storage']
        return storage if storage is not None and storage != {} else {"0x0": "0x0"}

    def _memory(self, data):
        memory = None
        if 'post' in data and 'memory' in list(data['post'].values())[0]:
            memory = list(data['post'].values())[0]['memory']
        return memory

    def _compare_storage_value(self, data, global_state):
        hex_storage = self._storage(data)
        int_storage = {}

        for x in hex_storage:
            key = int(x, 0)
            value = int(hex_storage[x], 0)
            int_storage[key] = value
            if key in global_state["storage"]:
                self.assertEqual(value, global_state["storage"][key])
            else:
                self.assertEqual(value, 0)
        for x in global_state["storage"]:
            if x not in int_storage:
                self.assertEqual(0, global_state["storage"][x])

    def _compare_memory_value(self, data, params_memory):
        hex_memory = self._memory(data)
        if hex_memory is not None:
            for x in hex_memory:
                self.assertIn(int(x, 0), params_memory.keys(), "start not in")
                self.assertEqual(int(hex_memory[x]["end"]), params_memory[int(x, 0)][0], "end not equal")
                self.assertEqual(int(hex_memory[x]["value"]), params_memory[int(x, 0)][1], "value not equal")

    def _test_opcode(self, name):
        with open(os.path.join(self.BASE_PATH, name + ".json")) as json_file:
            all_data = json.load(json_file)
        for x in all_data:
            log.mylogger.info("------------------Start Testing %s------------------", x)
            if x == "push32AndSuicide":
                log.mylogger.info("here")
            data = all_data[x]
            cname = x
            context = ctx.Context(time.time(), "", "", "", "", "")
            runtime = rt.EvmRuntime(
                context,
                opcodes=pyevmasm.disassemble_hex(data['exec']['code']).replace(
                    '\n', ' '),
                input_type=global_params.LanguageType.SOLIDITY,
                binary=data['exec']['code'][2:])
            runtime.build_cfg()
            interpreter = EVMInterpreter(runtime, cname, context)
            params = interpreter.sym_exec()
            if x in ["mulUnderFlow", "dup2error", "swap2error"]:
                self.assertEqual(params, None)
            else:
                self._compare_storage_value(data, params.global_state)
                self._compare_memory_value(data, params.memory)
            log.mylogger.info("------------------End Testing %s------------------", x)

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

    def test_mstore8MemExp(self):
        self._test_opcode("mstore8MemExp")

    def test_mstore8WordToBigError(self):
        self._test_opcode("mstore8WordToBigError")

    def test_mstore_mload0(self):
        self._test_opcode("mstore_mload0")

    def test_mstoreMemExp(self):
        self._test_opcode("mstoreMemExp")

    def test_mstoreWordToBigError(self):
        self._test_opcode("mstoreWordToBigError")

    def test_vmArithmeticTest(self):
        self._test_opcode("vmArithmeticTest")

    def test_vmBitwiseLogicOperationTest(self):
        self._test_opcode("vmBitwiseLogicOperationTest")

    def test_vmPushDupSwapTest(self):
        self._test_opcode("vmPushDupSwapTest")


if __name__ == "__main__":
    unittest.main()
