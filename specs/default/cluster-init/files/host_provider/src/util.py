import collections
from copy import deepcopy
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import shutil
import subprocess
import sys
import traceback
import random
from cyclecliwrapper import UserError


try:
    import cyclecli
except ImportError:
    import cyclecliwrapper as cyclecli
    

_logging_init = False


def init_logging(loglevel=logging.INFO, logfile=None, stderr_loglevel=logging.DEBUG):
    global _logging_init
    if logfile is None:
        logfile = "azurecc_prov.log"
    logfile_path = os.path.join(os.getenv("PRO_LSF_LOGDIR", "/tmp"), logfile)
    
    try:
        import jetpack
        jetpack.util.setup_logging()
        for handler in logging.getLogger().handlers:
            handler.setLevel(logging.ERROR)
    except ImportError:
        pass
    
    # this is really chatty
    requests_logger = logging.getLogger("requests.packages.urllib3.connectionpool")
    requests_logger.setLevel(logging.WARN)
    
    logger = logging.getLogger("cyclecloud")
    
    if _logging_init:
        return logger
    
    logger.setLevel(logging.DEBUG)
    
    tenMB = 10 * 1024 * 1024
    logfile_handler = RotatingFileHandler(logfile_path, maxBytes=tenMB, backupCount=5)
    logfile_handler.setLevel(loglevel)
    logfile_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    logger.addHandler(logfile_handler)
    
    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.setLevel(stderr_loglevel)
    stderr_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    
    logger.addHandler(stderr_handler)
    
    _logging_init = True
    
    return logger


