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
            if val is None:
                raise Exception("'%s' attribute can't be None" % attr)
            else:
                setattr(self, attr, val)

    def get_json_inputs(self, target):
        inputs = []
        if self.input_type == InputHelper.SOLIDITY:
            compiler = SolidityCompiler(self.source, self.root_path, self.allow_paths, self.remap,
                                        self.compilation_err, global_params.TMP_DIR)
            data_dict = {}
            contracts = {}
            try:
                #with open(self.source+os.sep+target, 'r') as inputfile:
                    
                solcx.install_solc("0.4.25")
                data_dict = solcx.compile_files(
                    [self.source + os.sep + target],
                    output_values=["abi", "bin-runtime", "ast", "asm", "opcodes"],
                    solc_version="0.4.25"
                )
                combined_json = {"contracts":{}, "sources":{}}
                for contract in data_dict:
                    try:
                        evm_file = "./tmp/evm.bin_runtime"
                        with open(evm_file, 'w') as of:
                            of.write(re.sub(r"a165627a7a72305820\S{64}0029$", "",data_dict[contract]["bin-runtime"]))
                        disasm_out = ""

                        disasm_p = subprocess.Popen(["evm", "disasm", evm_file], stdout=subprocess.PIPE)
                        disasm_out = disasm_p.communicate()[0].decode('utf-8', 'strict')
                        lines = disasm_out.split("\n")
                        deployedBytecode = ""
                        i = 0
                        for x in lines[1:]:
                            i = i+1
                            x = x.replace('SELFDESTRUCT', 'SUICIDE')
                            x = x.replace('Missing opcode 0xfd', 'REVERT')
                            x = x.replace('Missing opcode 0xfe', 'INVALID')
                            if "Missing opcode" in x:
                                break
                            try:
                                deployedBytecode = deployedBytecode + x.split(": ")[1] + " "
                            except:
                                break
                    except Exception as err:
                        continue
                    combined_json["contracts"][contract] = {'evm':
                                               {'deployedBytecode':
                                                    {'opcodes':
                                                         deployedBytecode
                                                     },
                                                "bytecode":
                                                    {"object":
                                                        data_dict[contract]["bin-runtime"]
                                                    },
                                                'legacyAssembly':
                                                    data_dict[contract]["asm"]
                                                }
                                           }
                    combined_json["sources"] = {
                        target:
                            {"legacyAST":
                                 data_dict[contract]['ast']
                             }
                    }
                contracts = combined_json["contracts"]
                global_params.PROJECT = "uniswap-v2-core"
                for contract in contracts:

                    cname = contract
                    disasm_file = contracts[contract]['evm']['deployedBytecode']['opcodes']

                    source_map = SourceMap(cname=cname, input_type='solidity-json', contract=contract,
                                           sources=combined_json)

                    inputs.append({
                        'contract': contract,
                        'source_map': source_map,
                        'source': self.source,
                        'c_source': source_map.position_groups[cname],
                        'c_name': cname,
                        'disasm_file': disasm_file,
                        'evm': contracts[contract]['evm']['bytecode']['object']
                    })
            except Exception as err:
                print(err)
                logging.error("solcx compile fail")
                contracts = compiler.get_compiled_contracts_from_json()
                if global_params.PROJECT == "uniswap-v2-core":
                    for contract in contracts:
                        if target == contract.split(":")[0]:
                            cname = contract
                            disasm_file = contracts[contract]['evm']['deployedBytecode']['opcodes']

                            source_map = SourceMap(cname=cname, input_type='solidity-json', contract=contract, sources=compiler.combined_json)


                            inputs.append({
                                'contract': contract,
                                'source_map': source_map,
                                'source': self.source,
                                'c_source': source_map.position_groups[cname],
                                'c_name': cname,
                                'disasm_file': disasm_file,
                                'evm': contracts[contract]['evm']['bytecode']['object']
                            })
                elif global_params.PROJECT == "openzeppelin-contracts":
                    for contract in contracts:
                        if target == contract:
                            for c in contracts[contract]:
                                cname = c
                                disasm_file = contracts[contract][c]['evm']['deployedBytecode']['opcodes']

                                source_map = SourceMap(cname=cname, input_type='solidity-json', contract=contract,
                                                       sources=compiler.combined_json)
                                c_source = None
                                if cname in source_map.position_groups:
                                    c_source = source_map.position_groups[cname]
                                inputs.append({
                                    'contract': contract,
                                    'source_map': source_map,
                                    'source': self.source,
                                    'c_source': c_source,
                                    'c_name': cname,
                                    'disasm_file': disasm_file,
                                    'evm': contracts[contract][cname]['evm']['bytecode']['object']
                                })

        else:
            logging.critical("Unknow file type")
            exit(1)
        return inputs

    def get_inputs(self):
        inputs = []
        if self.input_type == InputHelper.EVM_BYTECODE:
            disassembler = EvmDisassembler(self.source, self.source, global_params.TMP_DIR)
            disassembler.prepare_disasm_file()
            disasm_file = disassembler.get_temporary_files()['disasm']

            inputs.append({'disasm_file': disasm_file})

        elif self.input_type == InputHelper.SOLIDITY:
            compiler = SolidityCompiler(self.source, self.root_path, self.allow_paths, self.remap,
                                        self.compilation_err, global_params.TMP_DIR)
            contracts = compiler.get_compiled_contracts()

            for contract in contracts:
                if contracts[contract] == "":
                    continue
                disassembler = EvmDisassembler(self.source, contract, global_params.TMP_DIR)
                disassembler.prepare_disasm_file()

                cname = contract.split(os.path.sep)[-1].split(".bin")[0]

                source_map = SourceMap(cname, self.source, 'solidity', self.root_path, self.remap, self.allow_paths)
                c_source = source_map.cname.split(":")[0]


                disasm_file = disassembler.get_temporary_files()['disasm']
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
        shutil.rmtree(global_params.TMP_DIR, ignore_errors=True)
