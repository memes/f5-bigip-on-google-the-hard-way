"""Validation for almost all code blocks embedded in the markdown docs, end-to-end.

Validation functions should accept the fixture execute_shell_commands to ensure they are invoked *after* the commands
that build up resources from each fenced shell code block are executed. Resource clean-up will happen when
execute_shell_commands resumes from yield, and is followed by the final markdown script to ensure all provisioned
resources were destroyed.
"""

import contextlib
import pathlib
import re
from collections import Counter
from collections.abc import Callable, Generator

import pytest
from google.api_core import exceptions
from google.cloud import compute_v1, iam_admin_v1, iap_v1
from google.iam.v1 import policy_pb2

from tests import (
    EXPECTED_ADMIN_DATA_FIREWALL_RULE_NAME,
    EXPECTED_ADMIN_MGT_FIREWALL_RULE_NAME,
    EXPECTED_BIG_IP_ADDRESSES,
    EXPECTED_BIG_IP_EXT_ADDRESSES,
    EXPECTED_BIG_IP_INT_ADDRESSES,
    EXPECTED_BIG_IP_MGT_ADDRESSES,
    EXPECTED_BIG_IP_VM_NAMES,
    EXPECTED_DSC_DATA_FIREWALL_RULE_NAME,
    EXPECTED_DSC_MGT_FIREWALL_RULE_NAME,
    EXPECTED_IAP_DEST_GROUPS,
    EXPECTED_NETWORKS,
    EXPECTED_SUBNETS,
)


@pytest.fixture(scope="module")
def provision_resources(
    execute_shell_commands: Callable[..., Generator[bool]],
    ssh_public_key: bytes,
) -> Generator[bool]:
    """Extract all individual shell commands from the markdown files, with clean up after use."""
    yield from execute_shell_commands(
        create_paths=[
            pathlib.Path("docs/10_prereqs.md"),
            pathlib.Path("docs/20_create-big-ips.md"),
            pathlib.Path("docs/30_establish-ha.md"),
        ],
        destroy_paths=[
            pathlib.Path("docs/99_cleanup.md"),
        ],
        env={
            "BIG_IP_PUBKEY": ssh_public_key.decode(encoding="utf-8"),
        },
    )


def test_provision_complete(
    *,
    provision_resources: bool,
) -> None:
    """Asserts that the provisioning of resources is complete."""
    assert provision_resources


@pytest.mark.parametrize("name", EXPECTED_IAP_DEST_GROUPS)
def test_iap_dest_group(
    name: str,
    iam_member: str,
    iap_dest_group_retriever: Callable[[str], iap_v1.TunnelDestGroup],
    iap_dest_group_iam_policy_retriever: Callable[[str], policy_pb2.Policy],
    *,
    provision_resources: bool,
) -> None:
    """Verify the IAP tunnel destination group exists and has correct membership."""
    assert name
    assert provision_resources
    dest_group = iap_dest_group_retriever(name)
    assert dest_group
    assert dest_group.cidrs
    assert not dest_group.fqdns
    policy = iap_dest_group_iam_policy_retriever(name)
    assert policy
    assert policy.bindings
    bindings = [binding for binding in policy.bindings if binding.role == "roles/iap.tunnelResourceAccessor"]
    assert bindings
    for binding in bindings:
        assert binding
        assert iam_member in binding.members


@pytest.mark.parametrize("name", EXPECTED_NETWORKS)
def test_network(
    name: str,
    network_retriever: Callable[[str], compute_v1.Network],
    *,
    provision_resources: bool,
) -> None:
    """Verify the expected VPC networks exist."""
    assert name
    assert provision_resources
    network = network_retriever(name)
    assert network
    assert network.description
    assert not network.auto_create_subnetworks


@pytest.mark.parametrize("name", EXPECTED_SUBNETS)
def test_subnet(
    name: str,
    region: str,
    subnetwork_retriever: Callable[[str], compute_v1.Subnetwork],
    *,
    provision_resources: bool,
) -> None:
    """Verify the expected VPC subnets exist."""
    assert name
    assert provision_resources
    subnet = subnetwork_retriever(name)
    assert subnet
    assert subnet.description
    assert subnet.ip_cidr_range
    assert subnet.region.endswith(region)


def test_service_account(
    service_account_retriever: Callable[[], iam_admin_v1.ServiceAccount],
    *,
    provision_resources: bool,
) -> None:
    """Verify the expected service account exists."""
    assert provision_resources
    sa = service_account_retriever()
    assert sa
    assert not sa.disabled