class JsonStore:
    
    def __init__(self, name, directory, formatted=False):
        self.path = os.path.join(directory, name)
        self.lockpath = self.path + ".lock"
        if not os.path.exists(self.lockpath):
            with open(self.lockpath, "a"):
                pass
        
        self.formatted = formatted
        self.data = None
        self.lockfp = None
        self.logger = init_logging()
    
    def _lock(self):
        try:
            self.lockfp = open(self.lockpath, 'w')
            fcntl.lockf(self.lockfp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except IOError:
            self.logger.exception("Could not acquire lock - %s" % self.lockpath)
            return False
            
    def _unlock(self):
        try:
            self.lockfp.close()
        except IOError:
            self.logger.exception("Error closing lock - %s" % self.lockpath)
            
    def read(self):
        return self._read(do_lock=True)
            
    def _read(self, do_lock=True):
        if do_lock and not self._lock():
            raise RuntimeError("Could not get lock %s" % self.lockpath)
        
        if os.path.exists(self.path):
            try:
                self.data = load_json(self.path)
            except Exception:
                self.logger.exception("Could not reload %s - hosts may need to be manually removed from the system's hosts.json file." % self.path)
                self.data = {}
        else:
            self.data = {}
        
        if do_lock:
            self._unlock()
            
        return self.data
    
    def __enter__(self):
        if not self._lock():
            raise RuntimeError("Could not get lock %s" % self.lockpath)
        return self._read(do_lock=False)
            
    def __exit__(self, *args):
        with open(self.path + ".tmp", "w") as fw:
            indent = 2 if self.formatted else None
            json.dump(self.data, fw, indent=indent, sort_keys=True)
        shutil.move(self.path + ".tmp", self.path)
        self._unlock()
        

def failureresponse(response):
    '''
    Decorator to ensure that a sane default response is always sent back to LSF.
    '''
    def decorator(func):
        def _wrap(*args, **kwargs):
            logger = init_logging()
            try:
                return func(*args, **kwargs)
            except cyclecli.UserError as ue:
                with_message = deepcopy(response)
                message = unicode(ue)
                logger.debug(traceback.format_exc())
                
                try:
                    message_data = json.loads(message)
                    message = "Http Status %(Code)s: %(Message)s" % message_data
                except Exception:
                    pass
                
                with_message["message"] = message
                return args[0].json_writer(with_message)
            except Exception as e:
                logger.exception(unicode(e))
                logger.debug(traceback.format_exc())
                with_message = deepcopy(response)
                with_message["message"] = unicode(e)
                return args[0].json_writer(with_message)
            except:  # nopep8 ignore the bare except
                logger.exception(unicode(e))
                logger.debug(traceback.format_exc())
                with_message = deepcopy(response)
                with_message["message"] = traceback.format_exc()
                return args[0].json_writer(with_message)
        return _wrap
    return decorator


class ProviderConfig:
    
    def __init__(self, config, jetpack_config=None):
        self.config = config
        self.logger = init_logging()
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
                self.logger.warn("Invalid format, as a child key was specified for %s when its type is %s ", key, type(top_value))
                return {}
                
            value = top_value.get(keys[n])
            
            if n == len(keys) - 1 and value is not None:
                return value
            
            top_value = value
            
        if top_value is None:
            try:
                return self.jetpack_config.get(key, default_value)
            except cyclecli.ConfigError as e:
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


def provider_config_from_environment(pro_conf_dir=os.getenv('PRO_CONF_DIR', os.getcwd())):
    config_file = os.path.join(pro_conf_dir, "conf", "azureccprov_config.json")
    templates_file = os.path.join(pro_conf_dir, "conf", "azureccprov_templates.json")
    
    delayed_log_statements = []
    
    # on disk configuration
    config = {}
    if os.path.exists(config_file):
        delayed_log_statements.append((logging.DEBUG, "Loading provider config: %s" % config_file))
        config = load_json(config_file)
    else:
        try:
            with open(config_file, "w") as fw:
                json.dump({}, fw)
            delayed_log_statements.append((logging.WARN, "Provider config does not exist, creating an empty one: %s" % config_file))
        except IOError:
            delayed_log_statements.append((logging.DEBUG, "Provider config does not exist and can't write a default one: %s" % config_file))
            
    import logging as logginglib
    log_level_name = config.get("log_level", "info")
    
    log_levels = {
        "debug": logginglib.DEBUG,
        "info": logginglib.INFO,
        "warn": logginglib.WARN,
        "error": logginglib.ERROR
    }
    
    fine = False
    if log_level_name.lower() == "fine":
        fine = True
        log_level_name = "debug"
    
    if log_level_name.lower() not in log_levels:
        delayed_log_statements.append(((logging.WARN, "Unknown logging level: %s" % log_level_name.lower())))
        log_level_name = "info"
    
    logger = init_logging(log_levels[log_level_name.lower()])
    
    for level, message in delayed_log_statements:
        logger.log(level, message)
    
    # on disk per-nodearray template override
    customer_templates = {}
    if os.path.exists(templates_file):
        logger.debug("Loading template overrides: %s" % templates_file)
        customer_templates = load_json(templates_file)
    else:
        try:
            with open(templates_file, "w") as fw:
                json.dump({}, fw)
            logger.info("Template overrides file does not exist, wrote an empty one: %s" % templates_file)
        except IOError:
            logger.debug("Template overrides file does not exist and can't write a default one: %s" % templates_file)
    
    # don't let the user define these in two places
    if config.pop("templates", {}):
        logger.warn("Please define template overrides in %s, not the azureccprov_config.json" % templates_file)
    
    # and merge them so it is transparent to the code
    flattened_templates = {}
    for template in customer_templates.get("templates", []):
        
        if "templateId" not in template:
            logger.warn("Skipping template because templateId is not defined: %s", template)
            continue
        
        nodearray = template.pop("templateId")  # definitely don't want to rename them as machineId
        
        if nodearray in flattened_templates:
            logger.warn("Ignoring redefinition of templateId %s", nodearray)
            continue
        
        flattened_templates[nodearray] = template
        
    config["templates"] = flattened_templates
    
    return ProviderConfig(config), logger, fine


def custom_chaos_mode(action):
    def wrapped(func):
        return chaos_mode(func, action)
    return wrapped


def chaos_mode(func, action=None):
    def default_action():
        raise random.choice([RuntimeError, ValueError, UserError])("Random failure")
    
    action = action or default_action
    
    def wrapped(*args, **kwargs):
        if is_chaos_mode():
            return action()
            
        return func(*args, **kwargs)
    
    return wrapped


def is_chaos_mode():
    return random.random() < float(os.getenv("AZURECC_CHAOS_MODE", 0))


class Hostnamer:
    
    def __init__(self, use_fqdn=True):
        self.use_fqdn = use_fqdn
        self._bhost_cache = {}
    
    @custom_chaos_mode(lambda: None)
    def hostname(self, private_ip_address):
        try:
            toks = [x.strip() for x in subprocess.check_output(["getent", "hosts", private_ip_address]).split()]
            if self.use_fqdn:
                if len(toks) >= 2:
                    return toks[1]
                return toks[0]
            else:
                return toks[-1]
        except Exception as e:
            logging.error(str(e))
            return None
    
    @custom_chaos_mode(lambda: None)
    def private_ip_address(self, hostname):
        '''
        Tries to look up the private ip based on the existing bhosts -rconly -w private ip listed. If that fails, 
        it uses getent.
        '''
        try:
            if not self._bhost_cache:
                for line in subprocess.check_output(["bhosts", "-rconly", "-w"]).splitlines():
                    toks = line.split()
                    
                    if len(toks) < 8:
                        continue
                    
                    if toks[0] == "PUB_DNS_NAME":
                        continue
                    
                    self._bhost_cache[toks[2].lower()] = toks[3]
            
            if hostname.lower() in self._bhost_cache:
                return self._bhost_cache[hostname.lower()]
            
            logging.warn("Could not find %s in bhosts -rconly -w. Trying getent", hostname)    
        except Exception:
            logging.exception("Could not execute bhosts -rconly -w.")
        
        try:
            toks = [x.strip() for x in subprocess.check_output(["getent", "hosts", hostname]).split()]
            return toks[0]
        except Exception as e:
            logging.error(str(e))
            return None
    
        
def load_json(path):
    with open(path) as fr:
        return json.load(fr, object_pairs_hook=collections.OrderedDict)
