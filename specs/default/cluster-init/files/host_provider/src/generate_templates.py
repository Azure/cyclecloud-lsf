from copy import deepcopy
import json
import logging
import pprint
import sys


try:
    from cyclecli import UserError
    from cyclecli import ConfigError
except ImportError:
    class UserError(Exception):
        pass
    
    class ConfigError(Exception):
        pass


def get_session(config):
    try:
        retries = 3
        while retries > 0:
            try:
                import requests

                if not config["verify_certificates"]:
                    try:
                        from requests.packages import urllib3
                        if hasattr(urllib3, "disable_warnings"):
                            urllib3.disable_warnings()
                    except ImportError:
                        pass
            
                s = requests.session()
                s.auth = (config["username"], config["password"])
                s.timeout = config["cycleserver"]["timeout"]
                s.verify = config["verify_certificates"]  # Should we auto-accept unrecognized certs?
                s.headers = {"X-Cycle-Client-Version": "%s-cli:%s" % ("cyclecloud-lsf", "3.0.0")}
            
                return s
            except requests.exceptions.SSLError:
                retries = retries - 1
                if retries < 1:
                    raise
    except ImportError:
        raise


class ProviderConfig:
    
    def __init__(self, config, jetpack_config=None):
        self.config = config
        if jetpack_config is None:
            try:
                import jetpack
                jetpack_config = jetpack.config 
            except ImportError:
                jetpack_config = {}
        self.jetpack_config = jetpack_config
        
    def get(self, key, default_value=None):
        if not key:
            return self.config
        
        keys = key.split(".")
        top_value = self.config
        for n in range(len(keys)):
            if top_value is None:
                break
            
            if not hasattr(top_value, "keys"):
                logging.warn("Invalid format, as a child key was specified for %s when its type is %s ", key, type(top_value))
                return {}
                
            value = top_value.get(keys[n])
            
            if n == len(keys) - 1 and value is not None:
                return value
            
            top_value = value
            
        if top_value is None:
            try:
                return self.jetpack_config.get(key, default_value)
            except ConfigError as e:
                if key in unicode(e):
                    return default_value
                raise
        
        return top_value
    
    def set(self, key, value):
        keys = key.split(".")
        
        top_value = self.config
        for top_key in keys[:-1]: 
            tmp_value = top_value.get(top_key, {})
            top_value[top_key] = tmp_value
            top_value = tmp_value
            
        top_value[keys[-1]] = value
        
        
class Cluster:
    
    def __init__(self, cluster_name, provider_config):
        self.cluster_name = cluster_name
        self.provider_config = provider_config
    
    def status(self):
        return self.get("/clusters/%s/status" % self.cluster_name)
            
    def _session(self):
        config = {"verify_certificates": False,
                  "username": self._get_or_raise("cyclecloud.config.username"),
                  "password": self._get_or_raise("cyclecloud.config.password"),
                  "cycleserver": {
                      "timeout": 60
                  }
        }
        return get_session(config=config)
    
    def _get_or_raise(self, key):
        value = self.provider_config.get(key)
        if not value:
            #  jetpack.config.get will raise a ConfigError above.
            raise ConfigError("Please define key %s in the provider config." % key)
        return value

    def get(self, url, **params):
        root_url = self._get_or_raise("cyclecloud.config.web_server")
        logging.debug("GET %s with params %s", root_url + url, params)
        session = self._session()
        response = session.get(root_url + url, params=params)
        if response.status_code < 200 or response.status_code > 299:
            raise ValueError(response.content)
        return json.loads(response.content)


class InvalidCycleCloudVersionError(RuntimeError):
    pass


def _escape_id(name):
    return name.lower().replace("_", "")


