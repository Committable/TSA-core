import re
import logging
from inputDealer.solidityCompiler import SolidityCompiler
from disassembler.evmDisassembler import EvmDisassembler
from disassembler.wasmModule import Module
from inputDealer.soliditySouceMap import SourceMap
import six

class InputHelper:
    EVM_BYTECODE = 0
    WASM_BYTECODE = 1
    SOLIDITY = 2
    CPP = 3
    GO = 4

    def __init__(self, input_type, **kwargs):
        self.input_type = input_type

        if input_type == InputHelper.EVM_BYTECODE:
            attr_defaults = {
                'source': None,
                'evm': False
            }
        elif input_type == InputHelper.SOLIDITY:
            attr_defaults = {
                'source': None,
                'evm': False,
                'root_path': "",
                'compiled_contracts': [],
                'compilation_err': False,
                'remap': "",
                'allow_paths': ""
            }

        elif input_type == InputHelper.WASM_BYTECODE:
            attr_defaults = {
                'source': None
            }
        # TODO:
        # elif input_type == InputHelper.CPP:
        #     attr_defaults = {
        #         'source': None,
        #         'evm': False,
        #         'root_path': "",
        #         'compiled_contracts': [],
        #     }
        # elif input_type == InputHelper.GO:
        #     attr_defaults = {
        #         'source': None,
        #         'evm': False,
        #         'root_path': "",
        #         'compiled_contracts': [],
        #     }

        for (attr, default) in six.iteritems(attr_defaults):
            val = kwargs.get(attr, default)
            if val == None:
                raise Exception("'%s' attribute can't be None" % attr)
            else:
                setattr(self, attr, val)

    def get_inputs(self):
        inputs = []
        if self.input_type == InputHelper.EVM_BYTECODE:
            self.disassembler = EvmDisassembler(self)
            with open(self.source, 'r') as f:
                bytecode = f.read()
            self.disassembler.prepare_disasm_file(self.source, bytecode)

            disasm_file = self.disassembler.get_temporary_files(self.source)['disasm']
            inputs.append({'disasm_file': disasm_file})
        elif self.input_type == InputHelper.SOLIDITY:
            self.compiler = SolidityCompiler(self)
            contracts = self.compiler.get_compiled_contracts()
            self.disassembler = EvmDisassembler(self)
            for contract, bytecode in contracts:
                self.disassembler.prepare_disasm_file(contract, bytecode)
            for contract, _ in contracts:
                c_source, cname = contract.split(':')
                c_source = re.sub(self.root_path, "", c_source)
                source_map = SourceMap(contract, self.source, 'solidity', self.root_path, self.remap, self.allow_paths)
                disasm_file = self.disassembler.get_temporary_files(contract)['disasm']
                inputs.append({
                    'contract': contract,
                    'source_map': source_map,
                    'source': self.source,
                    'c_source': c_source,
                    'c_name': cname,
                    'disasm_file': disasm_file
                })
        elif self.input_type == InputHelper.WASM_BYTECODE:
            with open(self.source, 'rb') as f:
                self.module = Module.from_reader(f)

            inputs.append({"module": self.module})

        elif self.input_type == InputHelper.CPP:
            pass
            #TODO
        elif self.input_type == InputHelper.GO:
            pass
            #TODO
        else:
            logging.critical("Unknow file type")
            exit(1)
        return inputs

    def rm_tmp_files(self):
        if self.input_type == InputHelper.EVM_BYTECODE:
            self.disassembler.rm_tmp_files(self.source)
        elif self.input_type == InputHelper.SOLIDITY:
            self.compiler.rm_tmp_files_of_multiple_contracts(self.compiled_contracts)







