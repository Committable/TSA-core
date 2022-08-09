pragma solidity ^0.8.0;

contract Incrementer {
    event Increment(uint256 value);
    event Reset();

    function increment(uint256 _value) public {
        emit Increment(_value);
    }

    function reset() public {
        emit Reset();
    }
}
