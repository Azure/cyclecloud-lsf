## Building an Azure VM Image for LSF (using Packer)

This folder contains automated scripts for creating an Azure VM Image for use
with the LSF cluster type in CycleCloud. Below are instructions for running the 
image builder.

This build routine requires LSF install packages and entitlement files:
* lsf10.1_lsfinstall_linux_x86_64.tar.Z
* lsf10.1_lnx310-lib217-x86_64-520099.tar.Z
* lsf10.1_lnx310-lib217-x86_64-529611.tar.Z
* lsf_std_entitlement.dat

Place these files in the _/blobs_ directory.

1. [Install Packer](https://www.packer.io/intro/getting-started/install.html)
2. Enter your Azure subscription information (including Service Principal details)
in _env.sh_
3. Review _install_lsf.sh_, make sure to update the install location `export LSF_TOP_INSTALL="/grid/lsf"` if there is a preferred install location.
4. Add the LSF installer files to the _/blobs_ directory.
5. Note that _build.json_ specifies an CentOS base image. To change the 
starting image, modify this file.
6. Run the build with `source env.sh && run_build.sh`

Note what value was used for `LSF_TOP_INSTALL` because this configuration will
be needed for the LSF cluster.