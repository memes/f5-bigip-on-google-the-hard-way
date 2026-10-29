# Creating the BIG-IP instances

![Updated](https://img.shields.io/github/last-commit/memes/f5-bigip-on-google-the-hard-way?label=Updated&path=docs%2F20_create-big-ips.md)

## Choose your base BIG-IP Compute Engine image

The BIG-IP instances need to be created from an F5 published Google Compute Engine image that contains the base
operating system and BIG-IP installation. To keep things simple, we're going to use a **PAYG** (Pay-As-You-Go) image[^1]
as this removes the need to deal with BIG-IP license pools or keys, making it much easier to spin-up and tear-down
instances as needed.

Since this tutorial is not designed to handle large production workloads, a Good [bundle] with 1 Gbps [throughput] will
be sufficient. You can find the F5 published VE images for Google Cloud using `gcloud` command to list and filter for
BIG-IP v21.1 images matching `good` and `1gbps` in F5's public images source, ordering them by descending version and
build number (latest version first).

```shell
gcloud compute images list \
    --project f5-7626-networks-public \
    --filter 'selfLink~f5-7626-networks-public AND name~f5-bigip-21.1.*payg-good-1gbps' \
    --format 'table(name:sort=1:reverse)'
```

As of September 30th 2026, this command finds a few of BIG-IP v21.1 VE images that match requirements:

```text
NAME
f5-bigip-21-1-0-2-0-35-22-payg-good-1gbps-260923101645
f5-bigip-21-1-0-2-0-0-22-payg-good-1gbps-260824081116
f5-bigip-21-1-0-1-0-0-26-payg-good-1gbps-260714080018
f5-bigip-21-1-0-0-0-payg-good-1gbps-260504135337
```

For the remainder of this tutorial we'll use `f5-bigip-21-1-0-2-0-35-22-payg-good-1gbps-260923101645` as it is the most
recent published BIG-IP VE version meeting the licensing and throughput requirements.

## Choose your BIG-IP deployment zone(s)

> [!TIP]
> F5 recommends deploying each BIG-IP instance in distinct Compute Engine zones. This gives the HA pair resiliency in
> the case of a GCP zonal failure but with a potential increase in data transfer costs, depending on the origin servers
> zone assignments. If all the origin servers are in the same zone or if zonal redundancy is not required, use
> the same zone name for both instances. See Google's [Network Pricing](https://cloud.google.com/vpc/network-pricing)
> documentation for more details.

```shell
gcloud compute zones list \
    --project my-project \
    --filter 'region~us-west1'
```

```text
NAME        REGION    STATUS  NEXT_MAINTENANCE  TURNDOWN_DATE
us-west1-b  us-west1  UP
us-west1-c  us-west1  UP
us-west1-a  us-west1  UP
```

This shows that there are three zones that are `UP` in `us-west1`. Given these results, and to be tolerant of zonal
failures, the commands below will deploy the first BIG-IP to `us-west1-b` and the second BIG-IP to `us-west1-c`.

## Create the BIG-IP instances

<!-- markdownlint-disable line-length -->
```shell
gcloud compute instances create bigip-the-hard-way-01 \
    --project my-project \
    --zone us-west1-b \
    --description "F5 BIG-IP VE 01" \
    --machine-type n2-standard-4 \
    --can-ip-forward \
    --network-interface nic-type=VIRTIO_NET,no-address,stack-type=IPV4_ONLY,subnet=bigip-the-hard-way-ext-1,private-network-ip=10.0.0.101 \
    --network-interface nic-type=VIRTIO_NET,no-address,stack-type=IPV4_ONLY,subnet=bigip-the-hard-way-mgt-1,private-network-ip=10.100.0.101 \
    --network-interface nic-type=VIRTIO_NET,no-address,stack-type=IPV4_ONLY,subnet=bigip-the-hard-way-int-1,private-network-ip=10.10.0.101 \
    --metadata "block-project-ssh-keys=true,ssh-keys=admin:${BIG_IP_PUBKEY}" \
    --service-account "bigip-the-hard-way@my-project.iam.gserviceaccount.com" \
    --scopes https://www.googleapis.com/auth/cloud-platform \
    --create-disk auto-delete=yes,boot=yes,mode=rw,size=100,type=pd-balanced,image=projects/f5-7626-networks-public/global/images/f5-bigip-21-1-0-2-0-35-22-payg-good-1gbps-260923101645
```
<!-- markdownlint-enable line-length -->

<!-- markdownlint-disable line-length -->
```text
Created [https://www.googleapis.com/compute/v1/projects/my-project/zones/us-west1-b/instances/bigip-the-hard-way-01].
WARNING: Some requests generated warnings:
 - Disk size: '100 GB' is larger than image size: '47 GB'. You might need to resize the root repartition manually if the operating system does not support automatic resizing. See https://cloud.google.com/compute/docs/disks/add-persistent-disk#resize_pd for details.

NAME                   ZONE        MACHINE_TYPE   PREEMPTIBLE  INTERNAL_IP   EXTERNAL_IP  STATUS
bigip-the-hard-way-01  us-west1-b  n2-standard-4               10.0.0.101                 RUNNING
                                                               10.100.0.101
                                                               10.10.0.4
```
<!-- markdownlint-enable line-length -->

Repeat for the second BIG-IP instance, but use the reserved addresses and target zone for the second BIG-IP.

<!-- markdownlint-disable line-length -->
```shell
gcloud compute instances create bigip-the-hard-way-02 \
    --project my-project \
    --zone us-west1-c \
    --description "F5 BIG-IP VE 02" \
    --machine-type n2-standard-4 \
    --can-ip-forward \
    --network-interface nic-type=VIRTIO_NET,no-address,stack-type=IPV4_ONLY,subnet=bigip-the-hard-way-ext-1,private-network-ip=10.0.0.102 \
    --network-interface nic-type=VIRTIO_NET,no-address,stack-type=IPV4_ONLY,subnet=bigip-the-hard-way-mgt-1,private-network-ip=10.100.0.102 \
    --network-interface nic-type=VIRTIO_NET,no-address,stack-type=IPV4_ONLY,subnet=bigip-the-hard-way-int-1,private-network-ip=10.10.0.102 \
    --metadata "block-project-ssh-keys=true,ssh-keys=admin:${BIG_IP_PUBKEY}" \
    --service-account "bigip-the-hard-way@my-project.iam.gserviceaccount.com" \
    --scopes https://www.googleapis.com/auth/cloud-platform \
    --create-disk auto-delete=yes,boot=yes,mode=rw,size=100,type=pd-balanced,image=projects/f5-7626-networks-public/global/images/f5-bigip-21-1-0-2-0-35-22-payg-good-1gbps-260923101645
```
<!-- markdownlint-enable line-length -->

> [!TIP]
> In the instructions that follow you will be asked to check the serial console output periodically to ensure the
> BIG-IPs are ready for the next action. An alternative is to open two separate shell sessions and run
>
> ```shell
> gcloud compute instances tail-serial-port-output bigip-the-hard-way-01 \
>     --project my-project \
>     --zone us-west1-b
> ```
>
> in one session, and
>
> ```shell
> gcloud compute instances tail-serial-port-output bigip-the-hard-way-02 \
>     --project my-project \
>     --zone us-west1-c
> ```
>
> in the other. This way you can observe the that you can observe the BIG-IP VE serial console output for each instance
> in near-real time without executing `gcloud compute instances get-serial-port-output ...` repeatedly.

<!-- markdownlint-enable line-length -->
```shell
gcloud compute instances get-serial-port-output bigip-the-hard-way-01 \
    --project my-project \
    --zone us-west1-b
```

<!-- spell-checker: disable -->
```text
...
[  OK  ] Started The device management daemo...vice trust group functionality..
         Starting The devices management daem...ce trust group functionality....
[  OK  ] Reached target Multi-User System.
         Starting Update UTMP about System Runlevel Changes...
[  OK  ] Reached target Cloud-init target.
[  OK  ] Started Update UTMP about System Runlevel Changes.
[  OK  ] Started Execute cloud user/final scripts.
mcpd has reached 'running' state
...
```
<!-- spell-checker: enable -->

Repeat for the second BIG-IP to make sure it is ready for the next step by confirming `mcpd has reached 'running state`
message is seen in the output.

```shell
gcloud compute instances get-serial-port-output bigip-the-hard-way-02 \
    --project my-project \
    --zone us-west1-c
```

<!-- spell-checker: disable -->
```text
...
[  OK  ] Started The device management daemo...vice trust group functionality..
         Starting The devices management daem...ce trust group functionality....
[  OK  ] Reached target Multi-User System.
         Starting Update UTMP about System Runlevel Changes...
[  OK  ] Reached target Cloud-init target.
[  OK  ] Started Update UTMP about System Runlevel Changes.
[  OK  ] Started Execute cloud user/final scripts.
localhost login: mcpd has reached 'running' state
...
```

## Allow administration access on management and first data plane networks

Google Cloud VPC networks have default deny ingress firewall rules that prevent traffic from entering VMs. In order to
administer the BIG-IPs and accept administration via SSH and Web GUI we need to add an INGRESS firewall rule to allow
access to ports 22 and 443 from *your* source IP address or the address of a bastion. In the example below, the source
ranges are those associated with Google's IAP service which we use to tunnel into the VPC network without using a
bastion.

> [!WARNING]
> To avoid using IAP, change the value of `source-ranges` to match the appropriate set of source CIDRs for
> management access and ensure you have connectivity into the VPC before proceeding. You will not be able to configure
> the BIG-IP instances without access to ports 22 and 443 on the management and first data plane networks.

First we create the rule to allow access to the BIG-IP instances through the management network which will be assigned
on eth1.

```shell
gcloud compute firewall-rules create bigip-the-hard-way-allow-admin-mgt \
    --project my-project \
    --description "Allow INGRESS for SSH and GUI BIG-IP management (eth1)" \
    --network bigip-the-hard-way-mgt \
    --priority 900 \
    --direction INGRESS \
    --action allow \
    --rules tcp:22,tcp:443 \
    --target-service-accounts "bigip-the-hard-way@my-project.iam.gserviceaccount.com" \
    --source-ranges "35.235.240.0/20"
```

<!-- markdownlint-disable line-length -->
```text
Creating firewall...Created [https://www.googleapis.com/compute/v1/projects/my-project/global/firewalls/bigip-the-hard-way-allow-admin-mgt].
Creating firewall...done.
NAME                                NETWORK                 DIRECTION  PRIORITY  ALLOW           DENY  DISABLED
bigip-the-hard-way-allow-admin-mgt  bigip-the-hard-way-mgt  INGRESS    900       tcp:22,tcp:443        False
```
<!-- markdownlint-enable line-length -->

Next, create a similar firewall rule for the first data plane VPC network which will be assigned on eth0.

> NOTE: This rule will be disabled and/or deleted after verifying the BIG-IPs are running correctly after modifying each
> BIG-IP's management interface.

```shell
gcloud compute firewall-rules create bigip-the-hard-way-allow-admin-ext \
    --project my-project \
    --description "Allow INGRESS for SSH and GUI BIG-IP management (eth0)" \
    --network bigip-the-hard-way-ext \
    --priority 900 \
    --direction INGRESS \
    --action allow \
    --rules tcp:22,tcp:443 \
    --target-service-accounts "bigip-the-hard-way@my-project.iam.gserviceaccount.com" \
    --source-ranges "35.235.240.0/20"
```

## Modify the admin user password

> [!NOTE]
> All of the SSH commands in this tutorial should execute without error or response text, but there may be warnings or
> other output unrelated to the principal activity, such as validating and storing SSH fingerprints, which we do not
> show below. Only SSH text that is related to the command being executed will be shown.

```shell
ssh admin@10.0.0.101 modify auth user admin password BigIpTh3H@rdW@y4135
```

```shell
ssh admin@10.0.0.102 modify auth user admin password BigIpTh3H@rdW@y4135
```

## Modify the admin user shell

To make it easier to execute non-interactive commands through SSH, change the `admin` user's shell to `bash` from
`tmsh`. This can be reverted later.

```shell
ssh admin@10.0.0.101 modify auth user admin shell bash
```

```shell
ssh admin@10.0.0.102 modify auth user admin shell bash
```

## Change the BIG-IP management interface to eth1

```shell
ssh admin@10.0.0.101 mkdir -p /config/cloud
```

```shell
ssh admin@10.0.0.102 mkdir -p /config/cloud
```

<!-- markdownlint-disable no-bare-urls -->
https://github.com/memes/f5-bigip-on-google-the-hard-way/blob/main/reset_management_interface.sh
<!-- markdownlint-enable no-bare-urls -->

```shell
scp reset_management_interface.sh admin@10.0.0.101:/config/cloud/
```

```text
reset_management_interface.sh                      100% 1989    34.4KB/s   00:00
```

```shell
ssh admin@10.0.0.101 "nohup bash /config/cloud/reset_management_interface.sh >/dev/null 2>/dev/null &"
```

```shell
scp reset_management_interface.sh admin@10.0.0.102:/config/cloud/
```

```text
reset_management_interface.sh                      100% 1989    36.2KB/s   00:00
```

```shell
ssh admin@10.0.0.102 sed -i 's/\.101/.102/g' /config/cloud/reset_management_interface.sh
```

```shell
ssh admin@10.0.0.102 "nohup bash /config/cloud/reset_management_interface.sh >/dev/null 2>/dev/null &"
```

Observe the serial port output for `bigip-the-hard-way-01` and `bigip-the-hard-way-02` instances; for both you should
see evidence that the script was executed and that the VMs were rebooted, something similar to the output show below.

```text
mcpd has reached 'running' state
/config/cloud/reset_management_interface.sh: INFO: Resetting management configuration
Saving running configuration...
  /config/bigip.conf
  /config/bigip_base.conf
  /config/bigip_user.conf
Saving Ethernet map ...done
Saving PCI map ...
 - verifying checksum .../var/run/f5pcimap: OK
done
 - saving ...done
/config/cloud/reset_management_interface.sh: INFO: Updating sys database
Saving running configuration...
  /config/bigip.conf
  /config/bigip_base.conf
  /config/bigip_user.conf
Saving Ethernet map ...done
Saving PCI map ...
 - verifying checksum .../var/run/f5pcimap: OK
done
 - saving ...done
/config/cloud/reset_management_interface.sh: INFO: Rebooting to force reset of management interface
dracut Warning: Killing all remaining processes
Rebooting.
[  478.065906] Restarting system.
SeaBIOS (version 1.8.2-google)
Total RAM Size = 0x0000000400000000 = 16384 MiB
CPUs found: 4     Max CPUs supported: 4
found virtio-scsi at 0:3
virtio-scsi vendor='Google' product='PersistentDisk' rev='1' type=0 removable=0
virtio-scsi blksize=512 sectors=209715200 = 102400 MiB
drive 0x000f2800: PCHS=0/0/0 translation=lba LCHS=1024/255/63 s=209715200
Sending Seabios boot VM event.
Booting from Hard Disk 0...
```

> [!IMPORTANT]
> Do not proceed until you see `mcpd has reached 'running' state` on both consoles **AFTER the rebooting message**.

```shell
ssh admin@10.100.0.101 echo Success
```

```text
Success
```

```shell
ssh admin@10.100.0.102 echo Success
```

```text
Success
```

## Disable administration access on first data plane networks

Now that the BIG-IPs have been reconfigured to use eth1 as the management interface, there is no requirement to support
admin operations on the data plane interface (BIG-IP eth0). Use either of these commands to disable or delete the
firewall rule as you prefer.

### Disable data plane firewall rule

```shell
gcloud compute firewall-rules update \
    bigip-the-hard-way-allow-admin-ext \
    --disabled \
    --project my-project \
    --quiet
```

<!-- markdownlint-disable line-length -->
```text
Updated [https://www.googleapis.com/compute/v1/projects/my-project/global/firewalls/bigip-the-hard-way-allow-admin-ext].
```

### Delete data plane firewall rule

```shell
gcloud compute firewall-rules delete \
    bigip-the-hard-way-allow-admin-ext \
    --project my-project \
    --quiet
```

<!-- markdownlint-disable line-length -->
```text
Deleted [https://www.googleapis.com/compute/v1/projects/my-project/global/firewalls/bigip-the-hard-way-allow-admin-ext].
```

### (OPTIONAL): Modify IAP tunnel destination group

```shell
gcloud iap tcp dest-groups update bigip-the-hard-way \
    --project my-project \
    --region us-west1 \
    --ip-range-list "10.100.0.101/32,10.100.0.102/32"
```

```text
cidrs:
- 10.100.0.101/32
- 10.100.0.102/32
name: projects/12345678/iap_tunnel/locations/us-west1/destGroups/bigip-the-hard-way
```

## Set the BIG-IP device hostname and data plane self-ips for each device

```shell
ssh admin@10.100.0.101 <<EOF
tmsh delete net route all
tmsh delete net self all
tmsh delete net vlan all
tmsh modify /sys global-settings gui-setup disabled
tmsh modify /sys global-settings hostname bigip-01.local
tmsh create net vlan external interfaces add { 1.0 { untagged } } mtu 1460
tmsh create net self self_external address 10.0.0.101/32 vlan external allow-service default
tmsh create net route rt_gw_external network 10.0.0.1/32 interface external
tmsh create net route default network 0.0.0.0/0 gw 10.0.0.1
tmsh create net vlan internal interfaces add { 1.2 { untagged } } mtu 1460
tmsh create net self self_internal address 10.10.0.101/32 vlan internal allow-service none
tmsh create net route rt_gw_internal network 10.10.0.1/32 interface internal
tmsh create net route rt_internal network 10.10.0.0/16 gw 10.10.0.1
tmsh save /sys config
tmsh show running-config /sys global-settings hostname
tmsh show running-config net vlan non-default-properties
tmsh show running-config net self non-default-properties
tmsh show running-config net route non-default-properties
EOF
```

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
sys global-settings {
    hostname bigip-01.local
}
net vlan external {
    dag-adjustment none
    fwd-mode l3
    if-index 464
    interfaces {
        1.0 { }
    }
    mtu 1460
    tag 4017
}
net vlan internal {
    dag-adjustment none
    fwd-mode l3
    if-index 480
    interfaces {
        1.2 { }
    }
    mtu 1460
    tag 4018
}
net self self_internal {
    address 10.10.0.101/32
    traffic-group traffic-group-local-only
    vlan internal
}
net self self_external {
    address 10.0.0.101/32
    allow-service {
        default
    }
    traffic-group traffic-group-local-only
    vlan external
}
net route default {
    gw 10.0.0.1
    network default
}
net route rt_gw_external {
    interface /Common/external
    network 10.0.0.1/32
}
net route rt_gw_internal {
    interface /Common/internal
    network 10.10.0.1/32
}
net route rt_internal {
    gw 10.10.0.1
    network 10.10.0.0/16
}
```

```shell
ssh admin@10.100.0.102 <<EOF
tmsh delete net route all
tmsh delete net self all
tmsh delete net vlan all
tmsh modify /sys global-settings gui-setup disabled
tmsh modify /sys global-settings hostname bigip-02.local
tmsh create net vlan external interfaces add { 1.0 { untagged } } mtu 1460
tmsh create net self self_external address 10.0.0.102/32 vlan external allow-service default
tmsh create net route rt_gw_external network 10.0.0.1/32 interface external
tmsh create net route default network 0.0.0.0/0 gw 10.0.0.1
tmsh create net vlan internal interfaces add { 1.2 { untagged } } mtu 1460
tmsh create net self self_internal address 10.10.0.102/32 vlan internal allow-service default
tmsh create net route rt_gw_internal network 10.10.0.1/32 interface internal
tmsh create net route rt_internal network 10.10.0.0/16 gw 10.10.0.1
tmsh save /sys config
tmsh show running-config /sys global-settings hostname
tmsh show running-config net vlan non-default-properties
tmsh show running-config net self non-default-properties
tmsh show running-config net route non-default-properties
EOF
```

Verify that the output looks similar to that for the first BIG-IP instance, but with self-ips ending in `.102`.

Next: [Establish BIG-IP HA](30_establish-ha.md)

[bundle]: https://www.f5.com/products/get-f5/perpetual-licensing-gbb
[throughput]: https://my.f5.com/manage/s/article/K14810
[revoke]: https://my.f5.com/manage/s/article/K41458656
[^1]: You can use a BYOL (Bring-Your-Own-License) image and your own license keys or BIG-IQ if you really want to but you must make sure to [revoke] the license before destroying an instance if you intend to reuse it.
