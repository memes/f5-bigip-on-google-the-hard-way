"""Common fixtures for use in test cases."""

import contextlib
import os
import pathlib
import re
import subprocess
import tempfile
import time
from collections import Counter
from collections.abc import Callable, Generator, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import cryptography.hazmat.primitives.serialization
import google.auth
import google.auth.credentials
import google.auth.transport
import google.auth.transport.requests
import google.oauth2
import google.oauth2.credentials
import google.oauth2.id_token
import mistune
import pytest
import testinfra
from cryptography.hazmat.primitives.asymmetric import ed25519
from google.api_core import exceptions
from google.cloud import compute_v1, iam_admin_v1, iap_v1
from google.iam.v1 import iam_policy_pb2, policy_pb2
from paramiko.ssh_exception import SSHException
from testinfra.host import Host

from tests import (
    EXPECTED_BIG_IP_ADDRESSES,
    EXPECTED_BIG_IP_VM_NAMES,
    EXPECTED_FIREWALL_RULES,
    EXPECTED_IAP_DEST_GROUPS,
    EXPECTED_NETWORKS,
    EXPECTED_SUBNETS,
    env_substituter,
    find_address_in_tokens,
    find_shell_block_code,
    handle_operation,
    split_heredoc,
    tokenize_shell,
)

DEFAULT_REGION = "us-west1"
DEFAULT_NAME = "bigip-the-hard-way"
DEFAULT_WAIT_FOR_TIMEOUT = timedelta(seconds=600)


@pytest.fixture(scope="session")
def ignore_command_failure() -> bool:
    """Determine if command execution failures should be ignored during tests."""
    return os.getenv("TEST_IGNORE_COMMAND_FAILURE", "False").lower() in ["true", "t", "yes", "y", "1"]


@pytest.fixture(scope="session")
def skip_destroy_phase() -> bool:
    """Determine if resource destroy phase should be skipped for successful fixtures."""
    return os.getenv("TEST_SKIP_DESTROY_PHASE", "False").lower() in ["true", "t", "yes", "y", "1"]


@pytest.fixture(scope="session")
def skip_command_execution() -> bool:
    """Determine if command execution should be skipped for rapid testing."""
    return os.getenv("TEST_SKIP_COMMAND_EXECUTION", "False").lower() in ["true", "t", "yes", "y", "1"]


