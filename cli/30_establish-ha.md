# Establish active-standby HA

![Updated](https://img.shields.io/github/last-commit/memes/f5-bigip-on-google-the-hard-way?label=Updated&path=docs%2F30_establish-ha.md)

## Allow BIG-IP instances to sync data as a pair

In order to allow the BIG-IPs to establish trust and synchronize settings we need to add firewall rules to allow
bi-directional access.

```shell
gcloud compute firewall-rules create bigip-the-hard-way-allow-dsc-mgt \
    --project my-project \
    --description "BIG-IP ConfigSync support on management network (eth1)" \
    --network bigip-the-hard-way-mgt \
    --priority 900 \
    --direction INGRESS \
    --action allow \
    --rules tcp:443 \
    --source-service-accounts "bigip-the-hard-way@my-project.iam.gserviceaccount.com" \
    --target-service-accounts "bigip-the-hard-way@my-project.iam.gserviceaccount.com"
```

```shell
gcloud compute firewall-rules create bigip-the-hard-way-allow-dsc-ext \
    --project my-project \
    --description "BIG-IP ConfigSync support on data network (eth0)" \
    --network bigip-the-hard-way-ext \
    --priority 900 \
    --direction INGRESS \
    --action allow \
    --rules tcp:443,tcp:4353,udp:1026 \
    --source-service-accounts "bigip-the-hard-way@my-project.iam.gserviceaccount.com" \
    --target-service-accounts "bigip-the-hard-way@my-project.iam.gserviceaccount.com"
```

## Configure device trust

```shell
ssh admin@10.100.0.101 <<EOF
tmsh mv /cm device bigip1 bigip-the-hard-way-01
tmsh modify /cm device bigip-the-hard-way-01 configsync-ip 10.0.0.101
tmsh modify /cm device bigip-the-hard-way-01 unicast-address { { ip 10.0.0.101 } }
tmsh save /sys config
tmsh show /cm sync-status
EOF
```

<!-- spell-checker: disable -->
```text
Saving running configuration...
  /config/bigip.conf
  /config/bigip_base.conf
  /config/bigip_user.conf
Saving Ethernet map ...done
Saving PCI map ...
 - verifying checksum .../var/run/f5pcimap: OK
done
 - saving ...done

----------------------------------------------------------
CM::Sync Status
----------------------------------------------------------
Color    green
Status   Standalone
Mode     standalone
Summary
Details
         Optional action: Add a device to the trust domain

```
<!-- spell-checker: enable -->

```shell
ssh admin@10.100.0.102 <<EOF
tmsh mv /cm device bigip1 bigip-the-hard-way-02
tmsh modify /cm device bigip-the-hard-way-02 configsync-ip 10.0.0.102
tmsh modify /cm device bigip-the-hard-way-02 unicast-address { { ip 10.0.0.102 } }
tmsh save /sys config
tmsh show /cm sync-status
EOF
```

<!-- spell-checker: disable -->
```text
Saving running configuration...
  /config/bigip.conf
  /config/bigip_base.conf
  /config/bigip_user.conf
Saving Ethernet map ...done
Saving PCI map ...
 - verifying checksum .../var/run/f5pcimap: OK
done
 - saving ...done

----------------------------------------------------------
CM::Sync Status
----------------------------------------------------------
Color    green
Status   Standalone
Mode     standalone
Summary
Details
         Optional action: Add a device to the trust domain

```
<!-- spell-checker: enable -->

<!-- markdownlint-disable line-length -->
```shell
ssh admin@10.100.0.102 <<EOF
tmsh modify /cm trust-domain /Common/Root add-device { device-ip 10.100.0.101 device-name bigip-the-hard-way-01 username admin password BigIpTh3H@rdW@y4135 ca-device true }
tmsh list /cm trust-domain
tmsh save /sys config
EOF
```
<!-- markdownlint-enable line-length -->

<!-- spell-checker: disable -->
```text
cm trust-domain Root {
    ca-cert dtca.crt
    ca-cert-bundle dtca-bundle.crt
    ca-devices { /Common/bigip-the-hard-way-02 /Common/bigip-the-hard-way-01 }
    ca-key dtca.key
    status initialized
    trust-group device_trust_group
}
Saving running configuration...
  /config/bigip.conf
  /config/bigip_base.conf
  /config/bigip_user.conf
Saving Ethernet map ...done
Saving PCI map ...
 - verifying checksum .../var/run/f5pcimap: OK
done
 - saving ...done
```
<!-- spell-checker: enable -->

## Configure failover group and config sync

```shell
ssh admin@10.100.0.102 <<EOF
tmsh create /cm device-group failover-group devices add { bigip-the-hard-way-01 bigip-the-hard-way-02 } type sync-failover
tmsh save /sys config
tmsh run /cm config-sync to-group failover-group
tmsh show /cm sync-status
EOF
```
<!-- spell-checker: disable -->
```text
Saving running configuration...
  /config/bigip.conf
  /config/bigip_base.conf
  /config/bigip_user.conf
Saving Ethernet map ...done
Saving PCI map ...
 - verifying checksum .../var/run/f5pcimap: OK
done
 - saving ...done

--------------------------------------------------------------------------------
CM::Sync Status
--------------------------------------------------------------------------------
Color    blue
Status   Awaiting Initial Sync
Mode     high-availability
Summary  One or more devices awaiting initial config sync
Details
         bigip-the-hard-way-01: connected
         failover-group (Awaiting Initial Sync): One or more devices awaiting initial config sync
          - bigip-the-hard-way-01 is awaiting the initial config sync
          - Recommended action: Synchronize bigip-the-hard-way-02 to group failover-group

```
<!-- spell-checker: enable -->

Give the system a few seconds to sync, then verify devices are in sync by running the `tmsh` command
`show /cm sync-status` on one of the BIG-IP instances.

```shell
ssh admin@10.100.0.101 tmsh show /cm sync-status
```

```text
--------------------------------------------------------------------------------
CM::Sync Status
--------------------------------------------------------------------------------
Color    green
Status   In Sync
Mode     high-availability
Summary  All devices in the device group are in sync
Details
         bigip-the-hard-way-02: connected
         device_trust_group (In Sync): All devices in the device group are in sync
         failover-group (In Sync): All devices in the device group are in sync

```
