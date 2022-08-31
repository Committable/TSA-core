// SPDX-License-Identifier:  MIT
pragma solidity ^0.8.0;
contract Incrementer {
    uint256 public number;

    function increment(uint256 _value) public {
        require(_value > 0, "be positive");
        number = number + _value;
    }

}