@pytest.fixture(scope="session")
def project_id() -> str:
    """Return the project id to use for tests.

    Preference will be given to the environment variables TEST_GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_PROJECT followed by
    the default project identifier associated with local ADC credentials.
    """
    project_id = os.getenv("TEST_GOOGLE_CLOUD_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    if project_id:
        project_id = project_id.strip()
    if not project_id:
        _, project_id = google.auth.default()
    assert project_id
    return project_id


@pytest.fixture(scope="session")
def iam_member() -> str:
    """Return the IAM account to use for tests in the form of an IAM membership, e.g. user:foo.bar@baz.com.

    Preference will be given to the environment variables TEST_GOOGLE_IAM_ACCOUNT followed by the account associated
    with local ADC credentials.
    """
    iam_member = os.getenv("TEST_GOOGLE_IAM_ACCOUNT")
    if iam_member:
        iam_member = iam_member.strip()
    if not iam_member:
        credentials, _ = google.auth.default()
        assert credentials
        # Only handling user accounts for now
        assert isinstance(credentials, google.oauth2.credentials.Credentials)
        credentials = cast("google.oauth2.credentials.Credentials", credentials)
        if credentials.token_state != google.auth.credentials.TokenState.FRESH:
            credentials.refresh(google.auth.transport.requests.Request())
        info = google.oauth2.id_token.verify_oauth2_token(
            credentials.id_token,
            google.auth.transport.requests.Request(),
        )
        assert info
        assert isinstance(info, Mapping)
        iam_member = info["email"]
    return f"user:{iam_member}"


@pytest.fixture(scope="session")
def service_account(
    project_id: str,
) -> str:
    """Return the expected service account identifier."""
    return f"bigip-the-hard-way@{project_id}.iam.gserviceaccount.com"


@pytest.fixture(scope="session")
def region() -> str:
    """Return the Compute Engine region to use for tests.

    Preference will be given to the environment variable TEST_GOOGLE_REGION with fallback to the default value of
    'us-west1'.
    """
    region = os.getenv("TEST_GOOGLE_REGION", DEFAULT_REGION)
    if region:
        region = region.strip()
    if not region:
        region = DEFAULT_REGION
    assert region
    return region


@pytest.fixture(scope="session")
def region_zones_client() -> compute_v1.RegionZonesClient:
    """Return a reusable Compute Engine v1 RegionZones API client."""
    return compute_v1.RegionZonesClient()


@pytest.fixture(scope="session")
def zone(
    project_id: str,
    region: str,
    region_zones_client: compute_v1.RegionZonesClient,
) -> str:
    """Return the first zone in region."""
    assert region_zones_client
    return next(
        zone.name
        for zone in region_zones_client.list(
            request=compute_v1.ListRegionZonesRequest(
                region=region,
                project=project_id,
            ),
        )
    )


@pytest.fixture(scope="session")
def ssh_key_pair() -> tuple[bytes, bytes]:
    """Create an ed25519 SSH key pair if an existing key pair is not provided."""
    private_key_file = os.getenv("TEST_SSH_PRIVATE_KEY_FILE")
    public_key_file = os.getenv("TEST_SSH_PUBLIC_KEY_FILE")
    if private_key_file and public_key_file:
        private_key = pathlib.Path(private_key_file).expanduser().read_bytes()
        public_key = pathlib.Path(public_key_file).expanduser().read_bytes()
        return (private_key, public_key)

    key = ed25519.Ed25519PrivateKey.generate()
    assert key
    private_key = key.private_bytes(
        encoding=cryptography.hazmat.primitives.serialization.Encoding.PEM,
        format=cryptography.hazmat.primitives.serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=cryptography.hazmat.primitives.serialization.NoEncryption(),
    )
    assert private_key
    public_key = key.public_key().public_bytes(
        encoding=cryptography.hazmat.primitives.serialization.Encoding.OpenSSH,
        format=cryptography.hazmat.primitives.serialization.PublicFormat.OpenSSH,
    )
    assert public_key
    return (private_key, public_key)


@pytest.fixture(scope="session")
def ssh_private_key(ssh_key_pair: tuple[bytes, bytes]) -> bytes:
    """Return the SSH private key as bytes."""
    return ssh_key_pair[0]


@pytest.fixture(scope="session")
def ssh_public_key(ssh_key_pair: tuple[bytes, bytes]) -> bytes:
    """Return the SSH public key as bytes."""
    return ssh_key_pair[1]


@pytest.fixture(scope="session")
def ssh_private_key_file(ssh_private_key: bytes) -> Generator[pathlib.Path]:
    """Create an SSH private key file that will be removed during context exit."""
    assert ssh_private_key
    with tempfile.NamedTemporaryFile(
        mode="w+b",
        prefix="id_ed25519",
        suffix=None,
        delete_on_close=False,
        delete=True,
    ) as private_key:
        private_key.write(ssh_private_key)
        private_key.close()
        yield pathlib.Path(private_key.name)


@pytest.fixture(scope="session")
def ssh_public_key_file(ssh_public_key: bytes) -> Generator[pathlib.Path]:
    """Create an SSH public key file that will be removed during context exit."""
    assert ssh_public_key
    with tempfile.NamedTemporaryFile(
        mode="w+b",
        prefix="id_ed25519",
        suffix=".pub",
        delete_on_close=False,
        delete=True,
    ) as public_key:
        public_key.write(ssh_public_key)
        public_key.close()
        yield pathlib.Path(public_key.name)


@pytest.fixture(scope="session")
def ssh_config(
    ssh_private_key_file: pathlib.Path,
    project_id: str,
    region: str,
) -> Generator[pathlib.Path]:
    """Create an SSH config file to use for key authentication that will be removed during context exit."""
    assert ssh_private_key_file
    data = f"""
Host 10.100.0.101 10.100.0.102
\tUser admin
\tProxyCommand gcloud compute start-iap-tunnel %h %p --listen-on-stdin --dest-group bigip-the-hard-way --network bigip-the-hard-way-mgt --region {region} --project {project_id}

Host 10.0.0.101 10.0.0.102
\tUser admin
\tProxyCommand gcloud compute start-iap-tunnel %h %p --listen-on-stdin --dest-group bigip-the-hard-way --network bigip-the-hard-way-ext --region {region} --project {project_id}

Host *
\tCheckHostIP no
\tIdentitiesOnly yes
\tIdentityFile {ssh_private_key_file.as_posix()}
\tPasswordAuthentication no
\tPreferredAuthentications publickey
\tUserKnownHostsFile /dev/null
\tStrictHostKeyChecking no
"""  # noqa: E501
    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix="ssh_config",
        suffix=None,
        encoding="utf-8",
        delete_on_close=False,
        delete=True,
    ) as config_file:
        config_file.write(data)
        config_file.close()
        yield pathlib.Path(config_file.name)


