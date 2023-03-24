// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

library InternalLibrary {
    function add(uint x, uint y) internal pure returns(uint) {
        return x + y;
    }
}

contract Internal{
    function test(uint x, uint y) external pure returns(uint){
        return InternalLibrary.add(x, y);
    }
}

