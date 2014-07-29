The Emotion Media Center
========================

**EpyMC** is a Media Center application written in python that use the Enlightenemnt Foundation Library as the living base. The software is Open Source and multiplatform, it should work on every platform, as soon as you have installed the EFL and its python bindings. Thus at the moment the target platform is linux as all the delopment and testing is done on it.

![01](/doc/ss/emc_01.jpg)

## Features ##

- The core has a **modular structure**, every activity in the media center is a module that can be enabled/disable at runtime.
- An abstract **input event system** make the interface controllable by variuos input device, such as mouse, keybord, infrared remote controller and joystick. (more input device can be supported just writing a new module for it)
- All the application is written in the **python** language to speedup the development and to make the application REALLY **portable**, the same codebase should work (without recompile and friends) on every platform where the efl are supported.
- Thanks to the use of the EFL the application can run on different graphic backend, usually the super-fast software engine or the OpenGL/ES engine.
- The UI is **fully scalable** and the scale can be changed from the config section.





## Todo ##

- Handle remote url (like smb:// and so on)... just by mounting remote stuff?
- Photo Module (low-priority)