@pytest.fixture(scope="session")
def instances_client() -> compute_v1.InstancesClient:
    """Return a reusable Compute Engine v1 Instances API client."""
    return compute_v1.InstancesClient()


@pytest.fixture(scope="session")
def instance_retriever(
    instances_client: compute_v1.InstancesClient,
    project_id: str,
    zone: str,
) -> Callable[[str], compute_v1.Instance]:
    """Return a function that will return the Instance object for the named VM, or raise a NotFound exception."""

    def _retriever(name: str) -> compute_v1.Instance:
        return instances_client.get(
            request=compute_v1.GetInstanceRequest(
                instance=name,
                project=project_id,
                zone=zone,
            ),
        )

    return _retriever


@pytest.fixture(scope="session")
def instance_deleter(
    instances_client: compute_v1.InstancesClient,
    project_id: str,
    zone: str,
) -> Callable[[str], None]:
    """Return a function that delete the named VM, or raise a NotFound exception."""

    def _deleter(name: str) -> None:
        handle_operation(
            instances_client.delete(
                request=compute_v1.DeleteInstanceRequest(
                    instance=name,
                    project=project_id,
                    zone=zone,
                ),
            ),
        )

    return _deleter


@pytest.fixture(scope="session")
def get_host(
    ssh_config: pathlib.Path,
) -> Callable[[str], Host]:
    """Return a function that will create a testinfra Host for an IP address, with custom SSH configuration."""

    def _builder(address: str) -> Host:
        # NOTE: Native paramiko fails to close fd's on error, leading to false positive failures and termination of
        # tests. Using wrapped ssh command works correctly.
        return testinfra.get_host(hostspec=f"ssh://admin@{address}", ssh_config=ssh_config.as_posix())

    return _builder


