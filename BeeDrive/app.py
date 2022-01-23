# -*- coding: utf-8 -*-
import multiprocessing
import sys
sys.path.append("..")

import PySimpleGUI as sg

from BeeDrive import client,cloud
from BeeDrive.core.utils import resource_path

    
def welcome_page():
    layout = [[sg.Text("Welcome to BeeDrive!", text_color="black", background_color="white")],
              [sg.Button("Cloud", button_color="brown", size=(8, 1)),
               sg.Button("Upload", button_color="brown", size=(8, 1)),
               sg.Button("Download", button_color="brown", size=(8, 1))]]
    window = sg.Window('BeeDrive', layout,
                       auto_size_buttons=True, background_color="white",
                       icon=resource_path('source/icon.ico'))
    choice = window.read()[0]
    window.close()
    return choice


def main():
    multiprocessing.freeze_support()
    while True:
        choice = welcome_page()
        if  choice == "Upload":
            client.upload_gui()
            
        elif choice == "Download":
            client.download_gui()
            
        elif choice == "Cloud":
            cloud.cloud_gui()

        else:
            break


if __name__ == "__main__":
    main()