@pytest.mark.parametrize("name", EXPECTED_BIG_IP_ADDRESSES.keys())
def test_reserved_address(
    name: str,
    address_retriever: Callable[[str], compute_v1.Address],
    *,
    provision_resources: bool,
) -> None:
    """Verify the expected addresses have been reserved."""
    assert name
    assert provision_resources
    address = address_retriever(name)
    assert address
    assert address.address == EXPECTED_BIG_IP_ADDRESSES[name]
    assert address.address_type == "INTERNAL"
    assert address.status == "IN_USE"


def test_admin_data_firewall_rule(
    service_account: str,
    firewall_retriever: Callable[[str], compute_v1.Firewall],
    *,
    provision_resources: bool,
) -> None:
    """Verify the expected firewall rule meets expectations."""
    assert provision_resources
    # It is expected that the temporary admin on eth0 firewall has been destroyed, but assert it if it exists
    with contextlib.suppress(exceptions.NotFound):
        firewall_rule = firewall_retriever(EXPECTED_ADMIN_DATA_FIREWALL_RULE_NAME)
        assert firewall_rule
        assert not firewall_rule.disabled
        assert firewall_rule.priority == 900  # noqa: PLR2004
        assert firewall_rule.direction == "INGRESS"
        assert firewall_rule.allowed
        assert len(firewall_rule.allowed) == 2  # noqa: PLR2004
        for rule in firewall_rule.allowed:
            assert rule
            assert rule.I_p_protocol == "tcp"
            assert rule.ports
            assert rule.ports in (["22"], ["443"])
        assert not firewall_rule.denied
        assert not firewall_rule.destination_ranges
        assert firewall_rule.network.endswith(EXPECTED_NETWORKS[0])
        assert firewall_rule.source_ranges
        assert Counter(firewall_rule.source_ranges) == Counter(["35.235.240.0/20"])
        assert not firewall_rule.source_service_accounts
        assert not firewall_rule.source_tags
        assert firewall_rule.target_service_accounts
        assert Counter(firewall_rule.target_service_accounts) == Counter([service_account])
        assert not firewall_rule.target_tags


def test_admin_mgt_firewall_rule(
    service_account: str,
    firewall_retriever: Callable[[str], compute_v1.Firewall],
    *,
    provision_resources: bool,
) -> None:
    """Verify the expected firewall rule meets expectations."""
    assert provision_resources
    firewall_rule = firewall_retriever(EXPECTED_ADMIN_MGT_FIREWALL_RULE_NAME)
    assert firewall_rule
    assert not firewall_rule.disabled
    assert firewall_rule.priority == 900  # noqa: PLR2004
    assert firewall_rule.direction == "INGRESS"
    assert firewall_rule.allowed
    assert len(firewall_rule.allowed) == 2  # noqa: PLR2004
    for rule in firewall_rule.allowed:
        assert rule
        assert rule.I_p_protocol == "tcp"
        assert rule.ports
        assert rule.ports in (["22"], ["443"])
    assert not firewall_rule.denied
    assert not firewall_rule.destination_ranges
    assert firewall_rule.network.endswith(EXPECTED_NETWORKS[1])
    assert firewall_rule.source_ranges
    assert Counter(firewall_rule.source_ranges) == Counter(["35.235.240.0/20"])
    assert not firewall_rule.source_service_accounts
    assert not firewall_rule.source_tags
    assert firewall_rule.target_service_accounts
    assert Counter(firewall_rule.target_service_accounts) == Counter([service_account])
    assert not firewall_rule.target_tags


def test_dsc_mgt_firewall_rule(
    project_id: str,
    service_account: str,
    firewall_retriever: Callable[[str], compute_v1.Firewall],
    *,
    provision_resources: bool,
) -> None:
    """Verify the expected firewall rule meets expectations."""
    assert project_id
    assert provision_resources
    firewall_rule = firewall_retriever(EXPECTED_DSC_MGT_FIREWALL_RULE_NAME)
    assert firewall_rule
    assert not firewall_rule.disabled
    assert firewall_rule.priority == 900  # noqa: PLR2004
    assert firewall_rule.direction == "INGRESS"
    assert firewall_rule.allowed
    assert len(firewall_rule.allowed) == 1
    for rule in firewall_rule.allowed:
        assert rule
        assert rule.I_p_protocol == "tcp"
        assert rule.ports
        assert rule.ports == ["443"]
    assert not firewall_rule.denied
    assert not firewall_rule.destination_ranges
    assert firewall_rule.network.endswith(EXPECTED_NETWORKS[1])
    assert not firewall_rule.source_ranges
    assert firewall_rule.source_service_accounts
    assert Counter(firewall_rule.source_service_accounts) == Counter([service_account])
    assert not firewall_rule.source_tags
    assert firewall_rule.target_service_accounts
    assert Counter(firewall_rule.target_service_accounts) == Counter([service_account])
    assert not firewall_rule.target_tags


