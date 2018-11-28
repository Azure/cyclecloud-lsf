import version


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
                s.headers = {"X-Cycle-Client-Version": "%s-cli:%s" % ("cyclecloud-lsf", version.get_version())}
            
                return s
            except requests.exceptions.SSLError:
                retries = retries - 1
                if retries < 1:
                    raise
    except ImportError:
        raise