@pytest.fixture(scope="session")
def bigip_is_ready(
    get_host: Callable[[str], testinfra.host.Host],
) -> Callable[[str], None]:
    """Return a function that can verify a BIG-IP is ready for use within a given timeout."""
    is_config_ready = re.compile(r"^config\s+yes$", re.MULTILINE)
    is_license_ready = re.compile(r"^license\s+yes$", re.MULTILINE)
    is_provision_ready = re.compile(r"^provision\s+yes$", re.MULTILINE)

    def _is_ready(host: testinfra.host.Host) -> bool:
        try:
            result = host.run("tmsh show /sys ready")
            if result.failed:
                result = host.run("show /sys ready")
            if result.failed:
                return False
            return (
                is_config_ready.search(result.stdout) is not None
                and is_license_ready.search(result.stdout) is not None
                and is_provision_ready.search(result.stdout) is not None
            )
        except (RuntimeError, SSHException, TimeoutError):
            return False

    def _waiter(address: str, timeout: timedelta | None = None) -> None:
        host = get_host(address)
        timeout_ts = datetime.now(UTC) + (timeout if timeout is not None else DEFAULT_WAIT_FOR_TIMEOUT)
        while not _is_ready(host):
            if datetime.now(UTC) > timeout_ts:
                raise TimeoutError
            time.sleep(30)

    return _waiter


@pytest.fixture(scope="session")
def bigip_active_standby_asserter(
    get_host: Callable[[str], testinfra.host.Host],
) -> Callable[[list[str], timedelta | None], None]:
    """Return an asserter function that verifies one BIG-IP is 'active' and all others are 'standby'."""

    def _failover_status(host: testinfra.host.Host) -> str | None:
        try:
            result = host.run("tmsh show /cm failover-status")
            if result.failed:
                result = host.run("show /cm failover-status")
            if result.failed:
                return None
            status = re.search(r"^Status\s+(\w+)", result.stdout, flags=re.MULTILINE)
            if not status:
                return None
            return status.group(1).lower()
        except (RuntimeError, SSHException, TimeoutError):
            return None

    def _wait_for_status(address: str, timeout: timedelta | None = None) -> str:
        host = get_host(address)
        timeout_ts = datetime.now(UTC) + (timeout if timeout is not None else DEFAULT_WAIT_FOR_TIMEOUT)
        result = _failover_status(host)
        while result is None:
            if datetime.now(UTC) > timeout_ts:
                raise TimeoutError
            time.sleep(30)
            result = _failover_status(host)
        return result

    def _asserter(addresses: list[str], timeout: timedelta | None = None) -> None:
        states = Counter([_wait_for_status(address, timeout) for address in addresses])
        assert states["active"] == 1
        assert states["standby"] == len(addresses) - 1
        assert [key for key in states if key not in ["active", "standby"]] == []

    return _asserter


@pytest.fixture(scope="session")
def replace_arguments(  # noqa: C901
    project_id: str,
    iam_member: str,
    region: str,
    zone: str,
    service_account: str,
    ssh_config: pathlib.Path,
) -> Callable[[list[str]], list[str]]:
    """Replace arguments in the tokenized command with values suitable for the test environment."""

    def _replace(tokens: list[str], argument: str, value: str) -> None:
        """Replace a given property argument with the supplied value in a list of arguments."""
        with contextlib.suppress(ValueError):
            index = tokens.index(f"--{argument}")
            tokens[index + 1] = value
        with contextlib.suppress(StopIteration):
            index = next(idx for idx, value in enumerate(tokens) if value.startswith(f"--{argument}="))
            tokens[index] = f"--{argument}={value}"

    def _mutate_gcloud(original: list[str]) -> list[str]:
        """Return a copy of the gcloud arguments replaced with the session values."""
        mutated = original.copy()
        if project_id:
            _replace(mutated, "project", project_id)
        if iam_member:
            _replace(mutated, "member", iam_member)
        if region:
            _replace(mutated, "region", region)
        if zone:
            _replace(mutated, "zone", zone)
        if service_account:
            _replace(mutated, "service-account", service_account)
            _replace(mutated, "source-service-accounts", service_account)
            _replace(mutated, "target-service-accounts", service_account)
            with contextlib.suppress(ValueError):
                index = mutated.index("bigip-the-hard-way@my-project.iam.gserviceaccount.com")
                mutated[index] = service_account
        return mutated

    def _mutate_ssh(original: list[str]) -> list[str]:
        """Return a copy of the ssh or scp arguments replaced with the session values."""
        mutated = original.copy()
        try:
            index = mutated.index("-F")
            mutated[index + 1] = ssh_config.as_posix()
        except ValueError:
            mutated = [mutated[0], "-F", ssh_config.as_posix(), *mutated[1:]]
        return mutated

    def _mutator(original: list[str]) -> list[str]:
        """Return a copy of the arguments list with overridden arguments."""
        if original and original[0] == "gcloud":
            return _mutate_gcloud(original)
        if original and original[0] in ["ssh", "scp"] and ssh_config:
            return _mutate_ssh(original)

        return original.copy()

    return _mutator


