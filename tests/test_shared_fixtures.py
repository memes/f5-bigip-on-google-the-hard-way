"""Test cases to validate the shared fixtures defined in conftest.py."""

import pathlib
import re
import tempfile
from collections.abc import Callable, Iterator

import pytest


def test_project_id(project_id: str) -> None:
    """Verify project_id fixture."""
    assert project_id
    assert re.match(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$", project_id)


def test_iam_member(iam_member: str) -> None:
    """Verify iam_member fixture."""
    assert iam_member
    assert re.match(
        r"^user:.+@(?:[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]\.)+[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]$",
        iam_member,
    )


def test_region(region: str) -> None:
    """Verify region fixture."""
    assert region
    assert re.match(r"^[a-z]{2,}-[a-z]{2,}[1-9][0-9]*$", region)


def test_zone(region: str, zone: str) -> None:
    """Verify zone fixture."""
    assert region
    assert zone
    assert re.match(r"^[a-z]{2,}-[a-z]{2,}[1-9][0-9]*-[a-z]$", zone)
    assert zone.startswith(region)


def test_ssh_private_key(ssh_private_key: bytes) -> None:
    """Verify ssh_private_key fixture."""
    assert ssh_private_key
    assert ssh_private_key.startswith(b"-----BEGIN OPENSSH PRIVATE KEY-----")


def test_ssh_public_key(ssh_public_key: bytes) -> None:
    """Verify ssh_private_key fixture."""
    assert ssh_public_key
    assert ssh_public_key.startswith((b"ssh-ed25519 ", b"ssh-rsa "))


def test_ssh_private_key_file(ssh_private_key_file: pathlib.Path) -> None:
    """Verify ssh_private_key_file fixture."""
    assert ssh_private_key_file
    assert ssh_private_key_file.exists()
    assert ssh_private_key_file.read_bytes().startswith(b"-----BEGIN OPENSSH PRIVATE KEY-----")


def test_ssh_public_key_file(ssh_public_key_file: pathlib.Path) -> None:
    """Verify ssh_private_key_file fixture."""
    assert ssh_public_key_file
    assert ssh_public_key_file.exists()
    assert ssh_public_key_file.read_bytes().startswith((b"ssh-ed25519 ", b"ssh-rsa "))


def test_ssh_config(ssh_config: pathlib.Path) -> None:
    """Verify ssh_config fixture."""
    assert ssh_config
    assert ssh_config.exists()


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        pytest.param([], [], id="empty"),
        pytest.param([""], [""], id="blank"),
        pytest.param(["foo", "bar", "baz"], ["foo", "bar", "baz"], id="foo-no-matches"),
        pytest.param(
            [
                "foo",
                "--project",
                "my-project",
                "create",
            ],
            [
                "foo",
                "--project",
                "my-project",
                "create",
            ],
            id="foo-project-sep",
        ),
        pytest.param(
            [
                "foo",
                "--project=my-project",
                "create",
            ],
            [
                "foo",
                "--project=my-project",
                "create",
            ],
            id="foo-project-joined",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--project",
                "my-project",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--project",
                "{project_id}",
                "foo",
            ],
            id="gcloud-project-sep",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--project=my-project",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--project={project_id}",
                "foo",
            ],
            id="gcloud-project-joined",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--project-x",
                "my-project",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--project-x",
                "my-project",
                "foo",
            ],
            id="gcloud-project-x-sep",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--project-x=my-project",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--project-x=my-project",
                "foo",
            ],
            id="gcloud-project-x-joined",
        ),
        # NOTE: Only testing positive matches below
        pytest.param(
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--region",
                "my-region",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--region",
                "{region}",
                "foo",
            ],
            id="gcloud-region-sep",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--region=my-region",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--region={region}",
                "foo",
            ],
            id="gcloud-region-joined",
        ),
        pytest.param(
            [
                "gcloud",
                "iap",
                "tcp",
                "dest-groups",
                "add-iam-policy-binding",
                "--project",
                "my-project",
                "--region",
                "my-region",
                "--member",
                "group:foo@bar.com",
                "--dest-group",
                "foo",
            ],
            [
                "gcloud",
                "iap",
                "tcp",
                "dest-groups",
                "add-iam-policy-binding",
                "--project",
                "{project_id}",
                "--region",
                "{region}",
                "--member",
                "{iam_member}",
                "--dest-group",
                "foo",
            ],
            id="gcloud-dest-group-sep",
        ),
        pytest.param(
            [
                "gcloud",
                "iap",
                "tcp",
                "dest-groups",
                "add-iam-policy-binding",
                "--project=my-project",
                "--region=my-region",
                "--member=group:foo@bar.com",
                "--dest-group=foo",
            ],
            [
                "gcloud",
                "iap",
                "tcp",
                "dest-groups",
                "add-iam-policy-binding",
                "--project={project_id}",
                "--region={region}",
                "--member={iam_member}",
                "--dest-group=foo",
            ],
            id="gcloud-dest-group-joined",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--zone",
                "my-zone",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--zone",
                "{zone}",
                "foo",
            ],
            id="gcloud-zone-sep",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--zone=my-zone",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--zone={zone}",
                "foo",
            ],
            id="gcloud-zone-joined",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--service-account",
                "my-service-account@my-project.foo.bar",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--service-account",
                "{service_account}",
                "foo",
            ],
            id="gcloud-sa-sep",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--service-account=my-service-account@my-project.foo.bar",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "instances",
                "create",
                "--service-account={service_account}",
                "foo",
            ],
            id="gcloud-sa-joined",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--source-service-accounts",
                "my-service-account@my-project.foo.bar",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--source-service-accounts",
                "{service_account}",
                "foo",
            ],
            id="gcloud-src-sa-sep",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--source-service-accounts=my-service-account@my-project.foo.bar",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--source-service-accounts={service_account}",
                "foo",
            ],
            id="gcloud-src-sa-joined",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--source-service-accounts",
                "my-service-account@my-project.foo.bar,foo@foo.bar",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--source-service-accounts",
                "{service_account}",
                "foo",
            ],
            id="gcloud-multi-src-sa-sep",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--source-service-accounts=my-service-account@my-project.foo.bar,foo@foo.bar",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--source-service-accounts={service_account}",
                "foo",
            ],
            id="gcloud-src-sa-multi-joined",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--target-service-accounts",
                "my-service-account@my-project.foo.bar",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--target-service-accounts",
                "{service_account}",
                "foo",
            ],
            id="gcloud-tgt-sa-sep",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--target-service-accounts=my-service-account@my-project.foo.bar",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--target-service-accounts={service_account}",
                "foo",
            ],
            id="gcloud-tgt-sa-joined",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--target-service-accounts",
                "my-service-account@my-project.foo.bar,foo@foo.bar",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--target-service-accounts",
                "{service_account}",
                "foo",
            ],
            id="gcloud-tgt-sa-multi-sep",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--target-service-accounts=my-service-account@my-project.foo.bar,foo@foo.bar",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--target-service-accounts={service_account}",
                "foo",
            ],
            id="gcloud-tgt-sa-multi-joined",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--source-service-accounts",
                "my-service-account@my-project.foo.bar,foo@foo.bar",
                "--target-service-accounts",
                "my-service-account@my-project.foo.bar,foo@foo.bar",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--source-service-accounts",
                "{service_account}",
                "--target-service-accounts",
                "{service_account}",
                "foo",
            ],
            id="gcloud-src-tgt-sa-multi-sep",
        ),
        pytest.param(
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--source-service-accounts=my-service-account@my-project.foo.bar,foo@foo.bar",
                "--target-service-accounts=my-service-account@my-project.foo.bar,foo@foo.bar",
                "foo",
            ],
            [
                "gcloud",
                "compute",
                "firewall-rules",
                "create",
                "--source-service-accounts={service_account}",
                "--target-service-accounts={service_account}",
                "foo",
            ],
            id="gcloud-src-tgt-sa-multi-joined",
        ),
        pytest.param(
            [
                "ssh",
                "admin@10.100.0.101",
                "echo",
                "success",
            ],
            [
                "ssh",
                "-F",
                "{ssh_config!s}",
                "admin@10.100.0.101",
                "echo",
                "success",
            ],
            id="ssh-no-cfg",
        ),
        pytest.param(
            [
                "ssh",
                "admin@10.100.0.101",
                "-F",
                "~/.ssh/config",
                "echo",
                "success",
            ],
            [
                "ssh",
                "admin@10.100.0.101",
                "-F",
                "{ssh_config!s}",
                "echo",
                "success",
            ],
            id="ssh-cfg",
        ),
        pytest.param(
            [
                "scp",
                "foo",
                "admin@10.100.0.101:/config/cloud/",
            ],
            [
                "scp",
                "-F",
                "{ssh_config!s}",
                "foo",
                "admin@10.100.0.101:/config/cloud/",
            ],
            id="scp-no-cfg",
        ),
        pytest.param(
            [
                "scp",
                "-F",
                "~/.ssh/config",
                "foo",
                "admin@10.100.0.101:/config/cloud/",
            ],
            [
                "scp",
                "-F",
                "{ssh_config!s}",
                "foo",
                "admin@10.100.0.101:/config/cloud/",
            ],
            id="scp-cfg",
        ),
    ],
)
def test_replace_arguments(
    tokens: list[str],
    expected: list[str],
    replace_arguments: Callable[[list[str]], list[str]],
    project_id: str,  # noqa: ARG001 # Used via locals()
    iam_member: str,  # noqa: ARG001 # Used via locals()
    region: str,  # noqa: ARG001 # Used via locals()
    zone: str,  # noqa: ARG001 # Used via locals()
    service_account: str,  # noqa: ARG001 # Used via locals()
    ssh_config: pathlib.Path,  # noqa: ARG001 # Used via locals()
) -> None:
    """Verify the replace_arguments fixture works as expected."""
    assert replace_arguments(tokens) == [s.format(**locals()) for s in expected]


