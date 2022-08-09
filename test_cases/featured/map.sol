pragma solidity ^0.4.24;

contract Bet {
   mapping (address => uint256) public balanceOf;

   function depositFunds(uint256 _value) {
       balanceOf[msg.sender] += _value;
       msg.sender.call.value(_value);
   }
}