# F5 BIG-IP on Google Cloud, the hard way

![GitHub release](https://img.shields.io/github/v/release/memes/f5-bigip-on-google-the-hard-way?sort=semver)
![GitHub last commit](https://img.shields.io/github/last-commit/memes/f5-bigip-on-google-the-hard-way)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-3.0-4baaaa.svg)](CODE_OF_CONDUCT.md)

Inspired by [kubernetes the hard way], this repo takes you through provisioning and on-boarding a functional BIG-IP
active-standby pair on Google Cloud using the GCP web console, `gcloud`, `ssh`, and `scp` commands only. The intent is
to illustrate the steps that are performed in the background by F5's published templates and utilities for those that
are curious, or want to build out their own custom IaC modules, or are trying to understand the conditions that could
lead to a failure case.

> NOTE: This is not the recommended way to deploy a BIG-IP HA pair - see the F5 DevCentral community maintained
> [BIG-IP HA] module for a more robust and production ready solution that streamlines these provisioning steps.

## Objectives

* Launch a pair of BIG-IP VE instances on Google Cloud without public IP addresses
* Connect to VEs and reset admin user password
* Reconfigure management interface to eth1
* Establish device sync and failover between the VE instances
* Install optional BIG-IP extension packages for declarative management and [CFE] failover handling
* Configure data-plane self-IP addresses, setup a simple virtual server to verify functionality

## Non-objectives

* Integrate with a Google load balancer
* Configure [CFE] for real-world scenarios

## Steps

1. [Prerequisites](docs/10_prereqs.md)
1. [Create BIG-IP instances](docs/20_create-big-ips.md)
1. [Establish HA](docs/30_establish-ha.md)
1. [Clean up resources](docs/99_cleanup.md)

[kubernetes the hard way]: https://github.com/kelseyhightower/kubernetes-the-hard-way/
[BIG-IP HA]: https://github.com/f5devcentral/terraform-google-f5-bigip-ha
[CFE]: https://clouddocs.f5.com/products/extensions/f5-cloud-failover/latest/userguide/overview.html
