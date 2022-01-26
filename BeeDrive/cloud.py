import os
import sys
import pickle
import time

from multiprocessing import cpu_count

from .core.Server import LocalServer
from .core.Proxy import LocalRelay
from .core.utils import analysis_ip, resource_path, trust_sleep
from .configures import save_config, load_config


def parse_users(string):
    if len(string) == 0:
        return []
    return [_.split(":", 1) for _ in string.split(";") if len(_) > 0]


class ConfigLauncher:
    def __init__(self, config):
        self.config = config
        self.hosts = [LocalRelay(proxy, config["rport"], config["sport"], config["pname"]) \
                           for proxy in config["proxy"]]
        self.server = LocalServer(users=config["users"], port=config["sport"],
                                  save_path=config["spath"], max_manager=config["manager"],
                                  max_worker=config["worker"])

    def start(self):
        self.server.start()
        for each in self.hosts:
            each.start()

    def stop(self):
        for each in self.hosts:
            each.stop()
        self.server.stop()

    def wait(self):
        trust_sleep(float(self.config["times"]))


def cloud_gui():
    import PySimpleGUI as sg
    config = load_config("cloud")
    users = ";".join(_[0] + ":" + _[1] for _ in config.get("users", []))
    proxy = ";".join(_[0] + ":" + str(_[1]) for _ in config.get("proxy", []))
    GUI_SETTING = dict(size=(11, 1), justification='right', text_color="black", background_color="white")
    layout = [[sg.Text("Users", **GUI_SETTING), sg.InputText(users, size=(33, 1))],
              [sg.Text("Server Port", **GUI_SETTING), sg.InputText(str(config.get("sport", "")), size=(33, 1))],
              [sg.Text("Forward Proxy", **GUI_SETTING), sg.InputText(proxy, size=(33, 1))],
              [sg.Text("Relay Port", **GUI_SETTING), sg.InputText(str(config.get("rport", "")), size=(33, 1))],
              [sg.Text("Cloud Name", **GUI_SETTING), sg.InputText(config.get("pname"), size=(33, 1))],
              [sg.Text("Root Path", **GUI_SETTING),
               sg.InputText(config.get("spath"), size=(26, 1), key="tgt"),
               sg.FolderBrowse("Fold", size=(4, 1), target="tgt", button_color="brown")],
              [sg.Text("Status", **GUI_SETTING),
               sg.Text("Stop", size=(14, 1), key="status", justification='left', text_color="black", background_color="white"),
               sg.Button("Start", button_color="brown", size=(5, 1)),
               sg.Button("Stop", button_color="brown", size=(5, 1))]]
    window = sg.Window('BeeDrive-Cloud', layout, auto_size_buttons=False,
                       background_color="white", icon=resource_path('source/icon.ico'))

    RUNNING = False
    while True:
        evt, rspn = window.read()
        if evt == 'Cancel' or evt is None:                       
            break

        if evt == "Start" and not RUNNING:
            servers = ConfigLauncher(save_config("cloud",
                                                users=parse_users(rspn[0]),
                                                sport=int(rspn[1]),
                                                spath=rspn["tgt"],
                                                times=3153600,
                                                sign=True,
                                                crypt=True,
                                                proxy=analysis_ip(rspn[2]),
                                                manager=max(cpu_count(), 1),
                                                worker=4,
                                                pname=rspn[4],
                                                rport=rspn[3]))
            window["status"].update("Running")
            servers.start()
            RUNNING = True
            
        elif evt == "Stop" and RUNNING:
            servers.stop()
            window["status"].update("Stop")
            RUNNING = False      
    window.close()


def cmd_get_config(choose):
    if isinstance(choose, dict):
        for key in ["users", "sport", "spath", "times", "sign",
                    "crypt", "proxy", "pname", "rport"]:
            if key not in choose:
                raise ValueError("Loaded custom configure doesn't support Cloud service.")
        return choose

    config = load_config("cloud")
    if choose == "check":
        print("Cloud default configures:")
        for name, key in [("Users Info:", "users"),
                          ("Server Port:", "sport"),
                          ("Server Path:", "spath"),
                          ("Durations:", "times"),
                          ("#Managers:", "manager"),
                          ("#Workers:", "worker"),
                          ("Proxy IP:", "proxy"),
                          ("Nickname:", "pname"),
                          ("Relay Port:", "rport")]:
            print(name, config.get(key, ""))
        sys.exit()

    if choose == "default" and len(config) > 0:
        return config

    print("\nSetting default config for Cloud Drive")
    print("\n[1] Drive Service")
    config["users"] = parse_users(input("1. Authorized users and passwords [user:passwd;user:passwd;...]:"))
    config["sport"] = int(input("2. One port to launch the Server [1-52560]:"))
    config["spath"] = input("3. A path to save file on your computer: ")
    config["times"] = float(input("4. How many minutes your want to keep the cloud alive? ")) * 60
    config["manager"] = max(int(input("5. How many CPUs the service can use at most? ")), 1)
    config["worker"] = max(int(input("6. How many tasks can each CPU accept at most? ")), 1)
    config["sign"] = True
    config["crypt"] = True
    
    if input("\n[2] Free NAT Service [y|n]: ").lower() == "y":
        config["proxy"] = input("7. Accessible Forwarding servers [ip:port;ip;port;...]: ")
        config["proxy"] = [(addr.split(":")[0], int(addr.split(":")[1])) for addr in config["proxy"].split(";")]
        config["pname"] = input("8. A nickname on the Forwarding server: ")
        config["rport"] = int(input("9. One port to launch the local Proxy server: "))
    else:
        config["proxy"] = config["pname"] = config["rport"] = ""
    return save_config("cloud", **config)


def cloud_cmd(temp_port, temp_time, config):
    config = cmd_get_config(config)
    if temp_port:
        config["sport"] = int(temp_port)
    if temp_time:
        config["times"] = int(temp_time) * 60
    servers = ConfigLauncher(config)
    servers.start()
    servers.wait()
    servers.stop()
    
