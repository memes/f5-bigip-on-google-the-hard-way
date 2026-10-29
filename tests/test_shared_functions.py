"""Verify common test functions."""

from typing import Any

import pytest

from tests import (
    env_substituter,
    fenced_shell_matcher,
    find_address_in_tokens,
    find_shell_block_code,
    split_heredoc,
    tokenize_shell,
)


@pytest.mark.parametrize(
    ("block", "expected"),
    [
        pytest.param({}, False, id="empty"),
        pytest.param({"type": "block_code", "style": "fenced", "attrs": {"info": "text"}}, False, id="text"),
        pytest.param({"type": "block_code", "style": "fenced", "attrs": {"info": "shell"}}, True, id="shell"),
    ],
)
def test_fenced_shell_matcher(block: dict[str, Any], *, expected: bool) -> None:
    """Verify behavior of fenced_shell_matcher function."""
    assert fenced_shell_matcher(block) == expected


@pytest.mark.parametrize(
    ("root", "expected"),
    [
        pytest.param({}, [], id="empty"),
        pytest.param({"type": "paragraph"}, [], id="para-no-children"),
        pytest.param({"type": "paragraph", "children": [{"type": "paragraph"}]}, [], id="para-children-no-shell"),
        pytest.param(
            {
                "type": "paragraph",
                "children": [
                    {
                        "type": "paragraph",
                        "children": [
                            {"type": "block_code", "style": "fenced", "attrs": {"info": "shell"}, "raw": "foo bar baz"},
                        ],
                    },
                ],
            },
            ["foo bar baz"],
            id="nested-shell",
        ),
        pytest.param(
            {
                "type": "block_code",
                "style": "fenced",
                "attrs": {"info": "shell"},
                "raw": "one",
                "children": [
                    {
                        "type": "paragraph",
                        "children": [
                            {
                                "type": "paragraph",
                                "children": [
                                    {
                                        "type": "block_code",
                                        "style": "fenced",
                                        "attrs": {"info": "shell"},
                                        "raw": "two",
                                    },
                                ],
                            },
                            {"type": "block_code", "style": "fenced", "attrs": {"info": "shell"}, "raw": "three"},
                        ],
                    },
                ],
            },
            ["one", "two", "three"],
            id="nested-multi-shell",
        ),
    ],
)
def test_find_shell_block_code(root: dict[str, Any], expected: list[str]) -> None:
    """Verify behavior of find_shell_block_code function."""
    assert list(find_shell_block_code(root)) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("", [], id="empty"),
        pytest.param("foo bar baz", ["foo", "bar", "baz"], id="simple"),
        pytest.param("foo $bar baz", ["foo", "$bar", "baz"], id="shell-var"),
        pytest.param("foo ${bar} baz", ["foo", "${bar}", "baz"], id="brace-shell-var"),
        pytest.param(
            "foo --argument 'This is an argument'",
            ["foo", "--argument", "This is an argument"],
            id="quoted-arg",
        ),
        pytest.param(
            "foo \\\n\t--argument='This is an argument'",
            ["foo", "--argument=This is an argument"],
            id="line-break-quoted-arg",
        ),
        pytest.param(
            "foo \\\n\t--argument='This is an argument with $var'",
            ["foo", "--argument=This is an argument with $var"],
            id="line-break-quoted-arg-with-var",
        ),
        pytest.param(
            "foo \\\n\t--argument \\ \n\t'This is an argument'",
            ["foo", "--argument", "This is an argument"],
            id="multi-line-break-quoted-arg",
        ),
        pytest.param(
            "foo \\\n\t--argument \\ \n\t'This is an argument with ${var}'",
            ["foo", "--argument", "This is an argument with ${var}"],
            id="multi-line-break-quoted-arg-with-bracket-var",
        ),
    ],
)
def test_tokenize_shell(raw: str, expected: list[str]) -> None:
    """Verify behavior tokenize_shell function."""
    assert tokenize_shell(raw) == expected


