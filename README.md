
# LSF 

CycleCloud project for Spectrum LSF.

Azure Cyclecloud is integrated with LSF RC as a resource provider.

See the IBM docs for details.
https://www.ibm.com/support/knowledgecenter/en/SSWRJV_10.1.0/lsf_resource_connector/lsf_rc_cycle_config.html

## Prerequisites

### IBM Spectrum LSF

This product requires LSF FP9 or FP8 (520099) + iFix (529611).

To use the fully automated cluster, or the vm image builder in this project
LSF binaries and entitlement file must be added to the blobs/ directory.

* lsf10.1_lnx310-lib217-x86_64-520099.tar.Z
* lsf10.1_lnx310-lib217-x86_64-529611.tar.Z
* lsf10.1_lsfinstall_linux_x86_64.tar.Z
* lsf_std_entitlement.dat

To use the install automation in this project add these files (or appropriate
kernel packages) to the `blobs/` directory.

### Azure CycleCloud

This project requires running Azure CycleCloud version 7.7.4 or later.

## Supported Scenarios

### Externally Managed Master Node (Scenario 1)

The most common introductory approach is to manually configure LSF master nodes
to work with the CycleCloud LSF cluster type. The cluster type is available in 
the CycleCloud new cluster menu. The CycleCloud LSF cluster type does not have 
a master node(s), it's assumed that is a pre-existing resource.

This cluster also requires that the user creates a VM image with LSF pre-installed
in a slave configuration. To facilitate this we supply some automation using 
_Packer_ to create this image. These tools can be found in the [_/vm-image_](vm-image/README.md)

### Fully Managed Cluster (Scenario 2)

CycleCloud has an example project that can deploy a fully managed LSF cluster to
Azure. 


## LSF Configurations for CycleCloud Provider

### LSF Resources for CycleCloud

CycleCloud LSF cluster is designed to support a number of compute scenarios
including tightly-coupled MPI jobs, high-throughput parallel tasks, gpu-accelerated
workloads and low priority VirtualMachines.

To enable these scenarios Azure recommends configuring a number of custom shared
resource types.

Add these properties to _lsb.shared_
```
   cyclecloudhost  Boolean  ()       ()       (instances from Azure CycleCloud)
   cyclecloudmpi  Boolean   ()       ()       (instances that support MPI placement)
   cyclecloudlowprio  Boolean ()     ()       (instances that low priority / interruptible from Azure CycleCloud)
   nodearray  String     ()       ()       (nodearray from CycleCloud)
   placementgroup String ()       ()       (id used to note locality of machines)
   instanceid String     ()       ()       (unique host identifier)
```

### A Special Note on PlacementGroups

Azure Datacenters have Infiniband network capability for HPC scenarios. These
networks, unlike the normal ethernet, have limited span. The Infiniband network
extents are described by "PlacementGroups". If VMs reside in the same placement
group and are special Infiniband-enabled VM Types, then they will share an 
Infiniband network. 

These placement groups necessitate special handling in LSF and CycleCloud.

Here is an example LSF template for Cyclecloud from [_cyclecloudprov_templates.json_](examples/cyclecloudprov_templates.json):

```json
{
  "templateId": "ondemandmpi-1",
  "attributes": {
    "nodearray": ["String", "ondemandmpi" ],
    "zone": [  "String",  "westus2"],
    "mem": [  "Numeric",  8192.0],
    "ncpus": [  "Numeric",  2],
    "cyclecloudmpi": [  "Boolean",  1],
    "placementgroup": [  "String",  "ondemandmpipg1"],
    "ncores": [  "Numeric",  2],
    "cyclecloudhost": [  "Boolean",  1],
    "type": [  "String",  "X86_64"],
    "cyclecloudlowprio": [  "Boolean",  0]
  },
  "maxNumber": 40,
  "nodeArray": "ondemandmpi",
  "placementGroupName": "ondemandmpipg1",
  "priority": 448,
  "customScriptUri": "https://aka.ms/user_data.sh",
  "userData" : "nodearray_name=ondemandmpi;placement_group_id=ondemandmpipg1"
}
```

The `placementGroupName` in this file can be anything but will determine the 
name of the placementGroup in CycleCloud. Any nodes borrowed from CycleCloud 
from this template will reside in this placementGroup and, if they're Infiniband-enabled VMs, will share an IB network.

Note that `placementGroupName` matches the host attribute `placementgroup`, this
intentional and necessary. Also that the
`placement_group_id` is set in `userData` to be used in [_user_data.sh_](examples/user_data.sh) at 
host start time.
  The additional `ondemandmpi` attribute is used to 
prevent this job from 
matching on hosts where `placementGroup` is undefined.

We advise this template be used with a RES_REQ as follows:
```
-R "span[ptile=2] select[nodearray=='ondemandmpi' && cyclecloudmpi] same[placementgroup]" my_job.sh
```

By inspecting [_cyclecloudprov_templates.json_](examples/cyclecloudprov_templates.json) and [_user_data.sh_](examples/user_data.sh)
see how GPU jobs, both MPI and parallel can be supported, eg. for MPI job:
```
-R "span[ptile=1] select[nodearray=='gpumpi' && cyclecloudmpi] same[placementgroup] -ngpus 2
```
or parallel job (no placement group needed):
```
-R select[nodearray=='gpu' && !cyclecloudmpi] -ngpus 1
```

