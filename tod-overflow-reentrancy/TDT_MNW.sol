pragma solidity ^0.4.2;

contract Migrations {
  address public owner;
  uint public last_completed_migration;
  address public target = 0xca35b7d915458ef540ade6068dfe2f44e8fa733c;

  modifier restricted() {
    if (msg.sender == owner) _;
  }

  function Migrations() {
    owner = msg.sender;
  }

  function changeOwner(address myowner) {
    owner = myowner;
  }

  function sendEther(address target) restricted {
    target.call.value(1)();
  }
}