@pytest.fixture(scope="session")
def shell_example_extractor(
    replace_arguments: Callable[[list[str]], list[str]],
) -> Callable[[pathlib.Path, dict[str, str] | None], Generator[tuple[list[str], bytes | None]]]:
    """Return a Generator function that will extract fenced code blocks from markdown and normalize for testing."""
    parser = mistune.create_markdown(renderer="ast", escape=False)

    def _builder(doc: pathlib.Path, env: dict[str, str] | None = None) -> Generator[tuple[list[str], bytes | None]]:
        assert doc
        content = doc.read_text(encoding="utf-8")
        blocks = cast("list[dict[str, Any]]", parser(content))
        env_replacer = env_substituter(env=env)
        for block in blocks:
            yield from [
                (replace_arguments(tokenize_shell(command)), stdin)
                for command, stdin in [
                    split_heredoc(env_replacer(code_block))
                    for code_block in find_shell_block_code(root=block)
                    if not code_block.startswith(
                        (
                            # Ignore export lines as we're not running in a shell
                            "export ",
                            # Ignore tail-serial-port-output commands as they will block progress or result in an error
                            "gcloud compute instances tail-serial-port-output ",
                        ),
                    )
                ]
            ]

    return _builder


@pytest.fixture(scope="session")
def assert_resources_are_gone(
    service_account: str,
    network_retriever: Callable[[str], None],
    subnetwork_retriever: Callable[[str], None],
    service_account_retriever: Callable[[], None],
    firewall_retriever: Callable[[str], None],
    address_retriever: Callable[[str], None],
    instance_retriever: Callable[[str], None],
    iap_dest_group_retriever: Callable[[str], None],
) -> Callable[[], None]:
    """Return a function that will assert all resources that were expected to be created cannot be found."""

    def _all_gone() -> None:
        for name in EXPECTED_BIG_IP_VM_NAMES:
            with pytest.raises(expected_exception=exceptions.NotFound, match=name):
                instance_retriever(name)
        for name in EXPECTED_BIG_IP_ADDRESSES:
            with pytest.raises(expected_exception=exceptions.NotFound, match=name):
                address_retriever(name)
        for name in EXPECTED_FIREWALL_RULES:
            with pytest.raises(expected_exception=exceptions.NotFound, match=name):
                firewall_retriever(name)
        with pytest.raises(expected_exception=exceptions.NotFound, match=service_account):
            service_account_retriever()
        for name in EXPECTED_SUBNETS:
            with pytest.raises(expected_exception=exceptions.NotFound, match=name):
                subnetwork_retriever(name)
        for name in EXPECTED_NETWORKS:
            with pytest.raises(expected_exception=exceptions.NotFound, match=name):
                network_retriever(name)
        for name in EXPECTED_IAP_DEST_GROUPS:
            with pytest.raises(expected_exception=exceptions.NotFound):
                iap_dest_group_retriever(name)

    return _all_gone


