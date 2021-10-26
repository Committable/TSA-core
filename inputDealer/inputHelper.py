import logging
import shutil
import six
import os

import global_params

from disassembler.evmDisassembler import EvmDisassembler
from disassembler.wasmModule import Module
from inputDealer.solidityCompiler import SolidityCompiler
from inputDealer.soliditySourceMap import SourceMap

logger = logging.getLogger(__name__)


class InputHelper:
    def __init__(self, input_type, **kwargs):
        self.input_type = input_type

        if input_type == global_params.EVM_BYTECODE:
            attr_defaults = {
                'source': None,
                'evm': False
            }
        elif input_type == global_params.SOLIDITY:
            attr_defaults = {
                'source': "",  # source dir of project
                'joker': "",  # relative path of the analized file to source dir
                'root_path': "",
                'remap': "",
                'allow_paths': "",
                'compilation_err': False
            }
        elif input_type == global_params.WASM_BYTECODE:
            attr_defaults = {
                'source': None
            }

        else:
            logger.critical("input type not supported")
            raise Exception

        for (attr, default) in six.iteritems(attr_defaults):
            val = kwargs.get(attr, default)
            if val is None:
                raise Exception("'%s' attribute can't be None" % attr)
            else:
                setattr(self, attr, val)

    def get_solidity_inputs(self):
        inputs = []

        if self.input_type == global_params.SOLIDITY:
            compiler = SolidityCompiler(self.source, self.joker,
                                        self.root_path, self.allow_paths, self.remap,
                                        self.compilation_err)

            try:
                compiler.get_compiled_contracts_as_json()
            except Exception as err:
                compiler.rm_compiled_files()
                raise Exception("Complied Fail: %s", str(err))
            compiler.rm_compiled_files()
            # self.joker may not in build result if not code in solidity file
            if self.joker not in compiler.combined_json["contracts"]:
                if self.joker in compiler.combined_json["sources"]:
                    source_map = SourceMap(cname="",
                                           input_type=self.input_type,
                                           parent_file=self.joker,
                                           sources=compiler.combined_json)
                return []

            contracts = compiler.combined_json["contracts"][self.joker]
            for contract in contracts:
                disasm_file = contracts[contract]['evm']['deployedBytecode']['opcodes']

                source_map = SourceMap(cname=contract,
                                       input_type=self.input_type,
                                       parent_file=self.joker,
                                       sources=compiler.combined_json)

                inputs.append({
                    'contract': contract,
                    'source_map': source_map,
                    'source': self.source,
                    "joker": self.joker,
                    'disasm_file': disasm_file,
                    'evm': contracts[contract]['evm']['deployedBytecode']['object']
                })
        else:
            logger.critical("Unknow file type")
            raise Exception
        return inputs

    def get_evm_inputs(self):
        inputs = []
        if self.input_type == global_params.EVM_BYTECODE:
            disassembler = EvmDisassembler(self.source, self.source, global_params.TMP_DIR)
            disassembler.prepare_disasm_file()
            disasm_file = disassembler.get_temporary_files()['disasm']

            inputs.append({'disasm_file': disasm_file})
        return inputs

    def get_wasm_inputs(self):
        inputs = []
        if self.input_type == global_params.WASM_BYTECODE:
            with open(self.source, 'rb') as f:
                self.module = Module.from_reader(f)

            inputs.append({"module": self.module})
        return inputs

    @classmethod
    def rm_tmp_files(cls):
        shutil.rmtree(global_params.TMP_DIR, ignore_errors=True)
