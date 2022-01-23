import argparse
import os
import pickle
import sys


from . import cloud, proxy, client


def error(msg):
    print("Error: %s" % msg)
    sys.exit()


def parse_config():
    parser = argparse.ArgumentParser(description="BeeDrive Command Line Launcher!")
    parser.add_argument("service",
                        help="whice service you need?",
                        choices=["cloud", "upload", "download", "proxy"],
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

    parser.add_argument("-reset_config",
                        help="reset default configure file [y|n]",
                        default="n",
                        choices=["y", "n"])

    parser.add_argument("-custom_config",
                        help="launch service with your custom configure file",
                        type=str)
    args = parser.parse_args()
    args.reset = args.reset_config == "y"
    config = pickle.load(open(args.custom_config, "rb")) if args.custom_config else {}
    if args.reset and config:
        error("-reset_config and -custom_config")
    return args, config


def main():
    args, config = parse_config()
    if args.mode == "app":
        try:
            import PySimpleGUI
        except ImportError:
            error("No GUI supported. \nTry: pip install PySimpleGUI ")

    if args.service == "proxy":
        if not args.arg1:
            error("Miss port argument. \nTry: python -m beedrive proxy 8889")
        proxy.proxy_forever(args.arg1)

    elif args.service == "cloud":
        if args.mode == "app":
            cloud.cloud_gui()
        else:
            cloud.cloud_cmd(args.arg1, args.arg2, args.reset, config)

    elif args.service == "upload":
        if args.mode == "app":
            client.upload_gui()
        elif not args.arg1:
            error("Miss source file. \nTry: python -m beecloud upload myfile.txt")
        else:
            client.upload_cmd(args.arg1, args.reset, config)

    elif args.service == "download":
        if args.mode == "app":
            client.download_gui()
        elif not args.arg1:
            error("Miss target file. \nTry: python -m beecloud download myfile.txt")
        else:
            client.download_cmd(args.arg1, args.arg2, args.reset, config)
            
        
if __name__ == "__main__":
    main()
