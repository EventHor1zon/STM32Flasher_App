# STM32Flasher_App

TUI/CLI Application utilising my STM32 Bootloader tool

## TODO

Refactor:
- Menu dictionaries are a bit messy
- Display objects are also messy
- key handling works nicely, clean it up
- New worker class in textual 2.2 could replace long_running_task
- rely more on the state-machine approach
- Consider keeping user-supplied details in a global dictionary


### Application

The application is built with Textual. Pretty fun to use and looks really nice.

![image](./screenshots/stmapp_disconnected.svg) 
![image](./screenshots/stmapp_connected.svg)