def test_dsc_data_firewall_rule(
    project_id: str,
    service_account: str,
    firewall_retriever: Callable[[str], compute_v1.Firewall],
    *,
    provision_resources: bool,
) -> None:
    """Verify the expected firewall rule meets expectations."""
    assert project_id
    assert provision_resources
    firewall_rule = firewall_retriever(EXPECTED_DSC_DATA_FIREWALL_RULE_NAME)
    assert firewall_rule
    assert not firewall_rule.disabled
    assert firewall_rule.priority == 900  # noqa: PLR2004
    assert firewall_rule.direction == "INGRESS"
    assert firewall_rule.allowed
    assert len(firewall_rule.allowed) == 3  # noqa: PLR2004
    for rule in firewall_rule.allowed:
        assert rule
        assert rule.I_p_protocol in ["tcp", "udp"]
        assert rule.ports
        if rule.I_p_protocol == "tcp":
            assert rule.ports in (["443"], ["4353"])
        else:
            assert rule.ports == ["1026"]
    assert not firewall_rule.denied
    assert not firewall_rule.destination_ranges
    assert firewall_rule.network.endswith(EXPECTED_NETWORKS[0])
    assert not firewall_rule.source_ranges
    assert firewall_rule.source_service_accounts
    assert Counter(firewall_rule.source_service_accounts) == Counter([service_account])
    assert not firewall_rule.source_tags
    assert firewall_rule.target_service_accounts
    assert Counter(firewall_rule.target_service_accounts) == Counter([service_account])
    assert not firewall_rule.target_tags


@pytest.mark.parametrize("name", EXPECTED_BIG_IP_VM_NAMES)
def test_instances(
    name: str,
    zone: str,
    service_account: str,
    ssh_public_key: bytes,
    instance_retriever: Callable[[str], compute_v1.Instance],
) -> None:
    """Raise an assertion error if the Compute Engine instance does not meet expectations."""
    assert name
    instance = instance_retriever(name)
    assert instance
    assert instance.can_ip_forward
    assert not instance.deletion_protection
    assert instance.disks
    assert len(instance.disks) == 1
    for disk in instance.disks:
        assert disk.auto_delete
        assert disk.boot
        assert disk.disk_size_gb == 100  # noqa: PLR2004
        assert disk.mode == "READ_WRITE"
    assert re.match(r"F5 BIG-IP VE 0[12]", instance.description)
    assert instance.machine_type.endswith("n2-standard-4")
    assert not instance.min_cpu_platform
    assert instance.metadata
    meta_as_dict = {item.key: item.value for item in instance.metadata.items}
    assert all(
        item in meta_as_dict.items()
        for item in {
            "block-project-ssh-keys": "true",
            "ssh-keys": f"admin:{ssh_public_key.decode('utf-8')}",
        }.items()
    )
    assert instance.network_interfaces
    assert len(instance.network_interfaces) == 3  # noqa: PLR2004
    for i, interface in enumerate(instance.network_interfaces):
        assert len(interface.access_configs) == 0
        assert interface.nic_type == "VIRTIO_NET"
        if i == 0:
            assert interface.network_i_p == EXPECTED_BIG_IP_EXT_ADDRESSES[f"{name}-ext"]
        elif i == 1:
            assert interface.network_i_p == EXPECTED_BIG_IP_MGT_ADDRESSES[f"{name}-mgt"]
        else:
            assert interface.network_i_p == EXPECTED_BIG_IP_INT_ADDRESSES[f"{name}-int"]
        assert interface.stack_type == "IPV4_ONLY"
        assert interface.subnetwork.endswith(EXPECTED_SUBNETS[i])
    assert not instance.private_ipv6_google_access
    assert instance.service_accounts
    assert len(instance.service_accounts) == 1
    for sa in instance.service_accounts:
        assert sa
        assert sa.email == service_account
        assert sa.scopes == [
            "https://www.googleapis.com/auth/cloud-platform",
        ]
    assert not instance.source_machine_image
    assert instance.status == "RUNNING"
    assert instance.zone.endswith(zone)


def test_active_standby(
    bigip_active_standby_asserter: Callable[..., None],
) -> None:
    """Assert the BIG-IP pair is active-standby."""
    bigip_active_standby_asserter(EXPECTED_BIG_IP_MGT_ADDRESSES.values())
