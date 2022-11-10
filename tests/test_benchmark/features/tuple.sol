pragma solidity ^0.5.0;

contract SolidityTest {
   uint storedData;
   constructor() public{
      storedData = 10;
   }
   function getResult() public view returns(string memory){
      uint a;
      uint b;
      uint result = add(a, b);
      return integerToString(result);
   }
   function add(uint a, uint b) internal pure returns (uint){
        return (a + b);
   }
   function integerToString(uint _i) internal pure
      returns (string memory) {
      if (_i == 0) {
         return "0";
      }
      uint j = _i;
      uint len;
      while (j != 0) {
         len++;
         j /= 10;
      }
      bytes memory bstr = new bytes(len);
      uint k = len - 1;
      while (_i != 0) {
         bstr[k--] = byte(uint8(48 + _i % 10));
         _i /= 10;
      }
      return string(bstr);
   }
}