@pytest.fixture(scope="session")
def resource_cleanup(
    network_deleter: Callable[[str], None],
    subnetwork_deleter: Callable[[str], None],
    service_account_deleter: Callable[[], None],
    firewall_deleter: Callable[[str], None],
    address_deleter: Callable[[str], None],
    instance_deleter: Callable[[str], None],
    iap_dest_group_deleter: Callable[[str], None],
    *,
    skip_destroy_phase: bool,
) -> Generator[bool]:
    """Perform resource cleanup after yield."""
    yield True
    if not skip_destroy_phase:
        for name in EXPECTED_BIG_IP_VM_NAMES:
            with contextlib.suppress(exceptions.NotFound):
                instance_deleter(name)
        for name in EXPECTED_BIG_IP_ADDRESSES:
            with contextlib.suppress(exceptions.NotFound):
                address_deleter(name)
        for name in EXPECTED_FIREWALL_RULES:
            with contextlib.suppress(exceptions.NotFound):
                firewall_deleter(name)
        with contextlib.suppress(exceptions.NotFound):
            service_account_deleter()
        for name in EXPECTED_SUBNETS:
            with contextlib.suppress(exceptions.NotFound):
                subnetwork_deleter(name)
        for name in EXPECTED_NETWORKS:
            with contextlib.suppress(exceptions.NotFound):
                network_deleter(name)
        for name in EXPECTED_IAP_DEST_GROUPS:
            with contextlib.suppress(exceptions.NotFound):
                iap_dest_group_deleter(name)


@pytest.fixture(scope="session")
def execute_shell_commands(
    shell_example_extractor: Callable[..., Generator[tuple[list[str], bytes | None]]],
    bigip_is_ready: Callable[[str], testinfra.host.Host],
    assert_resources_are_gone: Callable[[], None],
    *,
    resource_cleanup: bool,
    ignore_command_failure: bool,
    skip_destroy_phase: bool,
    skip_command_execution: bool,
) -> Callable[[list[pathlib.Path] | None, list[pathlib.Path] | None, dict[str, str] | None], Generator[bool]]:
    """Return a function that will execute individual shell commands from markdown files, with clean up after use."""

    def _executor(
        create_paths: list[pathlib.Path] | None = None,
        destroy_paths: list[pathlib.Path] | None = None,
        env: dict[str, str] | None = None,
    ) -> Generator[bool]:
        if not skip_command_execution and create_paths:
            for command, command_input in [
                (command, command_input)
                for source in create_paths
                for (command, command_input) in shell_example_extractor(
                    doc=source,
                    env=env,
                )
            ]:
                # Before executing an SSH command, give the BIG-IP time to come online
                if not ignore_command_failure and command[0] in ["ssh", "scp"]:
                    address = find_address_in_tokens(command)
                    if address:
                        bigip_is_ready(address)
                subprocess.run(
                    args=command,
                    check=not ignore_command_failure,
                    capture_output=True,
                    input=command_input,
                )
        yield True
        if not skip_destroy_phase and destroy_paths:
            for command, command_input in [
                (command, command_input)
                for source in destroy_paths
                for (command, command_input) in shell_example_extractor(
                    doc=source,
                    env=env,
                )
            ]:
                check = (
                    False
                    if command[:5]
                    == [
                        "gcloud",
                        "compute",
                        "firewall-rules",
                        "delete",
                        "bigip-the-hard-way-allow-admin-ext",
                    ]
                    else not ignore_command_failure
                )
                subprocess.run(
                    args=command,
                    check=check,
                    capture_output=True,
                    input=command_input,
                )
            assert_resources_are_gone()

    assert resource_cleanup
    return _executor


@pytest.fixture(scope="session")
def networks_client() -> compute_v1.NetworksClient:
    """Return a reusable Compute Engine v1 Networks API client."""
    return compute_v1.NetworksClient()


@pytest.fixture(scope="session")
def network_retriever(
    networks_client: compute_v1.NetworksClient,
    project_id: str,
) -> Callable[[str], compute_v1.Network]:
    """Return a function that will return the Network object for the named network, or raise a NotFound exception."""

    def _retriever(name: str) -> compute_v1.Network:
        return networks_client.get(
            request=compute_v1.GetNetworkRequest(
                network=name,
                project=project_id,
            ),
        )

    return _retriever


