
# BeeDrive

Open Source Privacy File Transfering System for Teams and Individual Developers.

## Features

- __Security__

  In contrast with protocols like HTTP and FTP, BeeDrive keeps your data safe during each time of data transfer. We sign data and encrypt them based on your own password.

- __Efficiency__

  We didn't sacrifice performance for safety. BeeDrive can transfer individual files at a rate of 50MB/s with encryption, while it can even reach over 100MB/s without encryption. This performance is sufficient for typical file transfer scenarios, such as file exchange within the same data center (w/o encryption) or unsafety World Wide Web transfers (w/ encryption).

- __Free Network Address Translation (NAT)__

  Most individual developers and startups need to access their personal computers via their laptops. Although LAN Port Forwarding is a common choice, users take risks to be attacked. BeeDrive provides several public forwarding proxies world wild to help you access your data far away from your home. Once you have your cloud service, you can even deploy your own NAT service!

- __User Friendly API Designs__

  We keep BeeDrive as simple as we can. Firstly, you can obtain BeeDrive in flexible ways, such as PyPi, Source Code, and Executable Files (.exe). More than that, we have automatic strategies to help you manage configurations. To help you follow task progresses, we have rich information on console, and a simplify GUI window! No matter you are an expert or a freshman, you can always find a way that suits your style.

## Installation

The easiest way to get BeeDrive is using PyPi! 

```bash
> pip install BeeDrive
```

You can launch BeeDrive in CMD with `BeeDrive` and a GUI interface with `BeeDrive-gui`.
```bash
> BeeDrive -h
BeeDrive Command Line Launcher!

positional arguments:
  {cloud,upload,download,proxy}
                        whice service you need?
  arg1                  the first additional argument (optional)
  arg2                  the second additional argument (optional)

optional arguments:
  -h, --help            show this help message and exit
  -mode {app,cmd}       work on Command Line or Window Application?
  -reset_config {y,n}   reset default configure file [y|n]
  -custom_config CUSTOM_CONFIG
                        launch service with your custom configure file
```
The GUI interface will show if you are on a Mac/Windows platform.
```bash
> BeeDrive-gui
```

If you can't run above codes, try the followings instead.
```bash
> python -m BeeDrive -h
> python -m BeeDrive-gui
```
BeeDrive relies on two optional dependencies. `PySimpleGUI` is used to support GUI interface. `pycryptodome` is used for encrypting. They are not necessary if you don't need on these two purposes.
## Examples
* Personal Drive Service
You ONLY need to setup at the first time running `BeeDrive cloud`, it will remember your setting in the future. 

In this case, we not only launch a local personal drive, but also regist it on our public forwarding servers. `34.94.43.17:8889` is running at US, while `8.130.53.35:8889` is working in China. After we have a name on proxies, our drive can be accessed with this nick name instead of IP address.
```bash
> BeeDrive cloud 
Setting configurations

[1] Default Cloud Service
1. Authorized users and passwords [user:passwd;user:passwd;...]:BeeDrive:1234;anonymous:0
2. One port to launch the Server [1-65555]:8888
3. A path to save file on your computer: c:\\
4. How many minutes your want to keep the cloud alive? [1-30000]: 30000
5. Sign your data during transfering (maybe slow down transfering)? [y|n] y
6. Encrypto your data during transfering (maybe slow down transfering)? [y|n] y
7. How many CPUs the service can use at most? 8
8. How many tasks can each CPU accept at most? 8

[2] Free NAT Service [y|n]: y
9. Accessible Forwarding servers [ip:port;ip;port;...]: 34.94.43.17:8889;8.130.53.35:8889
10. A public name on the Forwarding server [anything]: wxsPC
11. One port to launch the local Proxy server [1-65555]: 8890
[Sun Jan 23 05:26:25 2022] INFO: Update BeeDrive-cloud default config at c:\.ProgramData\BeeDrive\cloud.bee
[Sun Jan 23 05:26:25 2022] INFO: Server has been launched at ('0.0.0.0', 8888)
[Sun Jan 23 05:26:25 2022] INFO: Registed at Proxy 34.94.43.17:8889 with nickname wxsPC:8888
[Sun Jan 23 05:26:26 2022] INFO: Registed at Proxy 8.130.53.35:8889 with nickname wxsPC:8888
```
Maybe you are more interested in running with a Window. 
```bash
> BeeDrive cloud -mode app
```

[Cloud APP]()

* Upload File/Folder
  Here is the example to help you upload `myfile.txt` to the cloud drive we just setup. Again, you will have to fill out these settings at the first time ONLY.

```bash
> BeeDrive upload myfile.txt
Setup default config
1. Username to login the Cloud: BeeDrive
2. Password to login the Cloud:
3. Cloud service address [ip:port]: wxsPC:8888
4. Forwarding Proxy service addresses [ip:port;ip;port;...]: 34.94.43.17:8889
5. Maximum numer of concurrently transferring files: 4
6. Sign transfering data (may slow down speed) [y|n]:y
7. Encrypto transfering data (may slow down speed) [y|n]:y
[Sun Jan 23 05:36:08 2022] INFO: Update BeeDrive-upload default config at c:\.ProgramData\BeeDrive\upload.bee
[Sun Jan 23 05:36:11 2022] INFO: - using proxy 34.94.43.17:8889 to connect target wxsPC:8888
Upload:myfile.txt: ================================================== 100.0% | 0.00KB/s |  0
```
Of course, we have GUI for this service again.
```bash
> BeeDrive upload -mode app
```
* Download File
Downloading is similar to uploading. The only different is we need to assign an address to save file.
```bash
> mkdir temp_download 
> BeeDrive download myfile.txt temp_download
Setup default config
1. Username to login the Cloud: BeeDrive
2. Password to login the Cloud:
3. Cloud service address [ip:port]: wxsPC:8888
4. Forwarding Proxy service addresses [ip:port;ip;port;...]: 34.94.43.17:8889
5. Maximum numer of concurrently transferring files: 4
6. Sign transfering data (may slow down speed) [y|n]:y
7. Encrypto transfering data (may slow down speed) [y|n]:y
[Sun Jan 23 05:53:28 2022] INFO: Update BeeDrive-download default config at c:\.ProgramData\BeeDrive\download.bee
[Sun Jan 23 05:53:31 2022] INFO: - using proxy 34.94.43.17:8889 to connect target wxsPC:8888
Download:myfile.txt: ================================================== 100.0% | 0.06KB/s |  0
```
Here is the code to help you run this service with a GUI.
```bash
> BeeDrive download -mode app
```

* Forwarding Proxy (Free NAT)
Forwarding proxy doesn't support GUI because we think it should work on servers only. This service only relies on one single argument! That is the port you need.
```bash
> BeeDrive proxy 8889
[Sun Jan 23 03:49:58 2022] INFO: Public Host Proxy is launched at port 8889
[Sun Jan 23 03:50:03 2022] INFO: Registration 198.137.18.12:8888 with Nickname=BeeDrive
[Sun Jan 23 03:50:32 2022] INFO: Forwarding 198.137.18.12:1557 to BeeDrive:8888
[Sun Jan 23 03:53:01 2022] INFO: Forwarding 64.136.145.66:2961 to BeeDrive:8888
[Sun Jan 23 03:53:54 2022] INFO: Forwarding 198.137.18.12:45652 to BeeDrive:8888
```