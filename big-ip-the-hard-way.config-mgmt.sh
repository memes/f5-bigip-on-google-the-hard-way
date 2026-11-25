#!/bin/bash
# One-time initialization of BIG-IP management interface on eth1 with reboot.
#
# Source: https://github.com/memes/f5-bigip-on-google-the-hard-way/blob/main/big-ip-the-hard-way.config-mgmt.sh
# shellcheck disable=SC1083 # TMSH encloses properties in { }
mkdir -p /var/log/cloud /config/cloud
touch /var/log/cloud/big-ip-the-hard-way.log
trap 'rm -f /tmp/big-ip-the-hard-way.fifo' EXIT
mknod /tmp/big-ip-the-hard-way.fifo p
tee </tmp/big-ip-the-hard-way.fifo -a /var/log/cloud/big-ip-the-hard-way.log /dev/ttyS0 &
exec 1>&-
exec 1>/tmp/big-ip-the-hard-way.fifo
exec 2>&1
# shellcheck disable=SC1091 # This file is guaranteed to exist on official BIG-IP VE images
. /usr/lib/bigstart/bigip-ready-functions
wait_bigip_ready
if [ ! -f /config/cloud/.mgmtInterface ]; then
    echo "$0: INFO: Resetting management configuration"
    target_name="$(curl -sf --retry 20 -H "Metadata-Flavor: Google" "http://169.254.169.254/computeMetadata/v1/instance/name")"
    target_address="$(curl -sf --retry 20 -H "Metadata-Flavor: Google" "http://169.254.169.254/computeMetadata/v1/instance/network-interfaces/1/ip")"
    target_netmask="$(curl -sf --retry 20 -H "Metadata-Flavor: Google" "http://169.254.169.254/computeMetadata/v1/instance/network-interfaces/1/subnetmask")"
    target_gateway="$(curl -sf --retry 20 -H "Metadata-Flavor: Google" "http://169.254.169.254/computeMetadata/v1/instance/network-interfaces/1/gateway")"
    target_mtu="$(curl -sf --retry 20 -H "Metadata-Flavor: Google" "http://169.254.169.254/computeMetadata/v1/instance/network-interfaces/1/mtu")"
    target_network="$(ipcalc -n "${target_address}" "${target_netmask}" | cut -d= -f2)"
    tmsh modify sys global-settings gui-setup disabled
    tmsh modify sys global-settings mgmt-dhcp disabled
    tmsh modify sys global-settings hostname "${target_name:0:57}.local"
    tmsh delete sys management-route all
    tmsh delete sys management-ip all
    tmsh create sys management-ip "${target_address}/32"
    tmsh create sys management-route mgmt_gw network "${target_gateway}/32" type interface mtu "${target_mtu}"
    tmsh create sys management-route mgmt_net network "${target_network}/${target_netmask}" gateway "${target_gateway}" mtu "${target_mtu}"
    tmsh create sys management-route default gateway "${target_gateway}" mtu "${target_mtu}"
    tmsh modify sys global-settings remote-host add { metadata.google.internal { hostname metadata.google.internal addr 169.254.169.254 } }
    tmsh modify sys management-dhcp sys-mgmt-dhcp-config request-options delete { ntp-servers }
    tmsh modify sys dns name-servers add { 169.254.169.254 }
    tmsh modify sys ntp servers add { 169.254.169.254 }
    tmsh save sys config
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
