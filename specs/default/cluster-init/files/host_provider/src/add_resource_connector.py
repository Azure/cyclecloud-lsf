'''
Used during converge to register azure_cyclecloud as a resource provider.
'''
import json
import shutil
import os
import util


logger = util.init_logging()


def update_hostsProviders(output_writer):
    logger.info("Update hostsProvider.json")
    connector_data = {"providers": [{"name": "azurecc",
                                     "type": "azureProv",
                                     "confPath": "resource_connector/azurecc",
                                      "scriptPath": "resource_connector/azurecc"
                                     }]
    }
    
    json.dump(connector_data, output_writer, indent=4)
        
        
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
    
    
def backup_path(path):
    if not os.path.exists(path + ".bkp") and os.path.exists(path):
        shutil.copyfile(path, path + ".bkp")


def main():
    lsf_shared_path = os.path.join(os.getenv('LSF_TOP', '/usr/share/lsf'), 'conf/lsf.shared')
    host_providers_json = os.path.join(os.getenv('LSF_TOP', '/usr/share/lsf'), 'resource_connector/hostProviders.json')
    
    backup_path(host_providers_json)
    backup_path(lsf_shared_path)
        
    with open(lsf_shared_path) as fr:
        lsf_shared_lines = fr.readlines()
    
    with open(host_providers_json, "w") as fw:
        update_hostsProviders(fw)
    
    with open(lsf_shared_path, "w") as fw:
        fw.write("".join(add_azurecc_resources(lsf_shared_lines)))
        

if __name__ == "__main__":
    main()