def templates(cluster, stdout_writer, config):
    """
    input (ignored):
    []
    
    output:
    {'templates': [{'attributes': {'cyclecloudhost': ['Boolean', 1],
                           'mem': ['Numeric', '2048'],
                           'ncores': ['Numeric', '4'],
                           'ncpus': ['Numeric', '4'],
                           'type': ['String', 'X86_64'],
                           'zone': ['String', 'southeastus']},
            'instanceTags': 'group=project1',
            'maxNumber': 10,
            'pgrpName': None,
            'priority': 0,
            'templateId': 'execute0'},
           {'attributes': {'cyclecloudhost': ['Boolean', '1'],
                           'mem': ['Numeric', '4096'],
                           'ncores': ['Numeric', '8'],
                           'ncpus': ['Numeric', '8'],
                           'type': ['String', 'X86_64'],
                           'zone': ['String', 'southeastus']},
            'instanceTags': 'group=project1',
            'maxNumber': 10,
            'pgrpName': None,
            'priority': 0,
            'templateId': 'execute1'}]}
    """
    
    # returns Cloud.Node records joined on MachineType - the array node only
    response = cluster.status()

    nodearrays = response["nodearrays"]
    
    if "nodeArrays" in nodearrays:
        logging.error("Invalid CycleCloud version. Please upgrade your CycleCloud instance.")
        raise InvalidCycleCloudVersionError("Invalid CycleCloud version. Please upgrade your CycleCloud instance.")
    
    currently_available_templates = set()
    
    # currently the REST api doesn't tell us which bucket is active, so we will manually figure that out by inspecting
    # the MachineType field on the nodearray
    active_machine_types_by_nodearray = {}
    for nodearray_root in nodearrays:
        nodearray = nodearray_root.get("nodearray")
        machine_types = nodearray.get("MachineType")
        if isinstance(machine_types, basestring):
            machine_types = [m.strip().lower() for m in machine_types.split(",")]
            
        active_machine_types_by_nodearray[nodearray_root["name"]] = set(machine_types)
                             
    default_priority = len(nodearrays) * 10
    
    for nodearray_root in nodearrays:
        nodearray = nodearray_root.get("nodearray")
        
        # legacy, ignore any dynamically created arrays.
        if nodearray.get("Dynamic"):
            continue
        
        # backward compatability
        has_worker_recipe = "recipe[lsf::worker]" in nodearray.get("Configuration", {}).get("run_list", [])
        is_autoscale = nodearray.get("Configuration", {}).get("lsf", {}).get("autoscale", False)
        if not has_worker_recipe and not is_autoscale:
            continue
        
        output = {"templates": []}
        
        for bucket in nodearray_root.get("buckets"):
            machine_type_name = bucket["definition"]["machineType"]
            if machine_type_name.lower() not in active_machine_types_by_nodearray[nodearray_root["name"]]:
                continue
            
            machine_type_short = machine_type_name.lower().replace("standard_", "").replace("basic_", "").replace("_", "")
            machine_type = bucket["virtualMachine"]
            
            # LSF hates special characters
            nodearray_name = nodearray_root["name"]
            template_id = "%s%s" % (nodearray_name, machine_type_name)
            template_id = _escape_id(template_id)
            currently_available_templates.add(template_id)
            
            max_count = bucket.get("quotaCount")
            available_count = bucket.get("maxCount")

            memory = machine_type.get("memory") * 1024
            is_low_prio = nodearray.get("Interruptible", False)
            ngpus = 0
            try:
                # if the user picks a non-gpu machine ngpus will actually be defined as None.
                ngpus = int(nodearray.get("Configuration", {}).get("lsf", {}).get("ngpus") or 0)
            except ValueError:
                logging.exception("Ignoring lsf.ngpus for nodearray %s" % nodearray_name)
            
            record = {
                "availableNumber": available_count,
                "maxNumber": max_count,
                "templateId": template_id,
                "nodeArray": nodearray_name,
                "vmType": machine_type_name,
                "priority": nodearray.get("Priority", default_priority),
                "attributes": {
                    "zone": ["String", nodearray.get("Region")],
                    "mem": ["Numeric", memory],
                    "ncpus": ["Numeric", machine_type.get("vcpuCount")],
                    "ncores": ["Numeric", machine_type.get("vcpuCount")],
                    "cyclecloudhost": ["Boolean", 1],
                    "type": ["String", "X86_64"],
                    "machinetypefull": ["String", machine_type_name],
                    "machinetype": ["String", machine_type_short],
                    "nodearray": ["String", nodearray_name],
                    "cyclecloudmpi": ["Boolean", 0],
                    "cyclecloudlowprio": ["Boolean", 1 if is_low_prio else 0]
                }
            }
            
            if ngpus:
                record["attributes"]["ngpus"] = ["Numeric", ngpus]
            
            attributes = generate_userdata(record)
            
            custom_env = _parse_UserData(record.pop("UserData", "") or "")
            record["UserData"] = {"lsf": {}}
            
            if custom_env:
                record["UserData"]["lsf"] = {"custom_env": custom_env,
                                             "custom_env_names": " ".join(sorted(custom_env.iterkeys()))}
            
            record["UserData"]["lsf"]["attributes"] = attributes
            record["UserData"]["lsf"]["attribute_names"] = " ".join(sorted(attributes.iterkeys()))
            
            output["templates"].append(record)
            
            for n, placement_group in enumerate(_placement_groups(nodearray_name, config)):
                template_id = record["templateId"] + placement_group
                # placement groups can't be the same across templates. Might as well make them the same as the templateid
                namespaced_placement_group = template_id
                if is_low_prio:
                    break
                
                record_mpi = deepcopy(record)
                record_mpi["placementGroupName"] = namespaced_placement_group
                record_mpi["attributes"]["placementgroup"] = ["String", namespaced_placement_group]
                record_mpi["UserData"]["lsf"]["attributes"]["placementgroup"] = namespaced_placement_group
                record_mpi["attributes"]["cyclecloudmpi"] = ["Boolean", 1]
                record_mpi["UserData"]["lsf"]["attributes"]["cyclecloudmpi"] = True
                # regenerate names, as we have added placementgroup
                record_mpi["UserData"]["lsf"]["attribute_names"] = " ".join(sorted(record_mpi["attributes"].iterkeys()))
                record_mpi["priority"] = record_mpi["priority"] - n - 1
                record_mpi["templateId"] = template_id
                record_mpi["maxNumber"] = min(record["maxNumber"], nodearray.get("Azure", {}).get("MaxScalesetSize", 40))
                record_mpi["availableNumber"] = min(record_mpi["maxNumber"], record_mpi["availableNumber"])
                output["templates"].append(record_mpi)
                
            default_priority = default_priority - 10
    
    return json.dump(output, stdout_writer, indent=2)


