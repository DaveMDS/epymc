The Emotion Media Center
========================

**EpyMC** is a Media Center application written in python that use the Enlightenemnt Foundation Library as the living base. The software is Open Source and multiplatform, it should work on every platform, as soon as you have installed the EFL and its python bindings. Thus at the moment the target platform is linux as all the delopment and testing is done on it.


## Features ##

- The core has a **modular structure**, every activity in the media center is a module that can be enabled/disable at runtime.
- An abstract **input event system** make the interface controllable by variuos input device, such as mouse, keybord, infrared remote controller and joystick. (more input device can be supported just writing a new module for it)
- All the application is written in the **python** language to speedup the development and to make the application REALLY **portable**, the same codebase should work (without recompile and friends) on every platform where the efl are supported.
- Thanks to the use of the EFL the application can run on different graphic backend, usually the super-fast software engine or the OpenGL/ES engine.
- The UI is **fully scalable** and the scale can be changed from the config section.

![01](/doc/ss/emc_01.png)
![02](/doc/ss/emc_02.png)
![03](/doc/ss/emc_03.png)
![04](/doc/ss/emc_04.png)


## Movie Module ##

The movie module let you browse (and play, of course) your film collection and thanks to the integration with themoviedb.org API is able to retrieve lots of information about you media, such as infos, posters, fanarts, cast and others...
- Ability to configure the source folders from the UI
- Retrive films info from themoviedb.org film database, with poster and fanart
- You can choose your preferred poster/fanart for a given film from all the image available on the online db.
- Movie info download can occur automatically on background or on-demand by the user.

![05](/doc/ss/emc_05.png)
![06](/doc/ss/emc_06.png)
![07](/doc/ss/emc_07.png)
![08](/doc/ss/emc_08.png)
![09](/doc/ss/emc_09.png)



## TvShow Module ##

The tvshows module is similar to the movie one but it retrieve your media information from thetvdb.com online database. It will fetch from the internet all the info about your series

- Ability to configure the source folders from the UI
- Retrive films info from thetvdb.com database, with posters, banners and fanarts.
- You can choose your preferred poster/fanart for a given serie/season from all the image available on the online db.
- Info download can occur automatically on background or on-demand by the user.


## M.A.M.E Module ##

- Make the list of available games (rom you own) or a list of all the supported games, more than 8000 !! with the ability to download the rom(if available) on the net.
- Transparent screenshots download for all the games hosted on progettoemma.net
- Parse of history.dat files to show super accurate game informations
- It's the fastest M.A.M.E. frontend I know about :)

![20](/doc/ss/emc_20.png)
![21](/doc/ss/emc_21.png)
![22](/doc/ss/emc_22.png)
![23](/doc/ss/emc_23.png)


## Online Channels Module ##

This module is able to "scrape" informations and videos from various video site aound the net. The functional model is quite the same as the one used in XBMC: every channel is a python script that get fired (in a separate thread) every time you request a new page. This way the application never hangs for network problems and porting channels from the XBMC scripts is really easy.

Available channels:
- You Tube
- Trailer Addict
- Zapiks Extreme Videos
- ...plus a secret one

![30](/doc/ss/emc_30.png)
![31](/doc/ss/emc_31.png)
![32](/doc/ss/emc_32.png)
![33](/doc/ss/emc_33.png)


## Music Module ##

The music module is still in a development stage, it use the mutagen library that is only available for python2, thus if you are using pyton3 this module will not work.


## Install ##

Requirements:
- A recent version of EFL 1.8 plus elementary
- The python bindings for EFL 1.8
- The Emotion preferred engine atm is gstreamer1 or generic/vlc
- python-mutagen, only available in py2 (for mp3 metadata extraction)

To install epymc on your system just run (as root):
```
python setup.py install
```

this will install in the default python directory for your distribution, you can change that by providing '--prefix=' param to the install command. 

To uninstall you can try (as root):
```
python setup.py uninstall
```

You can also run the media center directly from the sources folder, without installing anything:
```
./bin/epymc
```
but note that if you have a copy installed somewhere this command will use the installed one instead.


## Usage ##

To run the media center simply run the `epymc` command from the console, or just use your applications menu, you should find 'Emotion Media Center' under the 'AudioVideo' category.

The edje theme comes precompilated from svn, if you need to build it again just use the **build_themes** command of setup.py

More of the application options can be changed directly from the user interface.
All that options, and more, are stored in simple text file located at `<home>/.config/epymc/epymc.conf`, that you can easy edit with a text editor. A default file is created on startup.

Other info can be found in the [README](https://github.com/DaveMDS/epymc/blob/master/README) file and the default keyboard bindings are [keys.txt](https://github.com/DaveMDS/epymc/blob/master/doc/keys.txt).

## Todo ##

- GRAPHICS !!!
- I18N
- Finish the Music module
- Finish the Youtube module
- Handle remote url (like smb:// and so on)... just by mounting remote stuff?
- Photo Module (low-priority)

