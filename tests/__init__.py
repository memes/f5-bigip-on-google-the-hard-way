"""Define functions common to all test cases in the tests namespace."""

import re
import shlex
from collections.abc import Callable, Generator
from typing import Any

from google.api_core.extended_operation import ExtendedOperation

EXPECTED_IAP_DEST_GROUPS = ["bigip-the-hard-way"]
EXPECTED_NETWORKS = ["bigip-the-hard-way-ext", "bigip-the-hard-way-mgt", "bigip-the-hard-way-int"]
EXPECTED_SUBNETS = ["bigip-the-hard-way-ext-1", "bigip-the-hard-way-mgt-1", "bigip-the-hard-way-int-1"]
EXPECTED_ADMIN_DATA_FIREWALL_RULE_NAME = "bigip-the-hard-way-allow-admin-ext"
EXPECTED_ADMIN_MGT_FIREWALL_RULE_NAME = "bigip-the-hard-way-allow-admin-mgt"
EXPECTED_BIG_IP_VM_NAMES = ["bigip-the-hard-way-01", "bigip-the-hard-way-02"]
EXPECTED_DSC_MGT_FIREWALL_RULE_NAME = "bigip-the-hard-way-allow-dsc-mgt"
EXPECTED_DSC_DATA_FIREWALL_RULE_NAME = "bigip-the-hard-way-allow-dsc-ext"
EXPECTED_FIREWALL_RULES = [
    EXPECTED_ADMIN_DATA_FIREWALL_RULE_NAME,
    EXPECTED_ADMIN_MGT_FIREWALL_RULE_NAME,
    EXPECTED_DSC_MGT_FIREWALL_RULE_NAME,
    EXPECTED_DSC_DATA_FIREWALL_RULE_NAME,
]
EXPECTED_BIG_IP_MGT_ADDRESSES = {
    "bigip-the-hard-way-01-mgt": "10.100.0.101",
    "bigip-the-hard-way-02-mgt": "10.100.0.102",
}
EXPECTED_BIG_IP_EXT_ADDRESSES = {
    "bigip-the-hard-way-01-ext": "10.0.0.101",
    "bigip-the-hard-way-02-ext": "10.0.0.102",
}
EXPECTED_BIG_IP_INT_ADDRESSES = {
    "bigip-the-hard-way-01-int": "10.10.0.101",
    "bigip-the-hard-way-02-int": "10.10.0.102",
}
EXPECTED_BIG_IP_ADDRESSES = {
    **EXPECTED_BIG_IP_MGT_ADDRESSES,
    **EXPECTED_BIG_IP_EXT_ADDRESSES,
    **EXPECTED_BIG_IP_INT_ADDRESSES,
}


def fenced_shell_matcher(element: dict[str, Any]) -> bool:
    """Return true if the parsed markdown element is a fenced code block of type shell."""
    return (
        element.get("type") == "block_code"
        and element.get("style") == "fenced"
        and element.get("attrs", {}).get("info") == "shell"
    )


def find_shell_block_code(root: dict[str, Any]) -> Generator[str]:
    """Find markdown blocks that look like fenced code blocks for shell and extract the 'raw' command as a string."""
    if fenced_shell_matcher(root):
        yield root["raw"]
    for child in root.get("children", []):
        yield from find_shell_block_code(child)


def tokenize_shell(
    raw: str,
) -> list[str]:
    """Extract the raw shell command to a set of arguments, overriding arguments to fit the testing environment."""
    tokenizer = shlex.shlex(raw, posix=True, punctuation_chars=True)
    tokenizer.whitespace += "\\"
    tokenizer.whitespace_split = True
    return list(tokenizer)


def env_substituter(
    env: dict[str, str] | None = None,
    unknown_value: str | None = None,
) -> Callable[[str], str]:
    """Return a function that finds and replaces tokens that look like environment variables from supplied dict.

    If an environment variable is detected but does not exist as a key in the env dict.
    """
    if not env:
        env = {}
    if unknown_value is None:
        unknown_value = "UNKNOWN_VARIABLE"
    pattern = re.compile(
        pattern=r"""
             ( (?:.*?(?<!\\))                   # Match non-variable ending in non-slash
               (?:\\\\)* )                      # Match 0 or even number of backslash
             (?:$|\$ (?: (\w+)|\{(\w+)\} ) )    # Match variable or END
        """,
        flags=re.VERBOSE | re.DOTALL,
    )

    def _substituter(raw: str) -> str:
        result = ""
        for m in re.finditer(pattern, raw):
            this = re.sub(r"\\(.)", lambda x: x.group(1), m.group(1))
            v = m.group(2) or m.group(3)
            if v:
                this += env.get(v, unknown_value)
            result += this
        return result

    return _substituter


def split_heredoc(raw: str) -> tuple[str, bytes | None]:
    """Given a potential shell command with heredoc, split into effective raw command and input."""
    if re.search(pattern=r"<<\w+", string=raw):
        command, command_stdin = re.split(pattern=r"<<\w+", string=raw, maxsplit=1)
        command_stdin = "\n".join(command_stdin.rstrip().split("\n")[1:-1]).encode(encoding="utf-8")
        return (command, command_stdin)
    return (raw, None)


def find_address_in_tokens(tokens: list[str]) -> str | None:
    """Return the first IP address found in command tokens."""
    try:
        return next(
            match.group(0)
            for match in [re.search(pattern=r"((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}", string=arg) for arg in tokens]
            if match
        )
    except StopIteration:
        return None


def handle_operation(operation: ExtendedOperation) -> None:
    """Watch the operation and raise an error if the operation indicates a failure."""
    operation.result(timeout=180)
    if operation.error_code:
        raise operation.exception() or RuntimeError(operation.error_message)