### Additional LSF Template Attributes for CycleCloud

The only strictly required attributes in a LSF template are:
* templateId
* nodeArray

Others are inferred from the CycleCloud configuration, can be ommited, or aren't
necessary at all.
* imageId - Azure VM Image eg. `"/subscriptions/xxxxxxxx-xxxx-xxxx-xxx-xxxxxxxxxxxx/resourceGroups/my-images-rg/providers/Microsoft.Compute/images/lsf-execute-201910230416-80a9a87f"` override for CycleCloud cluster configuration.
* subnetId - Azure subnet eg. `"resource_group/vnet/subnet"` override for CycleCloud cluster configuration.
* vmType - eg. `"Standard_HC44rs"` override for CycleCloud cluster configuration.
* keyPairLocation - eg. `"~/.ssh/id_rsa_beta"` override for CycleCloud cluster configuration.
* customScriptUri - eg. "http://10.1.0.4/user_data.sh", no script if not specified.
* userData - eg. `"nodearray_name=gpumpi;placement_group_id=gpumpipg1"` empty if not specified.

### Environment Variables for _user_data.sh_

Cyclecloud/LSF automatically sets certain variables in the run environment of _user_data.sh_. These variables are:
* rc_account
* template_id 
* providerName (default: cyclecloud)
* clustername
* cyclecloud_nodeid
* anything specified in `userData` template attribute.

## Initializing the "Headless" LSF Cluster Type

### Setup involving LSF prerequisites

* Choose an LSF install location; eg. `LSF_TOP=/grid/lsf` and use throughout.
* Create a VM image with LSF installed
  * Add installers and entitlement file to the `/blobs` directory.
  * Follow instructions found in the [vm_image directory](vm-image/README.md).
* Configure the cyclecloud host provider on the LSF Master.
  * Compose _cyclecloudprov_config.json_
  * Compose [_cyclecloudprov_templates.json_](examples/cyclecloudprov_templates.json) which can be based on the file in the examples directory.
* Edit user_data.sh script to appropriately set MASTER_LIST.
* Host the updated script in a URL allowing anonymous authentication, 
Azure Storage Account in public mode works well.


### Setup Cluster in CycleCloud

* Create a LSF cluster in the CycleCloud UI
  * Along with VM types, Networking, and ImageId, set the `LSF_TOP` for the execute nodes when configuring.
* Start the cluster
* Restart mbatchd on the master node and LSF should be integrated with the 
CycleCloud cluster.
* Start a job requesting resources from _cyclecloudprov_templates.json_

## Setup the Fully-Managed LSF Cluster Type

This repo contains the [cyclecloud project](https://docs.microsoft.com/en-us/azure/cyclecloud/projects). The fully-managed LSF cluster is a completely automated cluster
which will start a filesystem for LSF_TOP, high-availability LSF master nodes,
as well as all the LSF configuration files, and worker nodes.

The cluster template for this scenario is [_lsf-full.txt_](examples/lsf-full.txt). 
To prepare the environment to run this cluster:

1. Copy LSF installers into the `blobs/` directory.
1. Upload the lsf project to a locker `cyclecloud project upload`
1. Import the cluster as a service offering `cyclecloud import_cluster LSF-full -f lsf-full.txt -t`
1. Add the cluster to your managed cluster list in the CycleCloud UI with the _+add cluster_ button.
1. Follow the configuration menu, save the cluster and START it.

_NOTE_ : to avoid race conditions in HA master setup, transient software 
installation failures with recovery are expected.

_NOTE_ : _cyclecloudprov_templates.json_ is not automatically updated. The automation
will initialize this file, but if you change the machine type then the host attributes
(mem, ncpus, etc) will need to be updated and _mbatchd_ restarted.

## Submit jobs

Once the cluster is running you can log into one of the master nodes and submit
jobs to the scheduler:

1. `cyclecloud connect master-1 -c my-lsf-cluster`
1. `bsub sleep 300`
1. You'll see an ondemand node start up and prepare to run jobs.
1. When the job queue is cleared, nodes will autoscale back down.

There are a number of default queue types in the CycleCloud LSF cluster.

```
QUEUE_NAME      PRIO STATUS          MAX JL/U JL/P JL/H NJOBS  PEND   RUN  SUSP 
ondemand         30  Open:Active       -    -    -    -     0     0      0     0
ondemandmpi      30  Open:Active       -    -    -    -     0     0      0     0
lowprio          30  Open:Active       -    -    -    -     0     0      0     0
gpu              30  Open:Active       -    -    -    -     0     0      0     0
gpumpi           30  Open:Active       -    -    -    -     0     0      0     0
```

* ondemand - a general queue (default), for pleasantly parallel jobs.
* ondemandmpi - a queue for tightly-coupled jobs.
* lowprio - a queue for pre-emptible jobs which will run on low priority machines.
* gpu - parallel queue for jobs needing GPU co-processor.
* gpumpi - gpu mpi jobs.

Examples of supported job submissions:
* `bsub -J "testArr[100]" my-job.sh` (ondemand is default)
* `bsub -n 4 -q ondemandmpi -R "span[ptile=2]" my-job.sh`
* `bsub -n 2 -q gpumpi -R "span[ptile=1]" -ngpus 2 my-job.sh`



# Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
