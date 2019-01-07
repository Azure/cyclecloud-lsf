
# LSF 

CycleCloud project for Spectrum LSF.

## Prerequisites

Users must provide LSF binaries:

* lsf10.1_linux2.6-glibc2.3-x86_64.tar.Z
* lsf10.1_lsfinstall_linux_x86_64.tar.Z

which belong in the lsf project `blobs/` directory.

## Start a LSF Cluster

This repo contains the [cyclecloud project](https://docs.microsoft.com/en-us/azure/cyclecloud/projects).  To get started with LSF:

1. Copy LSF installers into the `blobs/` directory.
1. Upload the lsf project to a locker `cyclecloud project upload`
1. Import the cluster as a service offering `cyclecloud import_cluster LSF -f lsf.txt -t`
1. Add the cluster to your managed cluster list in the CycleCloud UI with the _+add cluster_ button.

_NOTE_ : to avoid race conditions in HA master setup, transient software 
installation failures with recovery are expected.

## Resource Connector for Azure CycleCloud

This project extends the RC for LSF for an Azure CycleCloud provider: azurecc.

### Upgrading CycleCloud

A customer RC-compatible API is needed to run the resource connector. At the time
of writing this API is not distributed with GA CycleCloud but can be downloaded from this [link](https://aka.ms/cyclecloud-RC)

To upgrade CycleCloud to this version, run:
`/opt/cycle_server/util/upgrade.sh cyclecloud-7.6.0-*-linux64.tar.gz`

The Resource Connector will be configured automatically when running the cluster from the _lsf.txt_ template.  

To configure an pre-existing LSF cluster to use CycleCloud RC proceed to the next steps.

### Installing the azurecc RC

The azurecc resource connector is not yet part of the LSF product release.
For now, it's necessary to install the provider plugin.

1. Copy the project files into the RC library and conf directories on lsf.

```bash
wget https://github.com/Azure/cyclecloud-lsf/archive/feature/rc.zip
unzip rc.zip
rc_source_dir="cyclecloud-lsf-feature-rc/specs/default/cluster-init/files/host_provider"

rc_scripts_dir=$LSF_SERVERDIR/../../resource_connector/azurecc/scripts
mkdir -p $rc_scripts_dir
cp $rc_source_dir/*.sh $rc_scripts_dir/
chmod +x $rc_scripts_dir/*.sh

mkdir -p $rc_scripts_dir/src/
cp $rc_source_dir/src/*.py $rc_scripts_dir/src/

```

2. Add the azurecc provider to the hostProvider file in the LSF conf directory: _$LSF_TOP/conf/resource_connector/hostProviders.json_

```json
{
  "providers": [
    {
      "type": "azureProv", 
      "name": "azurecc", 
      "scriptPath": "resource_connector/azurecc", 
      "confPath": "resource_connector/azurecc"
    }
  ]
}
```

### Configure azurecc provider

LSF will be communicating to CC via the azurecc resource connector.
The azurecc provider includes a CycleCloud host and cluster.
With a CycleCloud cluster configured add a provider entry to the azurecc provider file: _${LSF_TOP}/conf/resource_connector/azurecc/conf/azureccprov_config.json_

An example of the provider file with a single cluster is below. The user name and password correspond to a CycleCloud user.
This user should be assigned the _cyclecloud_access_ role. 

```json
{
    "log_level": "info",
    "cyclecloud": {
        "cluster": {
            "name": "lsf-cluster-example"
        },
        "config": {
            "username": "cycle-api-user",
            "password": "cycl34P1P4ss0rd",
            "web_server": "https://cyclecloud.contoso.com"
        },
        "termination_retirement": 120,
        "machine_request_retirement": 120
    }
}
```

The provider interactions will be logged to _$LSF_LOGDIR/azurecc_prov.log_.


### Edit cluster configuration for azurecc

There are recommended configurations for declaring resources.  Add the following lines to _${LSF_TOP}/conf/lsf.conf_:

```txt
LSB_RC_EXTERNAL_HOST_FLAG="azurecchost"
LSF_LOCAL_RESOURCES="[resource azurecchost]"
```

And also add the following resources to the Resource section of _${LSF_TOP}/conf/lsf.shared_:

```txt
   azurecchost  Boolean  ()       ()       (instances from Azure CycleCloud)
   nodearray  String     ()       ()       (nodearray from AzureCC)
```



### Configure the azurecc provider templates (Optional)

_$LSF_TOP/conf/resource_connector/azurecc/conf/azureccprov_templates.json_ 

This file isn't required, cyclecloud will populate the default contents of
the provider template file based on the nodearrays in the CycleCloud cluster.

Any host factory attributes can be provided in this file as an override.

```json
{
  "templates" : [
    {
      "templateId" : "execute",
      "attributes" : { 
        "ncores": ["Numeric", "2"],
        "ncpus": ["Numeric", "2"]
      }
    },
    {
      "templateId" : "execute-mpi",
      "attributes" : {
        "ncores": ["Numeric", "16"],
        "ncpus": ["Numeric", "8"],
        "nodearray" : ["String" , "mpi"]
      },
    "customScriptUri": "https://clustermanage.blob.core.windows.net/utilities/scripts/user_data.sh"
    }
   ]
}
```

The `"templateId"` field corresponds to the nodearray name in the CycleCloud cluster. 
The `"nodearray"` attribute corresponds to the Resource in _lsf.shared_ and is used by the scheduler for job dispatching.

### Configure user_data.sh (Optional)

Configuring *LSF_LOCAL_RESOURCES* on hosts is important for job placement in azure.
User provided script, in the form of user_data.sh is the supported LSF mechanism for this.
CycleCloud has a default script that runs to advertise all (*) attributes in 
the in the template. It's recommended not to use a custom script unless necessary.


## Submit jobs

Once the cluster is running you can log into one of the master nodes and submit
jobs to the scheduler:

1. `cyclecloud connect master-1 -c my-lsf-cluster`
1. `bsub -R select[azurecchost] sleep 300`
1. You'll see an execute node start up and prepare to run jobs.
1. When the job queue is cleared, nodes will autoscale back down.

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
