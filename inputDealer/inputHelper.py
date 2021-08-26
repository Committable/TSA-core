import logging
import os
import shutil
import re
import six

import global_params
from disassembler.evmDisassembler import EvmDisassembler
from disassembler.wasmModule import Module
from inputDealer.solidityCompiler import SolidityCompiler
from inputDealer.soliditySourceMap import SourceMap
import networkx as nx
import solcx
import subprocess

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
                'source': None,
                'joker': None,
                'evm': False,
                'root_path': "",
                'compiled_contracts': [],
                'compilation_err': False,
                'remap': "",
                'allow_paths': ""
            }

        elif input_type == global_params.WASM_BYTECODE:
            attr_defaults = {
                'source': None
            }

        for (attr, default) in six.iteritems(attr_defaults):
            val = kwargs.get(attr, default)
            if val is None:
                raise Exception("'%s' attribute can't be None" % attr)
            else:
                setattr(self, attr, val)

    def get_json_inputs(self):
        inputs = []
        if self.input_type == global_params.SOLIDITY:
            compiler = SolidityCompiler(self.source, self.joker, self.root_path, self.allow_paths, self.remap,
                                        self.compilation_err)

            contracts = compiler.get_compiled_contracts_from_json()

            for contract in contracts:
                disasm_file = contracts[contract]['evm']['deployedBytecode']['opcodes']

                source_map = SourceMap(cname=contract, input_type=self.input_type, parent_file=self.joker,
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

    def rm_tmp_files(self):
        shutil.rmtree(global_params.TMP_DIR, ignore_errors=True)
