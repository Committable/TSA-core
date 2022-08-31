pragma solidity ^0.8.0;

contract Toke {
    function tokenURI(uint256 tokenId) public returns (string memory) {
        string memory baseURI = _baseURI();
        return baseURI;
    }

    function _baseURI() internal returns (string memory) {
        return "abcfdsfdsafasddddddddffssssssssssssssssssssssssssssss";
    }
}