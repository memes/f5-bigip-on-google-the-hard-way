#!/bin/bash
# shellcheck disable=SC1083 # TMSH encloses properties in { }
mkdir -p /var/log/cloud /config/cloud
touch /var/log/cloud/bigip-the-hard-way.log
trap 'rm -f /tmp/bigip-the-hard-way.fifo' EXIT
mknod /tmp/bigip-the-hard-way.fifo p
tee </tmp/bigip-the-hard-way.fifo -a /var/log/cloud/bigip-the-hard-way.log /dev/ttyS0 &
exec 1>&-
exec 1>/tmp/bigip-the-hard-way.fifo
exec 2>&1
# shellcheck disable=SC1091 # This file is guaranteed to exist on official BIG-IP VE images
. /usr/lib/bigstart/bigip-ready-functions
wait_bigip_ready
if [ ! -f /config/cloud/.mgmtInterface ]; then
    echo "$0: INFO: Resetting management configuration"
    tmsh modify sys global-settings mgmt-dhcp disabled
    tmsh delete sys management-route all
    tmsh delete sys management-ip all
    # MODIFY THE NEXT FOUR LINES TO MATCH YOUR DEPLOYMENT ENVIRONMENT
    tmsh create sys management-ip 10.100.0.101/32
    tmsh create sys management-route mgmt_gw network 10.100.0.1/32 type interface mtu 1460
    tmsh create sys management-route mgmt_net network 10.100.0.0/24 gateway 10.100.0.1 mtu 1460
    tmsh create sys management-route default gateway 10.100.0.1 mtu 1460
    tmsh modify sys global-settings remote-host add { metadata.google.internal { hostname metadata.google.internal addr 169.254.169.254 } }
    tmsh modify sys management-dhcp sys-mgmt-dhcp-config request-options delete { ntp-servers }
    tmsh modify sys dns name-servers add { 169.254.169.254 }
    tmsh modify sys ntp servers add { 169.254.169.254 }
    tmsh save /sys config
    echo "$0: INFO: Updating sys database"
    bigstart stop tmm
    tmsh modify sys db provision.managementeth value eth1
    tmsh modify sys db provision.1nicautoconfig value disable
    tmsh save /sys config
    [ -e "/etc/ts/common/image.cfg" ] && sed -i 's/iface=eth[0-7]/iface=eth1/g' /etc/ts/common/image.cfg
    touch /config/cloud/.mgmtInterface
    echo "$0: INFO: Rebooting to force reset of management interface"
    reboot
else
    echo "$0: INFO: Skipping reset of management interface - remove /config/cloud/.mgmtInterface to force reset"
fi
