pragma solidity ^0.4.25;



// ----------------------------------------------------------------------------
// Safe Math Library
// ----------------------------------------------------------------------------
contract SafeMath {
    function Add(uint a, uint b) public pure returns (uint c) {
        c = a + b;
        require(c >= a);
    }
    function Sub(uint a, uint b) public pure returns (uint c) {
        require(b <= a);
        c = a - b;
    }
}


contract CodeToken is SafeMath {
    string public name;
    string public symbol;
    uint8 public decimals; // 18 decimals is the strongly suggested default, avoid changing it

    uint256 public _totalSupply;

    mapping(address => uint) balances;
    mapping(address => mapping(address => uint)) allowed;

    /**
     * Constrctor function
     *
     * Initializes contract with initial supply tokens to the creator of the contract
     */
    constructor() public {
        name = "CodeToken";
        symbol = "CT";
        decimals = 18;
        _totalSupply = 100000000000000000000000000;

        balances[msg.sender] = _totalSupply;
    }

    function transfer(address to, uint tokens) public returns (bool success) {
        return true;
    }

    function transferFrom(address from, address to, uint tokens) public returns (bool success) {
        return true;
    }
}
