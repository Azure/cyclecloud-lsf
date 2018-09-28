'''
Used during converge to register azure_cyclecloud as a LSF RC provider plugin.
'''
import json
import shutil
import os
import util


logger = util.init_logging(logfile="cyclecloud_rc_install.log")


def update_hostsProviders(output_writer):
    logger.info("Update hostsProvider.json")
    
    connector_data = {"providers": [{"name": "azurecc",
                                     "type": "azureProv",
                                     "confPath": "resource_connector/azurecc",
                                      "scriptPath": "resource_connector/azurecc"
                                     }]
    }
    
    json.dump(connector_data, output_writer, indent=4)
    
    
def add_provider_json(output_writer):
    
    provider = {'host_type': 'azure_host',
                 'interfaces': [{'action': 'resource_connector/azurecc/scripts/getAvailableTemplates.sh',
                                 'name': 'getAvailableTemplates'},
                                {'action': 'resource_connector/azurecc/scripts/requestMachines.sh',
                                 'name': 'requestMachines'},
                                {'action': 'resource_connector/azurecc/scripts/requestReturnMachines.sh',
                                 'name': 'requestReturnMachines'},
                                {'action': 'resource_connector/azurecc/scripts/getRequestStatus.sh',
                                 'name': 'getRequestStatus'},
                                {'action': 'resource_connector/azurecc/scripts/getReturnRequests.sh',
                                 'name': 'getReturnRequests'}]}
    json.dump(provider, output_writer, indent=4)
        
        
def add_azurecc_resources(input_lines):
    logger.info("Seeing if azurehost is defined in lsf.shared")

    for line in input_lines:
        
        if line.strip().startswith("#"):
            continue
        
        if "azurehost" in line and "Boolean" in line:
            logger.info("'azurehost' is already defined in lsf.shared.")
            return input_lines
    
    end_resource_i = len(input_lines) - list(reversed([l.strip() for l in input_lines])).index("End Resource")
    
    logger.info("Defining azurehost at line %d" % (end_resource_i + 1))
    lines = input_lines[:end_resource_i - 1] + ["   azurehost  Boolean    ()       ()       (instances from Azure)\n"] + input_lines[end_resource_i - 1:]
    return lines


def enable_schmod_demand(input_lines):
    logger.info("Update lsb.modules to enable schmod_demand")
    in_plugin_module = False
    ret = []
    for line in input_lines:
        in_plugin_module = in_plugin_module or line.strip().lower().split() == ["begin", "pluginmodule"]
        in_plugin_module = in_plugin_module and line.strip().lower().split() != ["end", "pluginmodule"]
        
        if in_plugin_module and line.strip().startswith("#"):
            line_less_comment = line.strip()[1:].strip()
            if line_less_comment.startswith("schmod_demand"):
                logger.info("Uncommenting schmod_demand")
                ret.append(line_less_comment + "\n")
                continue
        ret.append(line)
    return ret
    
    
def backup_path(path):
    if not os.path.exists(path + ".bkp") and os.path.exists(path):
        shutil.copyfile(path, path + ".bkp")


def main():
    lsf_shared_path = os.path.join(os.getenv('LSF_ENVDIR', '/usr/share/lsf/conf'), 'lsf.shared')
    host_providers_json = os.path.join(os.getenv('LSF_ENVDIR', '/usr/share/lsf/conf'), 'resource_connector/hostProviders.json')
    provider_json = os.path.join(os.getenv('LSF_ENVDIR', '/usr/share/lsf/conf'), 'resource_connector/azurecc/provider.json')
    lsb_modules_path = os.path.join(os.getenv('LSF_ENVDIR', '/usr/share/lsf/conf'), "lsbatch/azure/configdir/lsb.modules")
    
    backup_path(host_providers_json)
    backup_path(lsf_shared_path)
    backup_path(lsb_modules_path)
        
    with open(host_providers_json, "w") as fw:
        update_hostsProviders(fw)
        
    with open(provider_json, "w") as fw:
        add_provider_json(fw)
    
    with open(lsf_shared_path) as fr:
        lsf_shared_lines = fr.readlines()
        
    with open(lsf_shared_path, "w") as fw:
        fw.write("".join(add_azurecc_resources(lsf_shared_lines)))
    
    with open(lsb_modules_path) as fr:
        lsf_shared_lines = fr.readlines()
        
    with open(lsb_modules_path, "w") as fw:
        fw.write("".join(enable_schmod_demand(lsf_shared_lines)))


if __name__ == "__main__":
    main()
