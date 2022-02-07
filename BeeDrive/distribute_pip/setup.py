import sys
import os

import setuptools

sys.path.append("../../")
import BeeDrive


setuptools.setup(
    name=BeeDrive.__name__,
    version=BeeDrive.__version__,
    description="BeeDrive: Open Source Privacy File Transfering System for Teams and Individual Developers",
    long_description=open("../../README.md", encoding="utf8").read(),
    long_description_content_type='text/markdown',
    url="https://github.com/JacksonWuxs/BeeDrive",
    author="Xuansheng Wu",
    maintainer="Xuansheng Wu",
    platforms=["all"],
    python_requires='>=3',
    install_requires=['pycryptodome', 'PySimpleGUI'],
    package_dir={"": os.path.abspath("../../")},
    packages=setuptools.find_packages(where=os.path.abspath("../../"),
                                      exclude=("../distribute_exe",
                                               "../distribute_pip",)),
    package_data={"BeeDrive.source": ["*.*"]},
    license="GPL v3",
    classifiers=[
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        "Programming Language :: Python :: 3",
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        ],
    entry_points={"console_scripts": ["BeeDrive=BeeDrive.__main__:main"],
                  "gui_scripts": ["BeeDrive-gui=BeeDrive.app:main"]}
    )
    
        