@pytest.mark.parametrize(
    ("data", "env", "expected"),
    [
        pytest.param("", None, [], id="empty"),
        pytest.param(
            """
# Header

```shell
foo bar baz
```
""",
            None,
            [(["foo", "bar", "baz"], None)],
            id="command-no-env-no-heredoc",
        ),
        pytest.param(
            """
# Header

```shell
foo bar baz <<EOF
This is input
EOF
```
""",
            None,
            [(["foo", "bar", "baz"], b"This is input")],
            id="command-no-env-heredoc",
        ),
        pytest.param(
            """
# Header

```shell
foo ${bar} baz <<EOF
This is input ${bar}
EOF
```
""",
            {"bar": "xxx"},
            [(["foo", "xxx", "baz"], b"This is input xxx")],
            id="command-env-heredoc-bracket-var",
        ),
        pytest.param(
            """
# Header

```shell
foo ${bar} baz <<EOF
This is input ${bar}
EOF
```
""",
            None,
            [(["foo", "UNKNOWN_VARIABLE", "baz"], b"This is input UNKNOWN_VARIABLE")],
            id="command-no-env-heredoc-bracket-var",
        ),
    ],
)
def test_shell_example_extractor(
    data: str,
    env: dict[str, str] | None,
    expected: list[tuple[list[str], bytes | None]],
    shell_example_extractor: Callable[[pathlib.Path, dict[str, str] | None], Iterator[tuple[list[str], bytes | None]]],
) -> None:
    """Verify the shell_example_extractor fixture works as expected."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix="source",
        suffix=".md",
        encoding="utf-8",
        delete_on_close=False,
        delete=True,
    ) as source_file:
        source_file.write(data)
        source_file.close()
        assert list(shell_example_extractor(pathlib.Path(source_file.name), env)) == expected
