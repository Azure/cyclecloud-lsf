import logging
import os
import sys
from logging.handlers import RotatingFileHandler
import json
import shutil
import fcntl
from cyclecli import UserError, ConfigError
from copy import deepcopy
import traceback
import subprocess

_logging_init = False


def init_logging(loglevel=logging.INFO, logfile=None):
    global _logging_init
    if logfile is None:
        logfile = "cyclecloud_rc.log"
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
    stderr_handler.setLevel(loglevel)
    stderr_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    
    logger.addHandler(stderr_handler)
    
    _logging_init = True
    
    return logger


class JsonStore:
    
    def __init__(self, name, directory, formatted=False):
        assert name not in ['hosts.json', 'requests.json'], "Illegal json name."
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
            self.lockfp = os.open(self.lockpath, os.O_EXCL)
            fcntl.flock(self.lockfp, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except IOError:
            self.logger.exception("Could not acquire lock - %s" % self.lockpath)
            return False
            
    def _unlock(self):
        try:
            os.close(self.lockfp)
        except IOError:
            self.logger.exception("Error closing lock - %s" % self.lockpath)
            
    def read(self):
        return self._read(do_lock=True)
            
    def _read(self, do_lock=True):
        if do_lock and not self._lock():
            raise RuntimeError("Could not get lock %s" % self.lockpath)
        
        if os.path.exists(self.path):
            try:
                with open(self.path) as fr:
                    self.data = json.load(fr)
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
            json.dump(self.data, fw, indent=indent)
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
            except UserError as ue:
                with_message = deepcopy(response)
                message = str(ue)
                try:
                    message_data = json.loads(message)
                    message = "Http Status %(Code)s: %(Message)s" % message_data
                except Exception:
                    pass
                
                with_message["message"] = message
                return args[0].json_writer(with_message)
            except Exception as e:
                logger.exception(str(e))
                with_message = deepcopy(response)
                with_message["message"] = str(e)
                return args[0].json_writer(with_message)
            except:  # nopep8 ignore the bare except
                logger.exception(str(e))
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

            value = top_value.get(keys[n])
            
            if n == len(keys) - 1 and value is not None:
                return value
            
            top_value = value
            
        if top_value is None:
            try:
                return self.jetpack_config.get(key, default_value)
            except ConfigError as e:
                if key in str(e):
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


class Hostnamer:
    
    def __init__(self, use_fqdn=True):
        self.use_fqdn = use_fqdn
    
    def hostname(self, private_ip_address):
        toks = [x.strip() for x in subprocess.check_output(["getent", "hosts", private_ip_address]).split()]
        if self.use_fqdn:
            if len(toks) >= 2:
                return toks[1]
            return toks[0]
        else:
            return toks[-1]
