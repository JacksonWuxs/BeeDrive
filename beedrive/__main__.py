import argparse
import sys
import os
import pickle


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
                    help="reset default configure file setting [y|n]",
                    default="n",
                    choices=["y", "n"])

parser.add_argument("-custom_config",
                    help="launch service with your custom configure file",
                    type=str)


args = parser.parse_args()
reset = args.reset_config == "y"
if args.custom_config:
    path = args.use_custom_config
    if not path.endswith(".bee"):
        print("BeeDrive configure file should end with .bee")
        sys.exit()
    if not os.path.exists(path):
        print("Cannot open file: %s" % path)
        sys.exit()
    config = pickle.load(open(path, "rb"))
else:
    config = {}
if reset and config:
    print("Cannot reset default config and use coustom config at the same time.")
    sys.exit()
    

if args.mode == "app":
    try:
        import PySimpleGUI
    except ImportError:
        print("No GUI supported on this environment. \nTry: pip install PySimpleGUI ")
        sys.exit()

if args.service == "proxy":
    if not args.arg1:
        print("Launch Proxy service needs one more argument to set port.")
        sys.exit()
    from . import proxy
    proxy.proxy_forever(args.arg1)

elif args.service == "cloud":
    from . import cloud
    if args.mode == "app":
        cloud.cloud_gui()
    else:
        cloud.cloud_cmd(args.arg1, args.arg2, reset, config)

elif args.service == "upload":
    from .import client
    if args.mode == "app":
        client.upload_gui()
    elif not args.arg1:
        print("Missing file path to upload, try: python -m beecloud upload myfile.txt")
        sys.exit()
    else:
        client.upload_cmd(args.arg1, reset, config)

elif args.service == "download":
    from . import client
    if args.mode == "app":
        client.download_gui()
    elif not args.arg1:
        print("Missing file path to upload, try: python -m beecloud upload myfile.txt")
        sys.exit()
    else:
        client.download_cmd(args.arg1, args.arg2,
                          reset, config)
    