@pytest.fixture(scope="session")
def network_deleter(
    networks_client: compute_v1.NetworksClient,
    project_id: str,
) -> Callable[[str], None]:
    """Return a function that delete the named network, or raise a NotFound exception."""

    def _deleter(name: str) -> None:
        handle_operation(
            networks_client.delete(
                request=compute_v1.DeleteNetworkRequest(
                    network=name,
                    project=project_id,
                ),
            ),
        )

    return _deleter


@pytest.fixture(scope="session")
def subnetworks_client() -> compute_v1.SubnetworksClient:
    """Return a reusable Compute Engine v1 Subnetworks API client."""
    return compute_v1.SubnetworksClient()


@pytest.fixture(scope="session")
def subnetwork_retriever(
    subnetworks_client: compute_v1.SubnetworksClient,
    project_id: str,
    region: str,
) -> Callable[[str], compute_v1.Subnetwork]:
    """Return a function that will return the Subnetwork object for the named network, or raise a NotFound exception."""

    def _retriever(name: str) -> compute_v1.Subnetwork:
        return subnetworks_client.get(
            request=compute_v1.GetSubnetworkRequest(
                subnetwork=name,
                project=project_id,
                region=region,
            ),
        )

    return _retriever


@pytest.fixture(scope="session")
def subnetwork_deleter(
    subnetworks_client: compute_v1.SubnetworksClient,
    project_id: str,
    region: str,
) -> Callable[[str], None]:
    """Return a function that delete the named subnetwork, or raise a NotFound exception."""

    def _deleter(name: str) -> None:
        handle_operation(
            subnetworks_client.delete(
                request=compute_v1.DeleteSubnetworkRequest(
                    subnetwork=name,
                    project=project_id,
                    region=region,
                ),
            ),
        )

    return _deleter


@pytest.fixture(scope="session")
def iam_client() -> iam_admin_v1.IAMClient:
    """Return a reusable IAM Admin v1 API client."""
    return iam_admin_v1.IAMClient()


@pytest.fixture(scope="session")
def service_account_retriever(
    iam_client: iam_admin_v1.IAMClient,
    project_id: str,
    service_account: str,
) -> Callable[[], iam_admin_v1.ServiceAccount]:
    """Return a function that will return the ServiceAccount object for tests, or raise a NotFound exception."""

    def _retriever() -> iam_admin_v1.ServiceAccount:
        return iam_client.get_service_account(
            request=iam_admin_v1.GetServiceAccountRequest(
                name=f"projects/{project_id}/serviceAccounts/{service_account}",
            ),
        )

    return _retriever


@pytest.fixture(scope="session")
def service_account_deleter(
    iam_client: iam_admin_v1.IAMClient,
    project_id: str,
    service_account: str,
) -> Callable[[], None]:
    """Return a function that delete the test service account, or raise a NotFound exception."""

    def _deleter() -> None:
        iam_client.delete_service_account(
            request=iam_admin_v1.DeleteServiceAccountRequest(
                name=f"projects/{project_id}/serviceAccounts/{service_account}",
            ),
        )

    return _deleter


@pytest.fixture(scope="session")
def firewalls_client() -> compute_v1.FirewallsClient:
    """Return a reusable Compute Engine v1 Firewalls API client."""
    return compute_v1.FirewallsClient()


@pytest.fixture(scope="session")
def firewall_retriever(
    firewalls_client: compute_v1.FirewallsClient,
    project_id: str,
) -> Callable[[str], compute_v1.Firewall]:
    """Return a function that will return the Firewall object for the named firewall, or raise a NotFound exception."""

    def _retriever(name: str) -> compute_v1.Firewall:
        return firewalls_client.get(
            request=compute_v1.GetFirewallRequest(
                firewall=name,
                project=project_id,
            ),
        )

    return _retriever


