pragma solidity ^0.8.0;
import "./IERC777Sender.sol";
import "./IERC1820Registry.sol";

contract ERC777{
    IERC1820Registry constant internal _ERC1820_REGISTRY = IERC1820Registry(0x1820a4B7618BdE71Dce8cdc73aAB6C95905faD24);
    bytes32 private constant _TOKENS_SENDER_INTERFACE_HASH = keccak256("ERC777TokensSender");
    constructor() {
    }

    function callTokensToSend(
            address operator,
            address from,
            address to,
            uint256 amount,
            bytes memory userData,
            bytes memory operatorData
        ) public
        {
            address implementer = _ERC1820_REGISTRY.getInterfaceImplementer(from, _TOKENS_SENDER_INTERFACE_HASH);
            if (implementer != address(0)) {
                IERC777Sender(implementer).tokensToSend(operator, from, to, amount, userData, operatorData);
            }
        }
}