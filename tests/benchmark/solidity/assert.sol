pragma solidity ^0.8.0;

contract Incrementer {

    function increment(uint256 _value) public {
        assert(_value > 10);
    }
}