def generate_userdata(template):
    ret = {}
    
    for key, value_array in template.get("attributes", {}).iteritems():
        if len(value_array) != 2:
            logging.error("Invalid attribute %s %s", key, value_array)
            continue
        if value_array[0].lower() == "boolean":
            ret[key] = str(str(value_array[1]) != "0").lower()
        else:
            ret[key] = value_array[1]
    
    if template.get("customScriptUri"):
        ret["custom_script_uri"] = template.get("customScriptUri")
        
    return ret

  
def _parse_UserData(user_data):
    ret = {}
    
    user_data = (user_data or "").strip()
    
    if not user_data:
        return ret
    
    key_values = user_data.split(";")
    
    # kludge: this can be overridden either at the template level
    # or during a creation request. We always want it defined in userdata
    # though.
    
    for kv in key_values:
        try:
            key, value = kv.split("=", 1)
            ret[key] = value
        except ValueError:
            logging.error("Invalid UserData entry! '%s'", kv)
    return ret


def _max_count(nodearray, machine_cores, bucket):
    if machine_cores < 0:
        logging.error("Invalid number of machine cores - %s", machine_cores)
        return -1
    
    max_count = bucket.get("maxCount")
    
    if max_count is not None:
        logging.debug("Using maxCount %s for %s", max_count, bucket)
        return max(-1, max_count)
    
    max_core_count = bucket.get("maxCoreCount")
    if max_core_count is None:
        if nodearray.get("maxCoreCount") is None:
            logging.error("Need to define either maxCount or maxCoreCount! %s", pprint.pformat(bucket))
            return -1
        logging.debug("Using maxCoreCount")
        max_core_count = nodearray.get("maxCoreCount")
    
    max_core_count = max(-1, max_core_count)
    
    return max_core_count / machine_cores
    

def _placement_groups(nodearray, config):
    return ["pg%s" % x for x in xrange(10)]


def main():  # pragma: no cover
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    try:
        provider_config = ProviderConfig({})
        cluster_name = provider_config.get("cyclecloud.cluster.name")
        cluster = Cluster(cluster_name, provider_config)
        templates(cluster, sys.stdout, provider_config)
        sys.exit(0)
    except ImportError as e:
        logging.exception(unicode(e))
        sys.exit(1)
    except Exception as e:
        logging.error(unicode(e))
        sys.exit(1)
            

if __name__ == "__main__":
    main()  # pragma: no cover
