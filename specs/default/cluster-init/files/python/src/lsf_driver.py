import argparse
import lsfwrapper
import json
import sys


def parse_args(argv=None):
    parser = argparse.ArgumentParser("Example: lsf_driver.py --queue cloudq -p")
    parser.add_argument("--version", dest="version", action="store_true", default=False)
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=False)
    parser.add_argument("-q", "--queue", dest="queue_name", help="Name of the queue")
    parser.add_argument("-p", "--limits", dest="policies_and_limits", action="store_true", default=False, help="include policies and limits")
    parser.add_argument("-u", "--busers", dest="return_busers_data", action="store_true", default=False, help="return busers data")
    parser.add_argument("--pretty", dest="pretty", action="store_true", default=False, help="pretty print json")
    return parser.parse_args(argv)


def version():
    import version as versionlib
    print versionlib.VERSION


def go(args):
    lsf = lsfwrapper.LsfWrapper()
    
    if args.return_busers_data:
        indent = None
        if args.pretty:
            indent = 2
        json.dump(lsf.lsb_userinfo2(), sys.stdout, indent=indent)
        return
    
    lsf.lsb_readjobinfo()
    

if __name__ == "__main__":
    go(parse_args())
