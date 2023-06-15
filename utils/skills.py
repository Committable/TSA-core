class Skills:
    def __init__(self, content):
        self.tags = []
        self.contracts = {}
        self.contract_2_tags = {}
        for tag in content:
            self.tags.append(tag)
            for contract in content[tag]:
                if isinstance(contract, dict):
                    for contract_name in contract:
                        self._add_contract(contract_name, tag)
                        for func in contract[contract_name]:
                            self.contracts[contract_name].append(func)
                else:
                    self._add_contract(contract, tag,)

    def get_tags_from_contract(self, contract):
        if contract in self.contract_2_tags:
            return self.contract_2_tags[contract]
        else:
            return []

    def _add_contract(self, contract, tag):
        if contract not in self.contract_2_tags:
            self.contract_2_tags[contract] = []
        self.contract_2_tags[contract].append(tag)
        if contract not in self.contracts:
            self.contracts[contract] = []
