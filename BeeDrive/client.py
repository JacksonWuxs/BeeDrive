import time
import getpass
import os
import sys

from .core.Client import ClientManager
from .core.constant import NewTask, Stop, Done
from .core.utils import analysis_ip, resource_path
from .configures import save_config, load_config


GUI_CONFIG = dict(size=(7, 1), justification='right', text_color="black", background_color="white")


def cmd_check_config():
    config = load_config("client")
    print("Client Default Configures:")
    for name, key in [("UserName:", "user"),
                      ("Password:", "passwd"),
                      ("Cloud IP:", "cloud"),
                      ("Proxy IP:", "proxy"),
                      ("Encrypt:", "encrypt"),
                      ("Save Path:", "root")]:
        print(name, config.get(key, ""))
    sys.exit()


def cmd_get_config(choose):
    if isinstance(choose, dict) > 0:
        for key in ["user", "pwd", "cloud", "proxy", "encrypt"]:
            if key not in choose:
                raise ValueError("Custom config file isn't valid for client service.")
        return config

    config = load_config("client")
    if choose == "default" and len(config) > 0:
        return config
    fast_setup = input("Do you need a fast setup? [y|n]:").lower() == "y"
    print("\nBeeDrive Client Setup")
    config["user"] = input("1. Username to login the Cloud: ")
    config["passwd"] = getpass.getpass("2. Password to login the Cloud: ")
    config["cloud"] = analysis_ip(input("3. Cloud service address [ip:port]: "))[0]
    if fast_setup:
        config["proxy"] = [("127.0.0.1", 8888), ("beedrive.kitgram.cn", 8888)]
        config["root"] = config.get("root", "./")
        config["encrypt"], config["pool"], config["retry"] = True, 2, 3
    else:
        config["root"] = input("4. Path to store files: ")
        config["proxy"] = analysis_ip(input("5. NAT service(s) addresses [ip:port;ip;port;...]: "))
        config["encrypt"] = input("6. Encrypto your data [y|n]:").lower() == "y"
        config['pool'] = max(int(input("7. Maximum number of parallel transferring files:")), 1)
        config["retry"] = max(int(input("8. Maximum number of failed retry:")), 1)
    return save_config("client", **config)


def gui_run(config, window, service):
    manager = ClientManager.get_controller(name=config["user"], pool_size=config["pool"])
    manager.relay_do(NewTask, task=service, **config)
    service = service.capitalize()
    while True:
        msg = manager.read()
        if msg == Done:
            break
        if not isinstance(msg, (str, bytes)):
            continue

        msg = msg.strip()
        if msg.startswith(service):
            l, m, r = msg.split(" | ")[-3:]
            msg = " | ".join([l.split(" ")[-1], m, r])
        window["status"].update(msg)
        if window.read(timeout=0.0001) in ("Cancel", None) or \
           msg.startswith("Error:"):
            break
    manager.join_do(Stop)
    return msg


def upload_gui():
    import PySimpleGUI as sg
    config = load_config("client")
    proxy = ";".join(_[0] + ":" + str(_[1]) for _ in config.get("proxy", []))
    cloud = "%s:%d" % config["cloud"] if "cloud" in config else ""
    layout = [[sg.Text("Name:", **GUI_CONFIG), sg.InputText(config.get("user", ""), size=(40, 1))],
              [sg.Text("Passwd:", **GUI_CONFIG), sg.InputText(config.get("passwd", ""), password_char="*", size=(40, 1))],
              [sg.Text("Cloud:", **GUI_CONFIG), sg.InputText(cloud, size=(40, 1))],
              [sg.Text("Proxy:", **GUI_CONFIG), sg.InputText(proxy, size=(40, 1))],
              [sg.Text("Source:", **GUI_CONFIG),
               sg.InputText("", key="tgt", size=(28, 1)), sg.FileBrowse("File", size=(3, 1), target="tgt", button_color="brown"),
                sg.FolderBrowse("Fold", size=(3, 1), target="tgt", button_color="brown")],
              [sg.Text("Progress:", **GUI_CONFIG),
               sg.Text("", size=(24, 1), key="status", justification='left', text_color="black", background_color="white"), sg.Submit(button_color="brown", size=(9, 1))]]
    window = sg.Window('BeeDrive-Upload', layout, auto_size_buttons=False, background_color="white", icon=resource_path('source/icon.ico'))

    while True:
        evt, rspn = window.read()
        if evt == 'Cancel' or evt is None:
            break
        if evt != "Submit":
            continue

        config = save_config("client",
                             user=rspn[0],
                             passwd=rspn[1],
                             cloud=analysis_ip(rspn[2])[0],
                             proxy=analysis_ip(rspn[3]),
                             pool=2,
                             retry=3,
                             root=config.get("root", "./"),
                             encrypt=True)
        config["source"] = rspn["tgt"]
        if gui_run(config, window, "upload") in ("Cancel", None):
            break
    window.close()


def download_gui():
    import PySimpleGUI as sg
    config = load_config("client")
    proxy = ";".join(_[0] + ":" + str(_[1]) for _ in config.get("proxy", []))
    cloud = "%s:%d" % config["cloud"] if "cloud" in config else ""
    layout = [[sg.Text("Name:", **GUI_CONFIG), sg.InputText(config.get("user", ""), size=(40, 1))],
              [sg.Text("Passwd:", **GUI_CONFIG), sg.InputText(config.get("passwd", ""), password_char="*", size=(40, 1))],
              [sg.Text("Cloud:", **GUI_CONFIG), sg.InputText(cloud, size=(40, 1))],
              [sg.Text("Proxy:", **GUI_CONFIG), sg.InputText(proxy, size=(40, 1))],
              [sg.Text("Target:", **GUI_CONFIG), sg.InputText("", size=(40, 1))],
              [sg.Text("Save:", **GUI_CONFIG), sg.InputText(config.get("root", ""), size=(33, 1), key="path"),
               sg.FolderBrowse("Fold", size=(4, 1), target="path", button_color="brown")],
              [sg.Text("Progress:", **GUI_CONFIG),
               sg.Text("", size=(24, 1), key="status", justification='left', text_color="black", background_color="white"),
               sg.Submit(button_color="brown", size=(9, 1))]]
    window = sg.Window('BeeDrive-Download', layout, auto_size_buttons=False, background_color="white", icon=resource_path('source/icon.ico'))

    while True:
        evt, rspn = window.read()
        if evt == 'Cancel' or evt is None:
            break
        if evt != "Submit":
            continue
        config = save_config("client",
                             user=rspn[0],
                             passwd=rspn[1],
                             cloud=analysis_ip(rspn[2])[0],
                             proxy=analysis_ip(rspn[3]),
                             root=rspn["path"],
                             pool=2,
                             retry=3,
                             encrypt=True)
        config["source"] = rspn[4]
        if gui_run(config, window, "download") in ("Cancel", None):
            break
    window.close()


def upload_cmd(source, config):
    config = cmd_get_config(config)
    config["source"] = source
    manager = ClientManager.get_controller(name=config["user"], pool_size=config["pool"])
    manager.join_do(NewTask, task="upload", **config)
    manager.join_do(Stop)


def download_cmd(source, root, config):
    config = cmd_get_config(config)
    config["source"] = source
    if root:
        config["root"] = root
    manager = ClientManager.get_controller(name=config["user"], pool_size=config["pool"])
    manager.join_do(NewTask, task="download", **config)
    manager.join_do(Stop)
    