@pytest.fixture(scope="session")
def firewall_deleter(
    firewalls_client: compute_v1.FirewallsClient,
    project_id: str,
) -> Callable[[str], None]:
    """Return a function that delete the named firewall, or raise a NotFound exception."""

    def _deleter(name: str) -> None:
        handle_operation(
            firewalls_client.delete(
                request=compute_v1.DeleteFirewallRequest(
                    firewall=name,
                    project=project_id,
                ),
            ),
        )

    return _deleter


@pytest.fixture(scope="session")
def addresses_client() -> compute_v1.AddressesClient:
    """Return a reusable Compute Engine v1 Addresses API client."""
    return compute_v1.AddressesClient()


@pytest.fixture(scope="session")
def address_retriever(
    addresses_client: compute_v1.AddressesClient,
    project_id: str,
    region: str,
) -> Callable[[str], compute_v1.Address]:
    """Return a function that will return the Address object for the named address, or raise a NotFound exception."""

    def _retriever(name: str) -> compute_v1.Address:
        return addresses_client.get(
            request=compute_v1.GetAddressRequest(
                address=name,
                project=project_id,
                region=region,
            ),
        )

    return _retriever


@pytest.fixture(scope="session")
def address_deleter(
    addresses_client: compute_v1.AddressesClient,
    project_id: str,
    region: str,
) -> Callable[[str], None]:
    """Return a function that delete the named reserved address, or raise a NotFound exception."""

    def _deleter(name: str) -> None:
        handle_operation(
            addresses_client.delete(
                request=compute_v1.DeleteAddressRequest(
                    address=name,
                    project=project_id,
                    region=region,
                ),
            ),
        )

    return _deleter


@pytest.fixture(scope="session")
def iap_admin_client() -> iap_v1.IdentityAwareProxyAdminServiceClient:
    """Return a reusable IAP v1 Admin Service API client."""
    return iap_v1.IdentityAwareProxyAdminServiceClient()


@pytest.fixture(scope="session")
def iap_dest_group_retriever(
    iap_admin_client: iap_v1.IdentityAwareProxyAdminServiceClient,
    project_id: str,
    region: str,
) -> Callable[[str], iap_v1.TunnelDestGroup]:
    """Return a function that will return the TunnelDestGroup object for the named group, or raise NotFound."""

    def _retriever(name: str) -> iap_v1.TunnelDestGroup:
        return iap_admin_client.get_tunnel_dest_group(
            request=iap_v1.GetTunnelDestGroupRequest(
                name=f"projects/{project_id}/iap_tunnel/locations/{region}/destGroups/{name}",
            ),
        )

    return _retriever


@pytest.fixture(scope="session")
def iap_dest_group_iam_policy_retriever(
    iap_admin_client: iap_v1.IdentityAwareProxyAdminServiceClient,
    project_id: str,
    region: str,
) -> Callable[[str], policy_pb2.Policy]:
    """Return a function that will return the IAM Policy object for the named group, or raise a NotFound exception."""

    def _retriever(name: str) -> policy_pb2.Policy:
        return iap_admin_client.get_iam_policy(
            request=iam_policy_pb2.GetIamPolicyRequest(
                resource=f"projects/{project_id}/iap_tunnel/locations/{region}/destGroups/{name}",
            ),
        )

    return _retriever


@pytest.fixture(scope="session")
def iap_dest_group_deleter(
    iap_admin_client: iap_v1.IdentityAwareProxyAdminServiceClient,
    project_id: str,
    region: str,
) -> Callable[[str], None]:
    """Return a function that delete the named reserved address, or raise a NotFound exception."""

    def _deleter(name: str) -> None:
        iap_admin_client.delete_tunnel_dest_group(
            request=iap_v1.DeleteTunnelDestGroupRequest(
                name=f"projects/{project_id}/iap_tunnel/locations/{region}/destGroups/{name}",
            ),
        )

    return _deleter
