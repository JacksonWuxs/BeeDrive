import time
import getpass
import os

from .core.Client import ClientManager
from .core.constant import NewTask, Stop, Done, STAGE_FAIL, STAGE_DONE
from .core.utils import analysis_ip, resource_path
from .configures import save_config, load_config


GUI_CONFIG = dict(size=(7, 1), justification='right', text_color="black", background_color="white")


def cmd_get_config(service, reset_config, custom_config):
    if len(custom_config) > 0:
        for key in ["user", "pwd", "cloud", "proxy", "crypto", "sign"]:
            if key not in custom_config:
                raise ValueError("Custom config file isn't valid for %s service." % service)
        return custom_config

    config = load_config(service)
    if not reset_config and len(config) > 0:
        return config

    print("\nSetup default config")
    config["user"] = input("1. Username to login the Cloud: ")
    config["passwd"] = getpass.getpass("2. Password to login the Cloud: ")
    config["cloud"] = analysis_ip(input("3. Cloud service address [ip:port]: "))[0]
    config["proxy"] = analysis_ip(input("4. Forwarding Proxy service addresses [ip:port;ip;port;...]: "))
    config['pool'] = int(input("5. Maximum numer of concurrently transferring files: "))
    config["sign"] = input("6. Sign transfering data (may slow down speed) [y|n]:").lower() == "y"
    config["crypto"] = input("7. Encrypto transfering data (may slow down speed) [y|n]:").lower() == "y"
    config["root"] = os.curdir
    config["task"] = service
    return save_config(service, **config)


def upload_gui():
    import PySimpleGUI as sg
    config = load_config("upload")
    proxy = ";".join(_[0] + ":" + str(_[1]) for _ in config.get("proxy", []))
    cloud = "%s:%d" % config["cloud"]
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

        config = save_config("upload",
                             user=rspn[0],
                             passwd=rspn[1],
                             cloud=analysis_ip(rspn[2])[0],
                             proxy=analysis_ip(rspn[3]),
                             pool=4,
                             sign=True,
                             crypto=True,
                             task="upload")
        config["source"] = rspn["tgt"]
        manager = ClientManager.get_controller(name=config["user"], pool_size=config["pool"])
        manager.relay_do(NewTask, **config) 
        while True:
            time.sleep(0.2)
            msg = manager.read()
            if not isinstance(msg, (str, bytes)):
                continue
            if msg.startswith("Upload:"):
                l, m, r = msg.split(" | ")[-3:]
                msg = " | ".join([l.split(" ")[-1], m, r])
            window["status"].update(msg + " " * (80 - len(msg)))
            if msg in (STAGE_FAIL, STAGE_DONE):
                break
            evt, _ = window.read(timeout=0.0001)
            if evt == 'Cancel' or evt is None:
                break
        manager.join_do(Stop)
    window.close()


def download_gui():
    import PySimpleGUI as sg
    config = load_config("download")
    proxy = ";".join(_[0] + ":" + str(_[1]) for _ in config.get("proxy", []))
    cloud = "%s:%d" % config["cloud"]
    layout = [[sg.Text("Name:", **GUI_CONFIG), sg.InputText(config.get("user", ""), size=(40, 1))],
              [sg.Text("Passwd:", **GUI_CONFIG), sg.InputText(config.get("passwd", ""), password_char="*", size=(40, 1))],
              [sg.Text("Cloud:", **GUI_CONFIG), sg.InputText(cloud, size=(40, 1))],
              [sg.Text("Proxy:", **GUI_CONFIG), sg.InputText(proxy, size=(40, 1))],
              [sg.Text("Target:", **GUI_CONFIG), sg.InputText("", size=(40, 1))],
              [sg.Text("Save To:", **GUI_CONFIG), sg.InputText(rspn.get("root", ""), size=(33, 1), key="path"),
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

        config = save_config("download",
                             user=rspn[0],
                             pwd=rspn[1],
                             cloud=analysis_ip(rspn[2])[0],
                             proxy=analysis_ip(rspn[3]),
                             root=rspn[5],
                             pool=4,
                             sign=True,
                             crypt=True,
                             task="download")
        config["source"] = rspn[4]
        manager = ClientManager.get_controller(name=config["user"], pool_size=config["pool"])
        manager.relay_do(NewTask, **config) 
        while True:
            time.sleep(0.2)
            msg = manager.read()
            if not isinstance(msg, (str, bytes)):
                continue
            if msg.startswith("Download:"):
                l, m, r = msg.split(" | ")[-3:]
                msg = " | ".join([l.split(" ")[-1], m, r])
            window["status"].update(msg + " " * (80 - len(msg)))
            if msg in (STAGE_FAIL, STAGE_DONE):
                break
            evt, _ = window.read(timeout=0.0001)
            if evt == 'Cancel' or evt is None:
                break
        manager.join_do(Stop)
    window.close()


def upload_cmd(source, reset_config, custom_config):
    config = cmd_get_config("upload", reset_config, custom_config)
    config["source"] = source
    manager = ClientManager.get_controller(name=config["user"], pool_size=config["pool"])
    manager.join_do(NewTask, **config)
    manager.join_do(Stop)


def download_cmd(source, root, reset_config, custom_config):
    config = cmd_get_config("download", reset_config, custom_config)
    config["source"] = source
    config["root"] = root if root else "./"
    manager = ClientManager.get_controller(name=config["user"], pool_size=config["pool"])
    manager.join_do(NewTask, **config)
    manager.join_do(Stop)
    
