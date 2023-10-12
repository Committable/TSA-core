class Skills:

    def __init__(self, content):
        self.tags = []
        self.contracts = {"API": {}, "Interface": {}}
        self.contract_2_tags = {"API": {}, "Interface": {}}
        if "API" in content:
            for tag in content["API"]:
                self.tags.append(tag)
                for contract in content["API"][tag]:
                    if isinstance(contract, dict):
                        for contract_name in contract:
                            self._add_contract_api(contract_name, tag)
                            for func in contract[contract_name]:
                                self.contracts["API"][contract_name].append(
                                    func)
                    else:
                        self._add_contract_api(contract, tag)
        if "Interface" in content:
            for tag in content["Interface"]:
                self.tags.append(tag)
                for contract in content["Interface"][tag]:
                    if isinstance(contract, dict):
                        for contract_name in contract:
                            self._add_contract_interface(contract_name, tag)
                            for func in contract[contract_name]:
                                self.contracts["Interface"][
                                    contract_name].append(func)
                    else:
                        self._add_contract_interface(contract, tag)

    def has_api(self):
        if self.contracts["API"] != {}:
            return True
        else:
            return False

    def has_interface(self):
        if self.contracts["Interface"] != {}:
            return True
        else:
            return False

    def get_api_tags_from_contract(self, contract):
        if contract in self.contract_2_tags["API"]:
            return self.contract_2_tags["API"][contract]
        else:
            return []

    def get_interface_tags_from_functions(self, functions):
        tags = set()
        for contract in self.contracts["Interface"]:
            implement = True
            for func in self.contracts["Interface"][contract]:
                if func not in functions:
                    implement = False
                    break
            if implement:
                for tag in self.contract_2_tags["Interface"][contract]:
                    tags.add(tag)
        return list(tags)

    def _add_contract_api(self, contract, tag):
        if contract not in self.contract_2_tags["API"]:
            self.contract_2_tags["API"][contract] = []
        self.contract_2_tags["API"][contract].append(tag)
        if contract not in self.contracts["API"]:
            self.contracts["API"][contract] = []

    def _add_contract_interface(self, contract, tag):
        if contract not in self.contract_2_tags["Interface"]:
            self.contract_2_tags["Interface"][contract] = []
        self.contract_2_tags["Interface"][contract].append(tag)
        if contract not in self.contracts["Interface"]:
            self.contracts["Interface"][contract] = []
