import os
import sys
import pickle
import time
import socket

from multiprocessing import cpu_count

from .lib.Server import LocalServer
from .lib.Proxy import LocalRelay
from .lib.utils import analysis_ip, resource_path, trust_sleep, get_uuid, clean_path
from .lib.core.database import UserDatabase
from .configures import save_config, load_config


CLOUD_CONFIGS = {"Database:": "database",
                 "Server Port:": "sport",
                 "Server Path:": "spath",
                 "Durations:": "times",
                 "#Managers:": "manager",
                 "#Workers:": "worker",
                 "Proxy IP:": "proxy",
                 "Nickname:": "pname",
                 "Relay Port:": "rport"}

def parse_users(string):
    if len(string) == 0:
        return []
    return [_.split(":", 1) for _ in string.split(";") if len(_) > 0]


class ConfigLauncher:
    def __init__(self, config, database):
        self.config = config
        self.hosts = [LocalRelay(proxy, config["rport"], config["sport"], config["pname"], config["manager"] * config["worker"]) \
                           for proxy in config["proxy"]]
        self.server = LocalServer(database=database, port=config["sport"],
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
    database = UserDatabase(config["database"])
    users = ";".join(database.list_users())
    proxy = ";".join(_[0] + ":" + str(_[1]) for _ in config.get("proxy", [("beedrive.kitgram.cn", 80)]))
    GUI_SETTING = dict(size=(11, 1), justification='right', text_color="black", background_color="white")
    layout = [[sg.Text("Users", **GUI_SETTING), sg.InputText(users, size=(33, 1))],
              [sg.Text("Server Port", **GUI_SETTING), sg.InputText(str(config.get("sport", "")), size=(33, 1))],
              [sg.Text("Forward Proxy", **GUI_SETTING), sg.InputText(proxy, size=(33, 1))],
              [sg.Text("Relay Port", **GUI_SETTING), sg.InputText(str(config.get("rport", "")), size=(33, 1))],
              [sg.Text("Cloud Name", **GUI_SETTING), sg.InputText(config.get("pname"), size=(33, 1))],
              [sg.Text("Root Path", **GUI_SETTING),
               sg.InputText(config.get("spath")[0], size=(26, 1), key="tgt"),
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
                                                sport=int(rspn[1]),
                                                spath=rspn["tgt"],
                                                times=3153600,
                                                proxy=analysis_ip(rspn[2]),
                                                manager=max(cpu_count(), 1),
                                                worker=4,
                                                pname=rspn[4],
                                                rport=[rspn[3]]))
            window["status"].update("Running")
            servers.start()
            RUNNING = True
            
        elif evt == "Stop" and RUNNING:
            servers.stop()
            window["status"].update("Stop")
            RUNNING = False      
    window.close()


def cmd_manage_config(choose):
    config = load_config("cloud")
    database = UserDatabase(config["database"])
    if not choose and len(config) > 0:
        return config, database

    if len(config) > 0:
        print("BeeDrive Cloud Configure")
        print('-' * 20)
        print("Users:", database.list_users())
        for name, key in CLOUD_CONFIGS.items():
            print(name, config.get(key, ""))
        print('-' * 20)
        if choose == "check":
            sys.exit()
    
    fast_setup = input("Do you need a fast setup? [y|n]:").lower() == "y"
    print("\nBeeDrive Cloud Setup")
    database.clear()
    username = input("1. Setup admin username:")
    password = input("2. Setup admin password:")
    echo = database.create_user(username, password, 1)
    assert echo == "Success", echo
    while input("Do you want to add more users? [Y|N]").upper() == "Y":
        name = input("New username:")
        pswd = input("New password:")
        print(database.create_user(username, password, 1))
    config["sport"] = int(input("3. Port for cloud service [1024-65535]:"))
    config["spath"] = [clean_path(_) for _ in input("4. Path(s) to store files: ").split(";")]
    if fast_setup:
        config["times"], config["manager"], config["worker"] = 2 ** 29, cpu_count(), 8
        config["proxy"] = [("beedrive-cn.kitgram.cn", 80), ("beedrive-us.kitgram.cn", 80)]
        config["pname"] = os.environ.get("USERNAME", os.environ.get("LOGNAME", get_uuid()))
        for port in range(int(config["sport"]) + 1, 65535):
            try:
                s = socket.socket()
                s.bind(("0.0.0.0", port))
                config["rport"] = port
                s.close()
                break
            except OSError:
                pass
        else:
            raise ValueError("Autosetup port for NAT service is failed")
                
    else:
        config["times"] = float(input("5. Cloud serving duration [hours]:")) * 3600
        config["manager"] = max(int(input("6. Maximum number of available CPU [1-%d]:" % cpu_count())), 1)
        config["worker"] = max(int(input("7. How many tasks can each CPU accept at most? ")), 1)
        if input("\nDo you need a Free NAT Service? [y|n]: ").lower() == "y":
            print("BeeDrive Official Free NAT at beedrive-cn.kitgram.cn:80 and beedrive-us.kitgram.cn:80.")
            config["proxy"] = input("8. NAT service(s) address [ip:port;ip;port;...]: ")
            config["proxy"] = [(addr.split(":")[0], int(addr.split(":")[1])) for addr in config["proxy"].split(";")]
            config["pname"] = input("9. Nickname on NAT servers: ")
            config["rport"] = int(input("10. Port for NAT service [1024-65535]: "))
        else:
            config["proxy"] = config["pname"] = config["rport"] = ""
    return save_config("cloud", **config), database


def cloud_cmd(temp_port, temp_time, config, database):
    if temp_port:
        config["sport"] = int(temp_port)
    if temp_time:
        config["times"] = int(temp_time)
    servers = ConfigLauncher(config)
    servers.start()
    servers.wait()
    servers.stop()
    