@pytest.mark.parametrize(
    ("value", "env", "expected"),
    [
        pytest.param("", None, "", id="empty-str-none-env"),
        pytest.param("foo", None, "foo", id="no-var-none-env"),
        pytest.param("foo $bar", None, "foo UNKNOWN_VARIABLE", id="end-var-none-env"),
        pytest.param("foo ${bar}", None, "foo UNKNOWN_VARIABLE", id="end-bracket-var-none-env"),
        pytest.param("foo ${bar} baz", None, "foo UNKNOWN_VARIABLE baz", id="mid-bracket-var-none-env"),
        pytest.param("", {}, "", id="empty-str-empty-env"),
        pytest.param("foo", {}, "foo", id="no-var-empty-env"),
        pytest.param("foo $bar", {}, "foo UNKNOWN_VARIABLE", id="end-var-empty-env"),
        pytest.param("foo ${bar}", {}, "foo UNKNOWN_VARIABLE", id="end-bracket-var-empty-env"),
        pytest.param("foo ${bar} baz", {}, "foo UNKNOWN_VARIABLE baz", id="mid-bracket-var-empty-env"),
        pytest.param("", {"x": "xxx"}, "", id="empty-str-x-env"),
        pytest.param("foo", {"x": "xxx"}, "foo", id="no-var-x-env"),
        pytest.param("foo $bar", {"x": "xxx"}, "foo UNKNOWN_VARIABLE", id="end-var-x-env"),
        pytest.param("foo ${bar}", {"x": "xxx"}, "foo UNKNOWN_VARIABLE", id="end-bracket-var-x-env"),
        pytest.param("foo ${bar} baz", {"x": "xxx"}, "foo UNKNOWN_VARIABLE baz", id="mid-bracket-var-x-env"),
        pytest.param("", {"bar": "xxx"}, "", id="empty-str-bar-env"),
        pytest.param("foo", {"bar": "xxx"}, "foo", id="no-var-bar-env"),
        pytest.param("foo $bar", {"bar": "xxx"}, "foo xxx", id="end-var-bar-env"),
        pytest.param("foo ${bar}", {"bar": "xxx"}, "foo xxx", id="end-bracket-var-bar-env"),
        pytest.param("foo ${bar} baz", {"bar": "xxx"}, "foo xxx baz", id="mid-bracket-var-bar-env"),
    ],
)
def test_env_substituter(value: str, env: dict[str, str] | None, expected: str) -> None:
    """Verify the value string is expanded to meet expectations."""
    substituter = env_substituter(env=env)
    assert substituter(value) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param("", ("", None), id="empty"),
        pytest.param("foo bar baz", ("foo bar baz", None), id="no-heredoc-simple"),
        pytest.param("foo $bar baz", ("foo $bar baz", None), id="no-heredoc-shell-var"),
        pytest.param("foo ${bar} baz", ("foo ${bar} baz", None), id="no-heredoc-brace-shell-var"),
        pytest.param("<<FOO", ("", b""), id="invalid-heredoc"),
        pytest.param("foo bar baz<<FOO\nthis is input\nFOO", ("foo bar baz", b"this is input"), id="heredoc"),
        pytest.param(
            "foo bar baz <<FOO\nthis is input\nFOO\n\n",
            ("foo bar baz ", b"this is input"),
            id="heredoc-trailing-whitespace",
        ),
        pytest.param(
            "foo bar baz <<FOO\t  \n\n\tthis is input\nFOO",
            ("foo bar baz ", b"\n\tthis is input"),
            id="heredoc-leading-whitespace",
        ),
    ],
)
def test_split_heredoc(raw: str, expected: tuple[str, bytes | None]) -> None:
    """Verify behavior of split_heredoc function."""
    assert split_heredoc(raw) == expected


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        pytest.param([], None, id="empty"),
        pytest.param(["foo", "bar", "baz"], None, id="no-address-simple"),
        pytest.param(["foo $bar baz"], None, id="no-address-shell-var"),
        pytest.param(["foo", "${bar}", "baz"], None, id="no-address-brace-shell-var"),
        pytest.param(["foo", "1.2.3.4", "baz"], "1.2.3.4", id="bare-address"),
        pytest.param(["foo", "admin@1.2.3.4", "baz"], "1.2.3.4", id="user-at-address"),
        pytest.param(["foo", "admin@1.2.3.4:/bar/baz"], "1.2.3.4", id="scp-style-address"),
        pytest.param(["foo", "444.555.101.101", "baz"], None, id="invalid-address"),
    ],
)
def test_find_address_in_tokens(tokens: list[str], expected: str | None) -> None:
    """Verify behavior of find_address_in_tokens function."""
    assert find_address_in_tokens(tokens) == expected
