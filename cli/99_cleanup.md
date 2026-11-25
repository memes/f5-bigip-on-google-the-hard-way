# Resource clean up

1. Delete the BIG-IP VM instances and disks

   ```shell
   gcloud compute instances delete \
        bigip-the-hard-way-01 \
        --project my-project \
        --zone us-west1-b \
        --delete-disks all \
        --no-graceful-shutdown \
        --quiet
   ```

   ```text
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/zones/us-west1-b/instances/bigip-the-hard-way-01].
   ```

   ```shell
   gcloud compute instances delete \
        bigip-the-hard-way-02 \
        --project my-project \
        --zone us-west1-c \
        --delete-disks all \
        --no-graceful-shutdown \
        --quiet
   ```

   ```text
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/zones/us-west1-c/instances/bigip-the-hard-way-02].
   ```

1. Delete the reserved IP addresses

   ```shell
   gcloud compute addresses delete \
        bigip-the-hard-way-01-mgt \
        bigip-the-hard-way-01-ext \
        bigip-the-hard-way-01-int \
        bigip-the-hard-way-02-mgt \
        bigip-the-hard-way-02-ext \
        bigip-the-hard-way-02-int \
        --project my-project \
        --region us-west1 \
        --quiet
   ```

   ```text
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/regions/us-west1/addresses/bigip-the-hard-way-01-mgt].
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/regions/us-west1/addresses/bigip-the-hard-way-01-ext].
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/regions/us-west1/addresses/bigip-the-hard-way-01-int].
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/regions/us-west1/addresses/bigip-the-hard-way-02-mgt].
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/regions/us-west1/addresses/bigip-the-hard-way-02-ext].
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/regions/us-west1/addresses/bigip-the-hard-way-02-int].
   ```

1. Delete the firewall rules

   ```shell
   gcloud compute firewall-rules delete \
        bigip-the-hard-way-allow-admin-mgt \
        bigip-the-hard-way-allow-dsc-mgt \
        bigip-the-hard-way-allow-dsc-ext \
        --project my-project \
        --quiet
   ```

   ```text
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/global/firewalls/bigip-the-hard-way-allow-admin-mgt].
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/global/firewalls/bigip-the-hard-way-allow-dsc-mgt].
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/global/firewalls/bigip-the-hard-way-allow-dsc-ext].
   ```

   ```shell
   gcloud compute firewall-rules delete \
        bigip-the-hard-way-allow-admin-ext \
        --project my-project \
        --quiet
   ```

   ```text
   ERROR: (gcloud.compute.firewall-rules.delete) Could not fetch resource:
    - The resource 'projects/my-project/global/firewalls/bigip-the-hard-way-allow-admin-ext' was not found
   ```

1. Delete the BIG-IP VM service account

   > NOTE: Make sure the email address matches that of the dedicated service account you created as a
   > [prerequisite](10_prereqs.md#create-a-service-account).

   ```shell
   gcloud iam service-accounts delete \
        bigip-the-hard-way@my-project.iam.gserviceaccount.com \
        --project my-project \
        --quiet
   ```

   ```text
   deleted service account [bigip-the-hard-way@my-project.iam.gserviceaccount.com]
   ```

1. Delete the VPC subnets and networks

   ```shell
   gcloud compute networks subnets delete \
        bigip-the-hard-way-mgt-1 \
        bigip-the-hard-way-ext-1 \
        bigip-the-hard-way-int-1 \
        --project my-project \
        --region us-west1 \
        --quiet
   ```

   ```text
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/regions/us-west1/subnetworks/bigip-the-hard-way-mgt-1].
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/regions/us-west1/subnetworks/bigip-the-hard-way-ext-1].
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/regions/us-west1/subnetworks/bigip-the-hard-way-int-1].
   ```

   ```shell
   gcloud compute networks delete \
        bigip-the-hard-way-mgt \
        bigip-the-hard-way-ext \
        bigip-the-hard-way-int \
        --project my-project \
        --quiet
   ```

   ```text
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/global/networks/bigip-the-hard-way-mgt].
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/global/networks/bigip-the-hard-way-ext].
   Deleted [https://www.googleapis.com/compute/v1/projects/my-project/global/networks/bigip-the-hard-way-int].
   ```

```shell
gcloud iap tcp dest-groups delete bigip-the-hard-way \
     --project my-project \
     --region us-west1 \
     --quiet
```

```text
{}
```
