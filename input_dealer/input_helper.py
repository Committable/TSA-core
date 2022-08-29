import os

import six

import errors
import global_params
from input_dealer import solidity_ast_helper
from input_dealer import solidity_compiler
from input_dealer import solidity_source_map
import log


class InputHelper:

    def __init__(self, input_type, **kwargs):
        self.input_type = input_type
        self.ast_helper = None
        self.source = None

        if input_type == global_params.LanguageType.SOLIDITY:
            attr_defaults = {
                'project_dir':
                    '',  # source dir of project, like /path/to/project dir
                'src_file': '',
                # relative path of the analyzed file to source dir,
                # like  relative/path/to/source file
                'root_path': '',
                'remaps': {},
                'allow_paths': [],
                'include_paths': [],
                'compiler_version': '',
                'compilation_err': False
            }
        else:
            log.mylogger.error('input type not supported')
            raise Exception('input type not supported')

        for (attr, default) in six.iteritems(attr_defaults):
            val = kwargs.get(attr, default)
            if val is None:
                log.mylogger.error('\'%s\' attribute can\'t be none', attr)
                raise Exception(f'\'{attr}\' attribute can\'t be none')
            else:
                setattr(self, attr, val)

    def get_solidity_inputs(self, compilation_cfg):
        inputs = []
        compilation_flag = True

        if self.input_type == global_params.LanguageType.SOLIDITY:
            # 1. compile the file
            compiler = solidity_compiler.SolidityCompiler(
                self.project_dir, self.src_file, self.root_path,
                self.allow_paths, self.remaps, self.include_paths,
                self.compiler_version, self.compilation_err)
            try:
                compiler.get_compiled_contracts_as_json(compilation_cfg)
            except errors.CompilationError:
                # TODO(Yang): we still analyze if there's a compilation err,
                #  and the compilation result is default nil
                compilation_flag = False

            # 2. get compilation result
            standard_json = compiler.combined_json
            absolute_src_path = os.path.abspath(
                os.path.join(self.project_dir, self.src_file))

            self.source = solidity_source_map.Source(absolute_src_path)
            self.ast_helper = solidity_ast_helper.AstHelper(
                self.input_type, standard_json['sources'])

            # 3. get contracts' evm and sourcemap info
            if absolute_src_path not in standard_json['sources']:
                log.mylogger.warning('%s has no source ast in compile result',
                                     absolute_src_path)
            else:
                if absolute_src_path in standard_json['contracts']:
                    contracts = standard_json['contracts'][absolute_src_path]
                    for contract in contracts:
                        opcodes = contracts[contract]['evm'][
                            'deployedBytecode']['opcodes']

                        source_map = solidity_source_map.SourceMap(
                            cname=contract,
                            input_type=self.input_type,
                            parent_file=absolute_src_path,
                            contract_evm_info=contracts[contract]['evm'],
                            ast_helper=self.ast_helper,
                            source=self.source)

                        inputs.append({
                            'contract':
                                contract,
                            'source_map':
                                source_map,
                            'ast_helper':
                                self.ast_helper,
                            'source':
                                self.source,
                            'src_file':
                                absolute_src_path,
                            'opcodes':
                                opcodes,
                            'binary':
                                contracts[contract]['evm']['deployedBytecode']
                                ['object']
                        })
                else:
                    log.mylogger.warning('%s has no contracts compiled',
                                         absolute_src_path)
        else:
            log.mylogger.error('Unknown file type')
            raise Exception(f'Unknown file type {self.input_type}')
        return inputs, compilation_flag
