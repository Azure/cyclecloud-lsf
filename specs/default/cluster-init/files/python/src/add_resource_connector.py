'''
Used during converge to register azure_cyclecloud as a resource provider.
'''
import json
import shutil


def update_hostsProviders():
    final_path = "/usr/share/lsf/resource_connector/hostProviders.json"

    connector_data = {
        "providers": [ {
                "name": "azurecc",
                "type": "azureProv",
                "confPath": "resource_connector/azurecc",
                "scriptPath": "resource_connector/azurecc"
            }
        ]
    }
    
    shutil.copy(final_path, final_path + ".bkp")
    with open(final_path, "w") as fw:
        json.dump(connector_data, fw, indent=4)
        
        
def add_azurecc_resources():
    path = '/usr/share/lsf/conf/lsf.shared'
    with open(path) as fr:
        lines = fr.readlines()
    
    for line in lines:
        if line.strip().startswith("#"):
            continue
        if "azurehost" in line and "Boolean" in line:
            return
    
    end_resource_i = len(lines) - list(reversed([l.strip() for l in lines])).index("End Resource")
    lines = lines[:end_resource_i - 1] + ["   azurehost  Boolean    ()       ()       (instances from Azure)\n"] + lines[end_resource_i:]
    with open(path + ".tmp", "w") as fw:
        fw.write("".join(lines))
        
        
    update_hostsProviders()
    add_azurecc_resources()
        

if __name__ == "__main__":
    main()
