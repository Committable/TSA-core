from abstracts.ast import ast_abstract
import global_params
from input_dealer import solidity_ast_walker
import log


class AstHelper:

    def __init__(self, input_type, sources):
        if input_type == global_params.LanguageType.SOLIDITY:
            self.input_type = input_type  # input type of file
            self.ast_trees = {}
            # distinguish between legacyAST and ast format
            for x in sources:
                if 'legacyAST' in sources[x]:
                    self.ast_trees[x] = sources[x]['legacyAST']
                    self.ast_type = 'legacyAST'
                elif 'ast' in sources[x]:
                    self.ast_trees[x] = sources[x]['ast']
                    self.ast_type = 'ast'
                else:
                    log.mylogger.error('unknown ast type for %s', x)
                    raise Exception(f'unknown ast type for {x}')
            # sources is nil when source file is not compilable or not exist
            if len(sources) == 0:
                self.ast_type = 'unknown'
        else:
            raise Exception('There is no such type of input for AstHelper')

        self.contracts = self.extract_contract_definitions()

    def get_ast_json(self, filename, source, context):
        walker = solidity_ast_walker.AstWalker(self.ast_type, context.diff)
        if filename in self.ast_trees:
            root = self.ast_trees[filename]
            result = walker.walk_to_json(source, root, 0)
            result['ast_type'] = self.ast_type
            return result
        else:
            log.mylogger.warning('Has no %s\'s ast when get ast', filename)
            return {'ast_type': self.ast_type}

    def get_ast_abstract(self, filename, source, context):
        ast_abstract_instance = ast_abstract.AstAbstract()
        ast_abstract_instance.register_ast_abstracts(context)
        if filename in self.ast_trees:
            return ast_abstract_instance.get_ast_abstract_json(
                self.ast_trees[filename], self.ast_type, source)
        else:
            log.mylogger.warning('Has no %s\'s ast when get abstract', filename)
            return ast_abstract_instance.get_ast_abstract_json()

    def extract_contract_definitions(self):
        if self.ast_type == 'legacyAST':
            ret = {
                'contractsById': {},
                'contractsByName': {},
                'sourcesByContract': {}
            }

            walker = solidity_ast_walker.AstWalker(self.ast_type)
            for k, ast in self.ast_trees.items():
                nodes = []
                walker.walk(ast, {'name': 'ContractDefinition'}, nodes)
                for node in nodes:
                    ret['contractsById'][node['id']] = node
                    ret['sourcesByContract'][node['id']] = k
                    ret['contractsByName'][k + ':' +
                                           node['attributes']['name']] = node
            return ret
        else:
            return None

    def extract_state_variable_names(self, c_name):
        if self.ast_type == 'legacyAST':
            state_variables = self.extract_states_definitions()[c_name]
            var_names = []
            for var_name in state_variables:
                var_names.append(var_name['attributes']['name'])
            return var_names
        else:
            return None

    def extract_states_definitions(self):
        if self.ast_type == 'legacyAST':
            ret = {}
            for contract in self.contracts['contractsById']:
                name = self.contracts['contractsById'][contract]['attributes'][
                    'name']
                source = self.contracts['sourcesByContract'][contract]
                full_name = source + ':' + name
                ret[full_name] = self.extract_state_definitions(full_name)
            return ret
        else:
            return None

    def extract_state_definitions(self, c_name):
        if self.ast_type == 'legacyAST':
            node = self.contracts['contractsByName'][c_name]
            state_vars = []
            if node:
                base_contracts = self.get_linearized_base_contracts(
                    node['id'], self.contracts['contractsById'])
                base_contracts = list(base_contracts)
                base_contracts = list(reversed(base_contracts))
                for contract in base_contracts:
                    if 'children' in contract:
                        for item in contract['children']:
                            if item['name'] == 'VariableDeclaration':
                                state_vars.append(item)
            return state_vars
        else:
            return None

    def get_linearized_base_contracts(self, cid, contracts_by_id):
        return map(
            lambda cid: contracts_by_id[cid],
            contracts_by_id[cid]['attributes']['linearizedBaseContracts'])

    def extract_func_call_definitions(self, c_name):
        if self.ast_type == 'legacyAST':
            node = self.contracts['contractsByName'][c_name]
            walker = solidity_ast_walker.AstWalker(self.ast_type)
            nodes = []
            if node:
                walker.walk(node, {'name': 'FunctionCall'}, nodes)
            return nodes
        return []

    def get_callee_src_pairs(self, c_name):
        if self.ast_type == 'legacyAST':
            node = self.contracts['contractsByName'][c_name]
            walker = solidity_ast_walker.AstWalker(self.ast_type)
            nodes = []
            if node:
                list_of_attributes = [{
                    'attributes': {
                        'member_name': 'delegatecall'
                    }
                }, {
                    'attributes': {
                        'member_name': 'call'
                    }
                }, {
                    'attributes': {
                        'member_name': 'callcode'
                    }
                }]
                walker.walk(node, list_of_attributes, nodes)

            callee_src_pairs = []
            for node in nodes:
                if 'children' in node and node['children']:
                    type_of_first_child = node['children'][0]['attributes'][
                        'type']
                    if type_of_first_child.split(' ')[0] == 'contract':
                        contract = type_of_first_child.split(' ')[1]
                        contract_path = self._find_contract_path(
                            self.contracts['contractsByName'].keys(), contract)
                        callee_src_pairs.append((contract_path, node['src']))
            return callee_src_pairs
        else:
            return None

    def _find_contract_path(self, contract_paths, contract):
        for path in contract_paths:
            cname = path.split(':')[-1]
            if contract == cname:
                return path
        return ''

    def extract_func_call_srcs(self, c_name):
        if self.ast_type == 'legacyAST':
            func_calls = self.extract_func_calls_definitions()[c_name]
            func_call_srcs = []
            for func_call in func_calls:
                func_call_srcs.append(func_call['src'])
            return func_call_srcs
        return []

    def extract_func_calls_definitions(self):
        ret = {}
        for contract in self.contracts['contractsById']:
            name = self.contracts['contractsById'][contract]['attributes'][
                'name']
            source = self.contracts['sourcesByContract'][contract]
            full_name = source + ':' + name
            ret[full_name] = self.extract_func_call_definitions(full_name)
        return ret

    def get_func_name_to_params(self, c_name):
        if self.ast_type == 'legacyAST':
            node = self.contracts['contractsByName'][c_name]
            walker = solidity_ast_walker.AstWalker(self.ast_type)
            func_def_nodes = []
            if node:
                walker.walk(node, {'name': 'FunctionDefinition'},
                            func_def_nodes)

            func_name_to_params = {}
            for func_def_node in func_def_nodes:
                func_name = func_def_node['attributes']['name']
                params_nodes = []
                walker.walk(func_def_node, {'name': 'ParameterList'},
                            params_nodes)

                params_node = params_nodes[0]
                param_nodes = []
                walker.walk(params_node, {'name': 'VariableDeclaration'},
                            param_nodes)

                for param_node in param_nodes:
                    var_name = param_node['attributes']['name']
                    type_name = param_node['children'][0]['name']
                    if type_name == 'ArrayTypeName':
                        literal_nodes = []
                        walker.walk(param_node, {'name': 'Literal'},
                                    literal_nodes)
                        if literal_nodes:
                            array_size = int(
                                literal_nodes[0]['attributes']['value'])
                        else:
                            array_size = 1
                        param = {
                            'name': var_name,
                            'type': type_name,
                            'value': array_size
                        }
                    elif type_name == 'ElementaryTypeName':
                        param = {'name': var_name, 'type': type_name}
                    else:
                        param = {'name': var_name, 'type': type_name}

                    if func_name not in func_name_to_params:
                        func_name_to_params[func_name] = [param]
                    else:
                        func_name_to_params[func_name].append(param)
            return func_name_to_params
        else:
            return None
