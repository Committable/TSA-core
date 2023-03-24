// SPDX-License-Identifier: MIT

pragma solidity ^0.8.0;

library ExternalLibrary {
    function add(uint x, uint y) external pure returns(uint) {
        return x + y;
    }
  
}

contract External{
    function test(uint x, uint y) external pure returns(uint){
        return ExternalLibrary.add(x,y);
    }
}

