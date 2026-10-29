# Prerequisites for BIG-IP on Google Cloud the hard way

![Updated](https://img.shields.io/github/last-commit/memes/f5-bigip-on-google-the-hard-way?label=Updated&path=docs%2F10_prereqs.md)

## Google Cloud CLI

Since we're doing things the hard way the only tool we'll use for provisioning BIG-IP VEs on Google Cloud will be the
Google Cloud CLI. Follow the [gcloud instructions] to install and configure `gcloud` and authenticate to Google Cloud.

## (*OPTIONAL*) Create VPC networks for management and data-plane traffic

> [!NOTE]
> If you have existing data plane and management VPC networks that should be used, skip this section and move on to the
> next step of [Reserve private IP addresses](#reserve-private-ip-addresses).

BIG-IP VEs will need networks to connect to data-plane and management interfaces, with subnets that cover the zone(s)
where the instances will be deployed. If you have existing VPC networks that are suitable those can be used as-is, just
substitute the names of the existing VPC networks and subnetworks in the next step.

1. Create three global VPC networks for the deployment

    We use `gcloud` to create the control-plane network that will be used for management activities.

    ```shell
    gcloud compute networks create bigip-the-hard-way-mgt \
        --project my-project \
        --description "Management control-plane network for BIG-IP on Google Cloud the hard way" \
        --subnet-mode custom
    ```

    After a few seconds a summary of the newly created VPC network will be displayed along with suggested firewall rules
    to grant access. Ignore those suggestions as we'll add the correct rules later in the tutorial.

    <!-- markdownlint-disable line-length -->
    ```text
    Created [https://www.googleapis.com/compute/v1/projects/my-project/global/networks/bigip-the-hard-way-mgt].
    NAME                    SUBNET_MODE  BGP_ROUTING_MODE  IPV4_RANGE  GATEWAY_IPV4  INTERNAL_IPV6_RANGE
    bigip-the-hard-way-mgt  CUSTOM       REGIONAL

    Instances on this network will not be reachable until firewall rules are created. As an example, you can allow all internal traffic between instances as well as SSH, RDP, and ICMP by running:

    $ gcloud compute firewall-rules create <FIREWALL_NAME> --network bigip-the-hard-way-mgt --allow tcp,udp,icmp --source-ranges <IP_RANGE>
    $ gcloud compute firewall-rules create <FIREWALL_NAME> --network bigip-the-hard-way-mgt --allow tcp:22,tcp:3389,icmp
    ```
    <!-- markdownlint-enable line-length -->

    Repeat to create the external and internal data-plane networks; we don't include the output from these commands here
    but it should look similar to above.

    ```shell
    gcloud compute networks create bigip-the-hard-way-ext \
        --project my-project \
        --description "External data-plane network for BIG-IP on Google Cloud the hard way" \
        --subnet-mode custom
    ```

    ```shell
    gcloud compute networks create bigip-the-hard-way-int \
        --project my-project \
        --description "Internal data-plane network for BIG-IP on Google Cloud the hard way" \
        --subnet-mode custom
    ```

1. Create regional subnets, one for each of the global networks

    VPC networks have a global scope, but subnets are regional and need to be created in the Compute Engine region where
    the BIG-IP VEs will be deployed. You also need to provide the primary CIDR for each subnet. In these examples I am
    using `us-west1` as the Compute Engine region, `10.100.0.0/24`, `10.0.0.0/16`, and `10.10.0.0/16` as the primary
    CIDRs for management control-plane, external, and internal data-plane networking, respectively.

    ```shell
    gcloud compute networks subnets create bigip-the-hard-way-mgt-1 \
        --project my-project \
        --network bigip-the-hard-way-mgt \
        --description "Management control-plane subnet for BIG-IP on Google Cloud the hard way" \
        --region us-west1 \
        --range "10.100.0.0/24"
    ```

    Shortly the command will output a summary of the actions taken, verifying that the subnet was created in the
    intended region `us-west1` and with the intended primary CIDR range `10.100.0.0/24`.

    <!-- markdownlint-disable line-length -->
    ```text
    Created [https://www.googleapis.com/compute/v1/projects/my-project/regions/us-west1/subnetworks/bigip-the-hard-way-mgt-1].
    NAME                      REGION       NETWORK                 RANGE          STACK_TYPE  IPV6_ACCESS_TYPE  INTERNAL_IPV6_PREFIX  EXTERNAL_IPV6_PREFIX
    bigip-the-hard-way-mgt-1  us-west1  bigip-the-hard-way-mgt  10.100.0.0/24  IPV4_ONLY
    ```
    <!-- markdownlint-enable line-length -->

    We create the `external` and `internal` data-plane subnets with CIDRs `10.0.0.0/16` and `10.10.0.0/16` respectively.

    ```shell
    gcloud compute networks subnets create bigip-the-hard-way-ext-1 \
        --project my-project \
        --network bigip-the-hard-way-ext \
        --description "External data-plane subnet for BIG-IP on Google Cloud the hard way" \
        --region us-west1 \
        --range "10.0.0.0/16"
    ```

    ```shell
    gcloud compute networks subnets create bigip-the-hard-way-int-1 \
        --project my-project \
        --network bigip-the-hard-way-int \
        --description "Internal data-plane subnet for BIG-IP on Google Cloud the hard way" \
        --region us-west1 \
        --range "10.10.0.0/16"
    ```

## Reserve private IP addresses

```shell
gcloud compute addresses create bigip-the-hard-way-01-mgt \
    --project my-project \
    --description "BIG-IP VE 01 management interface (eth0)" \
    --region us-west1 \
    --purpose GCE_ENDPOINT \
    --subnet bigip-the-hard-way-mgt-1 \
    --addresses 10.100.0.101
```

```text
Created [https://www.googleapis.com/compute/v1/projects/my-project/regions/us-west1/addresses/bigip-the-hard-way-01-mgt].
```

```shell
gcloud compute addresses create bigip-the-hard-way-02-mgt \
    --project my-project \
    --description "BIG-IP VE 02 management interface (eth0)" \
    --region us-west1 \
    --purpose GCE_ENDPOINT \
    --subnet bigip-the-hard-way-mgt-1 \
    --addresses 10.100.0.102
```

```shell
gcloud compute addresses create bigip-the-hard-way-01-ext \
    --project my-project \
    --description "BIG-IP VE 01 external data interface (eth1)" \
    --region us-west1 \
    --purpose GCE_ENDPOINT \
    --subnet bigip-the-hard-way-ext-1 \
    --addresses 10.0.0.101
```

```shell
gcloud compute addresses create bigip-the-hard-way-02-ext \
    --project my-project \
    --description "BIG-IP VE 02 external data interface (eth1)" \
    --region us-west1 \
    --purpose GCE_ENDPOINT \
    --subnet bigip-the-hard-way-ext-1 \
    --addresses 10.0.0.102
```

```shell
gcloud compute addresses create bigip-the-hard-way-01-int \
    --project my-project \
    --description "BIG-IP VE 01 internal data interface (eth2)" \
    --region us-west1 \
    --purpose GCE_ENDPOINT \
    --subnet bigip-the-hard-way-int-1 \
    --addresses 10.10.0.101
```

```shell
gcloud compute addresses create bigip-the-hard-way-02-int \
    --project my-project \
    --description "BIG-IP VE 02 internal data interface (eth2)" \
    --region us-west1 \
    --purpose GCE_ENDPOINT \
    --subnet bigip-the-hard-way-int-1 \
    --addresses 10.10.0.102
```

```shell
gcloud compute addresses list \
    --project my-project \
    --filter 'name~bigip-the-hard-way-0'
```

```text
NAME                       ADDRESS/RANGE  TYPE      PURPOSE       NETWORK  REGION       SUBNET                    STATUS
bigip-the-hard-way-01-ext  10.0.0.101     INTERNAL  GCE_ENDPOINT           us-west1  bigip-the-hard-way-ext-1  RESERVED
bigip-the-hard-way-01-int  10.10.0.101    INTERNAL  GCE_ENDPOINT           us-west1  bigip-the-hard-way-int-1  RESERVED
bigip-the-hard-way-01-mgt  10.100.0.101   INTERNAL  GCE_ENDPOINT           us-west1  bigip-the-hard-way-mgt-1  RESERVED
bigip-the-hard-way-02-ext  10.0.0.102     INTERNAL  GCE_ENDPOINT           us-west1  bigip-the-hard-way-ext-1  RESERVED
bigip-the-hard-way-02-int  10.10.0.102    INTERNAL  GCE_ENDPOINT           us-west1  bigip-the-hard-way-int-1  RESERVED
bigip-the-hard-way-02-mgt  10.100.0.102   INTERNAL  GCE_ENDPOINT           us-west1  bigip-the-hard-way-mgt-1  RESERVED
```

## SSH

```shell
export BIG_IP_PUBLIC_KEY="$(< "${BIG_IP_PRIVATE_KEY_FILE}.pub")"
```

### (OPTIONAL): Setup IAP tunneling for access to VMs

```shell
gcloud iap tcp dest-groups create bigip-the-hard-way \
    --project my-project \
    --region us-west1 \
    --ip-range-list "10.0.0.101/32,10.0.0.102/32,10.100.0.101/32,10.100.0.102/32"
```

```text
cidrs:
- 10.0.0.101/32
- 10.0.0.102/32
- 10.100.0.101/32
- 10.100.0.102/32
name: projects/12345678/iap_tunnel/locations/us-west1/destGroups/bigip-the-hard-way
```

```shell
gcloud iap tcp dest-groups add-iam-policy-binding \
    --project my-project \
    --role roles/iap.tunnelResourceAccessor \
    --dest-group bigip-the-hard-way \
    --region us-west1 \
    --member "user:admin.user@example.com"
```

<!-- spell-checker: disable -->
```text
Updated IAM policy for iap_tunneldestgroups [projects/12345678/iap_tunnel/locations/us-west1/destGroups/bigip-the-hard-way].
```
<!-- spell-checker: enable -->

### Configure IAP tunnelling for SSH client

<!-- markdownlint-disable line-length -->
```ssh_config˚
Host 10.100.0.101 10.100.0.102
    ProxyCommand gcloud compute start-iap-tunnel %h %p --listen-on-stdin --dest-group bigip-the-hard-way --region us-west1 --project my-project --network bigip-the-hard-way-mgt

Host 10.0.0.101 10.0.0.102
    ProxyCommand gcloud compute start-iap-tunnel %h %p --listen-on-stdin --dest-group bigip-the-hard-way --region us-west1 --project my-project --network bigip-the-hard-way-ext

```
<!-- markdownlint-enable line-length -->

## Create a service account

> [!IMPORTANT]
> You can choose to use an existing service account, such as the project's Compute Engine default service account if
> suitable. Just remember that the BIG-IP instances you launch inherit the service account's permissions which may give
> the VEs more access to GCP APIs than they need. If you have an existing service account in mind, skip ahead to the
> next page to [Create the BIG-IP instances].

Google Cloud documentation recommends that [single-purpose] service accounts be created for each workload, allowing the
workload to have access only to the APIs and endpoints needed to operate successfully.

To create the service account in your default project:

```shell
gcloud iam service-accounts create bigip-the-hard-way \
    --project my-project \
    --description "Service identity for BIG-IP VMs provisioned the hard way" \
    --display-name "BIG-IP the hard way"
```

```text
Created service account [bigip-the-hard-way].
```

When referring to the service account later we will need to know the fully-qualified email address of the account. This
is usually of the form `name@my-project.iam.gserviceaccount.com` where `name` is the name you provided (e.g.
`bigip-the-hard-way`) and `my-project` is the identifier of the project you are working in, but it could be a different
email format if your Google Cloud Organization has been set to override the defaults.

To be certain, let's list all service accounts in the target project and make sure we see the one we just created and
verify the assigned email address:

```shell
gcloud iam service-accounts list \
    --project my-project
```

Your results may have more or less entries, but you should see the service account you created above in the output:

```text
DISPLAY NAME                            EMAIL                                                  DISABLED
...
Compute Engine default service account  12345678-compute@developer.gserviceaccount.com         False
App Engine default service account      my-project@appspot.gserviceaccount.com                 False
BIG-IP the hard way                     bigip-the-hard-way@my-project.iam.gserviceaccount.com  False
...
```

At this point we do not need to add any roles or permissions to the service account. This means the BIG-IP cannot make
API calls to GCP which is a best practice in case of compromise. Later in the tutorial we may add additional roles if
needed.

Next: [Create the BIG-IP instances]

[gcloud instructions]: https://cloud.google.com/sdk/docs/install-sdk
[single-purpose]: https://cloud.google.com/iam/docs/best-practices-service-accounts#single-purpose
[create the big-ip instances]: 20_create-big-ips.md
