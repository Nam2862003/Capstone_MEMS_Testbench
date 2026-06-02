# Capstone MEMS Testbench Setup

This document lists the tools needed to build, regenerate, flash, and run the Capstone MEMS Testbench firmware and Python GUI.

All paths and commands below are written from the main repository folder:

```text
C:\STM32\Capstone_MEMS_Testbench
```

## Project Folders

- `Nucleo_H723ZG/` - STM32H723ZG firmware project.
- `NUCLEO_H7S3L8_CDC/` - STM32H7S3L8 firmware project with USB CDC support.
- `Py_GUI/` - Python GUI used to communicate with the firmware over USB serial and/or UDP.

## Firmware Dependencies

Install these tools on the development PC.

### Required

- Git
- Visual Studio Code
- CMake 3.22 or newer
- Ninja
  - The `ninja.exe` file can be stored anywhere, but its folder must be on the Windows `PATH`.
  - On this PC, Windows currently finds Ninja at `C:\ninjia\ninja.exe`.
- Arm GNU Toolchain / GCC Arm Embedded
  - Required executables include `arm-none-eabi-gcc`, `arm-none-eabi-g++`, `arm-none-eabi-objcopy`, and `arm-none-eabi-size`.
- STM32CubeProgrammer
  - Used to flash firmware and recover/debug boards.
- ST-LINK USB driver
  - Needed on Windows so the boards are detected correctly.

### Recommended STM32 Tools

- STM32CubeIDE
  - Useful for debugging, flashing, and checking generated STM32 projects.
- STM32CubeMX
  - Used to open and regenerate `.ioc` configuration files.
- STM32 VS Code Extension
  - Useful when working with STM32 projects directly inside VS Code.
- VS Code CMake Tools extension
- VS Code clangd extension or Microsoft C/C++ extension

## Firmware Environment Checks

After installing the firmware tools, open a new terminal and check:

```powershell
git --version
cmake --version
ninja --version
arm-none-eabi-gcc --version
STM32_Programmer_CLI --version
```

If any command is not found, add the tool installation folder to the Windows `PATH`, then restart the terminal.

Common Windows paths to check:

```text
C:\Program Files\CMake\bin
C:\Program Files\Ninja
C:\ninjia
C:\Program Files (x86)\Arm GNU Toolchain arm-none-eabi\bin
C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin
```

The exact Ninja and Arm toolchain folder names may vary depending on where they were installed.

## Build the H723ZG Firmware

From the repository root:

```powershell
cd Nucleo_H723ZG
cmake --preset Debug
cmake --build --preset Debug
```

For a release build:

```powershell
cmake --preset Release
cmake --build --preset Release
```

This project uses:

- `CMakePresets.json`
- Ninja generator
- `cmake/gcc-arm-none-eabi.cmake`
- Target/project name: `Capstone_MEMS_Testbench`

## Build the H7S3L8 Firmware

From the repository root:

```powershell
cd NUCLEO_H7S3L8_CDC
cmake --preset Debug
cmake --build --preset Debug
```

For a release build:

```powershell
cmake --preset Release
cmake --build --preset Release
```

This project uses:

- `CMakePresets.json`
- Ninja generator
- `gcc-arm-none-eabi.cmake`
- Target/project name: `NUCLEO_H7S3L8_CDC`

## Regenerate Firmware with STM32CubeMX

Use STM32CubeMX when pin configuration, clocks, peripherals, middleware, USB, or Ethernet settings need to change.

Open the matching `.ioc` file:

- H723ZG: `Nucleo_H723ZG/Capstone_MEMS_Testbench.ioc`
- H7S3L8: `NUCLEO_H7S3L8_CDC/NUCLEO_H7S3L8_CDC.ioc`

After regeneration:

1. Rebuild with CMake.
2. Check that user code sections were preserved.
3. Confirm the generated files still match the expected board and MCU.

## Flash Firmware

The easiest option is STM32CubeProgrammer or STM32CubeIDE.

Typical STM32CubeProgrammer CLI flow:

```powershell
STM32_Programmer_CLI --connect port=SWD
STM32_Programmer_CLI --connect port=SWD --download path\to\firmware.elf --verify --reset
```

Replace `path\to\firmware.elf` with the `.elf` produced in the matching `build/` folder.

## GUI Dependencies

The GUI is a Python application in `Py_GUI/`.

### Required

- Python 3.10 or newer
- pip
- Python packages:
  - `PyQt6`
  - `pyqtgraph`
  - `numpy`
  - `scipy`
  - `pyserial`

### Optional

- A virtual environment, recommended so the GUI dependencies do not interfere with other Python projects.

## Set Up the GUI

From the repository root:

```powershell
cd Py_GUI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install PyQt6 pyqtgraph numpy scipy pyserial
```

Run the GUI:

```powershell
python main.py
```

## GUI Communication Notes

The GUI code uses:

- USB serial via `pyserial`
- UDP sockets via Python's standard `socket` module
- NumPy/SciPy signal processing
- PyQt6 and pyqtgraph for the user interface and plots

For USB serial:

1. Flash firmware with USB CDC support.
2. Connect the board by USB.
3. Check Windows Device Manager for the COM port.
4. Make sure no other program is using the same COM port.

For UDP:

1. Confirm the board and PC are on the same network or directly connected as expected.
2. Check IP address and port settings in the GUI/firmware.
3. Allow the Python app through Windows Firewall if prompted.

## Generated Files to Avoid Committing

These are build/runtime outputs and normally should not be committed:

```text
Nucleo_H723ZG/build/
NUCLEO_H7S3L8_CDC/build/
NUCLEO_H7S3L8_CDC/.codex-build-check/
Py_GUI/.venv/
Py_GUI/__pycache__/
Py_GUI/pages/__pycache__/
__pycache__/
*.pyc
```

## Quick Setup Checklist

Firmware:

- Install CMake, Ninja, Arm GNU Toolchain, STM32CubeProgrammer, STM32CubeMX, and STM32CubeIDE.
- Confirm all command-line tools work from PowerShell.
- Build each firmware project with `cmake --preset Debug` and `cmake --build --preset Debug`.
- Flash the correct `.elf` to the matching board.

GUI:

- Install Python.
- Create and activate a virtual environment in `Py_GUI/`.
- Install `PyQt6 pyqtgraph numpy scipy pyserial`.
- Run `python main.py`.

