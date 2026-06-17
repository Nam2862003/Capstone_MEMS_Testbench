# Packaging The GUI

Use this on your development laptop to create a Windows app folder for another laptop.

## Build

From `Py_GUI`:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build_exe.ps1
```

The output is:

```text
dist\SPR25_MEMS_TESTBENCH\SPR25_MEMS_TESTBENCH.exe
```

Zip the whole `dist\SPR25_MEMS_TESTBENCH` folder and send that zip to your friend. Do not send only the `.exe`, because PyQt/scipy support files are stored beside it.

## Friend's Laptop

1. Unzip the folder somewhere writable, for example Desktop or Documents.
2. Plug in the Nucleo board and check the COM port in Windows Device Manager.
3. Run `SPR25_MEMS_TESTBENCH.exe`.
4. In the GUI, choose the right COM port for HS USB or the right IP settings for Ethernet.

CSV exports will be saved in a `data` folder beside the EXE.

## Optional Installer

To make it install like normal Windows apps and create a clean desktop shortcut named `SPR25 MEMS TESTBENCH`, install Inno Setup on your build laptop, then:

1. Run `.\build_exe.ps1`.
2. Run `.\build_installer.ps1`.

The installer output will be:

```text
installer_output\SPR25_MEMS_TESTBENCH_Setup.exe
```

Send that setup EXE to your friend. It installs the app and creates the desktop shortcut with the clean name.

## Notes

- Build the EXE on Windows for Windows.
- If Windows SmartScreen warns about an unknown app, choose More info then Run anyway.
- If the USB COM port does not appear, install the ST or Windows USB serial driver for the Nucleo board.
