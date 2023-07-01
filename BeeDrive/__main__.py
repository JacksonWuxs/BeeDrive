import argparse
import os
import pickle
import sys


from . import cloud, proxy, client, __version__, __date__
from .lib.logger import callback


def error(msg):
    callback(msg, "error")
    sys.exit()


def parse_params():
    parser = argparse.ArgumentParser(description="BeeDrive Command Line Launcher!")
    parser.add_argument("service",
                        help="whice service you need?",
                        nargs="?",
                        choices=["cloud", "upload", "download", "proxy", "command"],
                        type=str)

    parser.add_argument("arg1", help="the first additional argument (optional)",
                        nargs="?", default="")

    parser.add_argument("arg2", help="the second additional argument (optional)",
                        nargs="?", default="")

    parser.add_argument("-mode",
                        help="work on Command Line or Window Application?",
                        choices=["app", "cmd"],
                        default="cmd",
                        type=str)

    parser.add_argument("-config",
                        help="command to control configure files",
                        choices=["", "check", "reset"],
                        default="",
                        type=str)

    parser.add_argument("-version", nargs="?", default="",
                        help="check the version of current BeeDrive service")
    return parser.parse_args()


def main():
    args = parse_params()
    if args.version is None:
        callback("BeeDrive-%s (%s) at %s" % (__version__,
                                             __date__,
                                             os.path.dirname(os.path.abspath(__file__))))
        sys.exit()
    
    if args.mode == "app":
        try:
            import PySimpleGUI
        except ImportError:
            error("No GUI supported. \nTry: pip install PySimpleGUI ")

    if args.service == "proxy":
        if not args.arg1:
            error("Miss port argument. \nTry: python -m BeeDrive proxy 8889")
        if not args.arg2:
            args.arg2 = 16
        proxy.proxy_forever(args.arg1, args.arg2)
        sys.exit()

    
    if args.service == "cloud":
        config = cloud.cmd_manage_config(args.config)
    else:
        config = client.cmd_manage_config(args.config)

    if args.config != "":
        sys.exit()

    elif args.service == "command":
        client.command_cmd(config)
        
    elif args.service == "cloud":
        if args.mode == "app":
            cloud.cloud_gui()
        else:
            cloud.cloud_cmd(args.arg1, args.arg2, config)

    elif args.service == "upload":
        if args.mode == "app":
            client.upload_gui()
        elif not args.arg1:
            error("Missing source file. \nTry: python -m beecloud upload myfile.txt")
        else:
            client.upload_cmd(args.arg1, config)

    elif args.service == "download":
        if args.mode == "app":
            client.download_gui()
        elif not args.arg1:
            error("Missing target file. \nTry: python -m beecloud download myfile.txt")
        else:
            client.download_cmd(args.arg1, args.arg2, config)

    else:
        print("Please assign a service name (cloud, proxy, upload, download)")
        print("Using command semms like: BeeDrive cloud")
            
        
if __name__ == "__main__":
    main()
