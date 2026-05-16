# MEMS Cantilever Testbench Firmware System Architecture

## 1. System Purpose

The firmware controls a MEMS cantilever testbench using an STM32 Nucleo board. It generates or selects an excitation signal, captures two analog channels from the analog front-end, streams acquired samples to a PC GUI, and receives GUI commands for acquisition and test configuration.

Current firmware target:

- Board: Nucleo-H723ZG
- PC link: Ethernet using LwIP UDP
- Excitation generator: AD9833 DDS controlled by SPI1
- Acquisition: dual ADC simultaneous sampling using ADC1 and ADC2

Optional future target:

- Board: Nucleo-H7S3L8
- PC link: high-speed USB CDC instead of Ethernet UDP

## 2. Top-Level Architecture

```mermaid
flowchart LR
    GUI[PC GUI\nControl, plotting, logging]

    subgraph STM32[STM32 Firmware]
        APP[Application Layer\nCommand parser and test state]
        COMMS[Communication Layer\nEthernet UDP or HS USB CDC]
        ACQ[Acquisition Layer\nTIM6 + Dual ADC + DMA]
        DDS[DDS Control Layer\nSPI1 to AD9833]
        IO[Board Control GPIO\nPE/PR select, actuator select, PE gain]
        BUF[Sample Buffer\nD1 RAM circular DMA buffer]
    end

    DDSIC[AD9833 DDS\nSine excitation]
    AFE[Analog Front-End\nAmplifier / Wheatstone bridge]
    MEMS[MEMS Cantilever]

    GUI -->|Commands| COMMS
    COMMS --> APP
    APP --> ACQ
    APP --> DDS
    APP --> IO

    ACQ --> BUF
    BUF -->|Sample chunks| COMMS
    COMMS -->|ADC data/status| GUI

    DDS -->|SPI config| DDSIC
    DDSIC -->|Excitation sine| AFE
    IO -->|Analog switch/control lines| AFE
    MEMS -->|Sensor signal| AFE
    AFE -->|MEMS channel| ACQ
    AFE -->|Reference channel| ACQ
```

## 3. Firmware Layers

### Application Layer

Implemented mainly in `Core/Src/main.c`.

Responsibilities:

- Initialize clocks, MPU, cache, GPIO, DMA, ADC, TIM6, LwIP, UART, and SPI.
- Maintain runtime state:
  - ADC running/stopped
  - active ADC buffer size
  - DDS running/stopped
  - DDS frequency
  - PE/PR board mode
  - actuator source
  - PE gain index
- Parse GUI commands received over the communication interface.
- Apply configuration changes to acquisition, DDS, and GPIO-controlled analog routing.

Main command handlers:

- `BOARD?`
- `BUF,<samples>`
- `ADC SAMP,<Hz>`
- `ADC RES,<bits>`
- `START`
- `STOP`
- `DAC START`
- `DAC STOP`
- `DAC FREQ,<Hz>`
- `MODE,PE`
- `MODE,PR`
- `ACTUATOR,DDS`
- `ACTUATOR,FG`
- `ACTUATOR,STM32`
- `PE GAIN,<0..3>`

### Communication Layer

Current Nucleo-H723ZG implementation:

- Ethernet MAC + LAN8742 PHY
- LwIP without RTOS
- Static IP: `192.168.0.123`
- PC GUI destination IP: `192.168.0.100`
- ADC/status transmit port: UDP `5005`
- command receive port: UDP `5006`

The main loop calls `MX_LWIP_Process()` to poll Ethernet packets, process UDP commands, and handle LwIP timeouts.

Future Nucleo-H7S3L8 option:

- Replace Ethernet/LwIP UDP transport with USB HS CDC.
- Keep the same application command strings.
- Encapsulate ADC sample chunks in CDC bulk transfers.
- Preserve the same GUI control model, changing only the physical transport and packet framing.

### Acquisition Layer

Acquisition is timer-triggered and DMA-driven.

- Timer: TIM6
- TIM6 trigger output: update event / TRGO
- ADC mode: dual regular simultaneous mode
- ADC master: ADC1
- ADC slave: ADC2
- ADC1 channel: ADC channel 15
- ADC2 channel: ADC channel 5
- Default resolution: 16-bit
- DMA: DMA1 Stream0, circular mode, peripheral-to-memory
- Buffer: `adc_buffer[]` in `.RAM_D1`, 32-byte aligned
- Maximum buffer size: 4096 `uint32_t` words
- Each `uint32_t` word carries packed dual-ADC sample data from the ADC multimode data register.

Data movement:

1. TIM6 emits a trigger at the configured sampling rate.
2. ADC1 and ADC2 sample simultaneously.
3. ADC multimode hardware packs both conversion results.
4. DMA transfers packed samples into `adc_buffer`.
5. Half-complete and complete DMA callbacks split the buffer into chunks.
6. Each chunk is cache-cleaned and sent to the GUI.

### Signal Generation Layer

The AD9833 DDS is controlled through SPI1.

- SPI mode: master, transmit only
- DDS chip select: PD14
- DDS reference clock constant in firmware: 25 MHz
- Frequency tuning word is calculated from:

```text
tuning_word = requested_frequency * 2^28 / 25 MHz
```

DDS states:

- stopped: reset/sleep command is sent to AD9833
- running: B28 mode is enabled and the configured frequency word is applied

### Board Control GPIO Layer

The firmware controls analog front-end routing and gain through GPIOs.

- PE/PR select: PE9
- actuator source select: PE11
- BNC/ADC routing: PE14
- PE gain bit A0: PE13
- PE gain bit A1: PG14
- DDS chip select: PD14

Board modes:

- PE mode
- PR mode

Actuator modes:

- DDS excitation from AD9833
- external function generator
- STM32 DAC path placeholder

## 4. Runtime Data Flow

```mermaid
sequenceDiagram
    participant GUI as PC GUI
    participant UDP as Ethernet UDP / USB CDC
    participant APP as Command Parser
    participant TIM as TIM6
    participant ADC as ADC1+ADC2
    participant DMA as DMA1
    participant BUF as D1 RAM Buffer
    participant AFE as Analog Front-End
    participant DDS as AD9833 DDS

    GUI->>UDP: START / ADC SAMP / DAC FREQ commands
    UDP->>APP: command string
    APP->>TIM: configure/start trigger
    APP->>DDS: SPI frequency/start command
    DDS->>AFE: sine excitation
    TIM->>ADC: TRGO sample trigger
    AFE->>ADC: MEMS and reference analog inputs
    ADC->>DMA: packed dual ADC sample
    DMA->>BUF: circular transfer
    DMA->>APP: half/full complete callback
    APP->>UDP: send sample chunks
    UDP->>GUI: binary ADC stream/status text
```

## 5. GUI Architecture

The PC GUI should be separated into these modules:

```mermaid
flowchart TB
    UI[GUI User Interface\nControls and plots]
    CTRL[Test Controller\nRun state and parameter validation]
    TRANSPORT[Transport Adapter\nUDP Ethernet or USB CDC]
    DECODER[Sample Decoder\nPacked dual-ADC words to channels]
    PLOT[Real-Time Plotter\nMEMS and reference channels]
    LOG[Data Logger\nCSV/binary export]

    UI --> CTRL
    CTRL --> TRANSPORT
    TRANSPORT --> CTRL
    TRANSPORT --> DECODER
    DECODER --> PLOT
    DECODER --> LOG
    CTRL --> UI
    PLOT --> UI
```

Recommended GUI functions:

- Connect/disconnect to board.
- Select transport:
  - Ethernet UDP for Nucleo-H723ZG.
  - USB HS CDC for Nucleo-H7S3L8.
- Configure sample rate, ADC resolution, and buffer size.
- Start/stop ADC acquisition.
- Start/stop DDS.
- Set DDS frequency.
- Select PE/PR mode.
- Select actuator source.
- Select PE gain.
- Plot MEMS and reference channels in real time.
- Save raw and processed data.
- Show board status and connection health.

## 6. Communication Protocol

### Command Direction

GUI to STM32:

```text
ASCII command strings
Ethernet: UDP port 5006
USB option: CDC OUT endpoint
```

STM32 to GUI:

```text
Status text and binary ADC chunks
Ethernet: UDP port 5005
USB option: CDC IN endpoint
```

### Existing Commands

| Command | Purpose |
| --- | --- |
| `BOARD?` | Request board identification |
| `BUF,<samples>` | Set active DMA buffer size |
| `ADC SAMP,<Hz>` | Set TIM6-derived ADC sampling rate |
| `ADC RES,<bits>` | Set ADC resolution: 10, 12, 14, or 16 |
| `START` | Start ADC acquisition |
| `STOP` | Stop ADC acquisition |
| `DAC START` | Start DDS output |
| `DAC STOP` | Stop DDS output |
| `DAC FREQ,<Hz>` | Set AD9833 output frequency |
| `MODE,PE` | Select PE board mode |
| `MODE,PR` | Select PR board mode |
| `ACTUATOR,DDS` | Select AD9833 DDS excitation |
| `ACTUATOR,FG` | Select external function generator |
| `ACTUATOR,STM32` | Select STM32 actuator path |
| `PE GAIN,<0..3>` | Set PE gain GPIO code |

## 7. Hardware Interface Summary

| Interface | STM32 Peripheral | External Block | Purpose |
| --- | --- | --- | --- |
| SPI1 | SPI master TX | AD9833 DDS | Configure sine-wave excitation |
| ADC1 | ADC channel 15 | Analog front-end reference/MEMS path | Dual simultaneous acquisition |
| ADC2 | ADC channel 5 | Analog front-end reference/MEMS path | Dual simultaneous acquisition |
| TIM6 | TRGO update | ADC trigger | Fixed-rate sampling |
| DMA1 Stream0 | ADC1 request | D1 RAM buffer | Circular sample transfer |
| Ethernet | MAC + LAN8742 PHY | PC GUI | UDP command/data link |
| USB HS CDC | USB device FS/HS stack | PC GUI | Alternative command/data link |
| GPIO | PE9, PE11, PE13, PE14, PG14, PD14 | Analog routing and DDS CS | Mode/gain/source control |
| UART3 | USART3 | Debug console | Optional debug output |

## 8. Recommended Final Block Diagram

Use this structure for the final report diagram:

```text
PC GUI
  |  commands: ASCII strings
  |  data: ADC binary stream + status
  v
Communication Interface
  - Nucleo-H723ZG: Ethernet UDP + LwIP
  - Nucleo-H7S3L8: USB HS CDC
  |
  v
STM32 Application Firmware
  - command parser
  - acquisition state machine
  - DDS control
  - board mode/gain control
  |
  +--> AD9833 DDS over SPI1 --> analog excitation
  |
  +--> GPIO control lines --> analog front-end routing/gain
  |
  +--> TIM6 trigger --> dual ADC simultaneous sampling
                         |
                         v
                     DMA circular buffer
                         |
                         v
                  streamed sample chunks to GUI

Analog Front-End
  - amplifier / Wheatstone bridge
  - MEMS cantilever signal
  - reference signal
```

## 9. Notes for Improvement

- Add an explicit packet header for ADC data containing sequence number, sample rate, resolution, channel format, and payload length.
- Add acknowledgements for configuration commands.
- Add error/status messages for invalid commands.
- Consider moving UDP/USB behind a common transport API so the same application layer supports both Nucleo-H723ZG and Nucleo-H7S3L8.
- Consider moving ADC streaming out of interrupt callbacks into a main-loop or RTOS task queue if packet handling becomes too heavy.

## 10. Embedded Firmware Code Flowchart

This flowchart follows the current `Core/Src/main.c` execution path.

```mermaid
flowchart TD
    RESET([Reset / Power On])
    MPU[Configure MPU]
    CACHE[Enable I-Cache and D-Cache]
    HAL[HAL_Init]
    CLOCK[SystemClock_Config\nPeriphCommonClock_Config]
    INIT[Initialize peripherals\nGPIO, DMA, ADC2, TIM6, LwIP,\nUSART3, ADC1, SPI1]
    DDSINIT[DDS init\nAD9833 reset/sleep\nset default frequency]
    ADCSTART[Start ADC2 slave\nStart ADC1 dual-mode DMA\nStart TIM6 trigger]
    UDPINIT[Create UDP TX PCB\nconnect to PC port 5005\nCreate UDP RX PCB\nbind to port 5006]
    DEFAULTS[Set default test state\nPE mode, DDS actuator,\nPE gain 0]
    LOOP{{Main while loop}}
    LWIP[MX_LWIP_Process\nEthernet input, UDP receive,\ntimeouts, link check]

    RESET --> MPU --> CACHE --> HAL --> CLOCK --> INIT
    INIT --> DDSINIT --> ADCSTART --> UDPINIT --> DEFAULTS --> LOOP
    LOOP --> LWIP --> LOOP
```

### Embedded Command Receive Flow

```mermaid
flowchart TD
    RXPKT([UDP packet received on port 5006])
    COPY[Copy packet payload into command buffer]
    SETDEST[Update UDP transmit destination\nusing sender IP]
    PARSE[parse_command]
    BOARD{Command type?}

    RXPKT --> COPY --> SETDEST --> PARSE --> BOARD

    BOARD -->|BOARD?| BOARDRESP[Send board status text]
    BOARD -->|BUF,n| BUF[Validate and update active DMA buffer size]
    BOARD -->|ADC SAMP,fs| FS[Validate sampling rate\nstop ADC if running\nupdate TIM6 auto-reload]
    BOARD -->|ADC RES,bits| RES[Validate resolution\nstop ADC if running\nreinitialize ADC1/ADC2]
    BOARD -->|START| START[Start ADC2, ADC1 DMA, TIM6]
    BOARD -->|STOP| STOP[Stop TIM6, ADC DMA, ADC2]
    BOARD -->|DAC START| DDSSTART[Enable AD9833 output]
    BOARD -->|DAC STOP| DDSSTOP[Reset/sleep AD9833]
    BOARD -->|DAC FREQ,f| DDSFREQ[Calculate tuning word\nwrite AD9833 frequency registers]
    BOARD -->|MODE,PE / MODE,PR| MODE[Set PE/PR GPIO]
    BOARD -->|ACTUATOR,...| ACT[Set actuator routing GPIO]
    BOARD -->|PE GAIN,n| GAIN[Set PE gain GPIO bits]
    BOARD -->|Unknown| IGNORE[Ignore command]

    BOARDRESP --> DONE([Return to LwIP/main loop])
    BUF --> DONE
    FS --> DONE
    RES --> DONE
    START --> DONE
    STOP --> DONE
    DDSSTART --> DONE
    DDSSTOP --> DONE
    DDSFREQ --> DONE
    MODE --> DONE
    ACT --> DONE
    GAIN --> DONE
    IGNORE --> DONE
```

### Embedded ADC Streaming Flow

```mermaid
flowchart TD
    TIM6([TIM6 update event / TRGO])
    SAMPLE[ADC1 and ADC2 sample simultaneously]
    PACK[ADC multimode packs dual result\ninto 32-bit word]
    DMA[DMA1 Stream0 writes sample\ninto circular adc_buffer]
    HALF{DMA event?}
    FIRST[Half-complete callback\nprocess first half of buffer]
    SECOND[Complete callback\nprocess second half of buffer]
    CHUNK[Split selected half into\nCHUNK_SIZE blocks]
    CACHE[Clean D-Cache for chunk]
    PBUF[Create LwIP pbuf reference\nto ADC buffer memory]
    SEND[udp_send to GUI port 5005]
    FREE[Free pbuf]

    TIM6 --> SAMPLE --> PACK --> DMA --> HALF
    HALF -->|Half complete| FIRST --> CHUNK
    HALF -->|Full complete| SECOND --> CHUNK
    CHUNK --> CACHE --> PBUF --> SEND --> FREE
    FREE --> TIM6
```

### Embedded DDS Control Flow

```mermaid
flowchart TD
    CMD([DDS command from GUI])
    TYPE{Command}
    START[DDS START\nset dds_running = 1]
    STOP[DDS STOP\nset dds_running = 0]
    FREQ[DDS FREQ,f\nvalidate requested frequency]
    WORD[Calculate AD9833 28-bit tuning word]
    WRITECTRL[Write AD9833 control word\nB28 + RESET]
    WRITELSB[Write frequency LSB word over SPI1]
    WRITEMSB[Write frequency MSB word over SPI1]
    RUNNING{dds_running?}
    ENABLE[Write B28 control word\nDDS output enabled]
    SLEEP[Write B28 + RESET + SLEEP1\nDDS output disabled]

    CMD --> TYPE
    TYPE -->|DAC START| START --> WORD
    TYPE -->|DAC STOP| STOP --> SLEEP
    TYPE -->|DAC FREQ,f| FREQ --> WORD
    WORD --> WRITECTRL --> WRITELSB --> WRITEMSB --> RUNNING
    RUNNING -->|Yes| ENABLE
    RUNNING -->|No| SLEEP
```

## 11. GUI Code Flowchart

This is the recommended GUI code flow. It matches the firmware command protocol and supports either Ethernet UDP or HS USB CDC behind the same transport interface.

```mermaid
flowchart TD
    GUISTART([Start GUI application])
    INITUI[Create main window\ncontrols, plots, status panel]
    LOAD[Load default settings\nboard IP, UDP ports,\nsample rate, buffer size]
    TRANSPORT{Select transport}
    UDP[Open UDP sockets\nTX to board port 5006\nRX on PC port 5005]
    USB[Open USB CDC port\nfor H7S3L8 option]
    ID[Send BOARD?]
    WAIT[Wait for board response]
    READY[GUI ready]

    GUISTART --> INITUI --> LOAD --> TRANSPORT
    TRANSPORT -->|Ethernet / H723ZG| UDP --> ID
    TRANSPORT -->|HS USB CDC / H7S3L8| USB --> ID
    ID --> WAIT --> READY
```

### GUI Control Flow

```mermaid
flowchart TD
    READY{{GUI event loop}}
    EVENT{User action?}
    SAMPLE[User changes sample rate]
    RES[User changes ADC resolution]
    BUF[User changes buffer size]
    START[User presses Start]
    STOP[User presses Stop]
    DDSF[User changes DDS frequency]
    DDSSTART[User presses DDS Start]
    DDSSTOP[User presses DDS Stop]
    MODE[User selects PE/PR mode]
    ACT[User selects actuator source]
    GAIN[User selects PE gain]

    TX[Format ASCII command]
    SEND[Send command through\nUDP or USB CDC]
    STATE[Update local GUI state\nand status display]

    READY --> EVENT
    EVENT -->|Sample rate| SAMPLE --> TX
    EVENT -->|ADC resolution| RES --> TX
    EVENT -->|Buffer size| BUF --> TX
    EVENT -->|Start acquisition| START --> TX
    EVENT -->|Stop acquisition| STOP --> TX
    EVENT -->|DDS frequency| DDSF --> TX
    EVENT -->|DDS start| DDSSTART --> TX
    EVENT -->|DDS stop| DDSSTOP --> TX
    EVENT -->|PE/PR mode| MODE --> TX
    EVENT -->|Actuator source| ACT --> TX
    EVENT -->|PE gain| GAIN --> TX
    TX --> SEND --> STATE --> READY
```

Command examples generated by the GUI:

```text
ADC SAMP,100000
ADC RES,16
BUF,4096
START
STOP
DAC FREQ,1000
DAC START
DAC STOP
MODE,PE
MODE,PR
ACTUATOR,DDS
ACTUATOR,FG
PE GAIN,2
```

### GUI Data Receive Flow

```mermaid
flowchart TD
    RX([Receive data from STM32])
    KIND{Payload type?}
    TEXT[Status text packet]
    BINARY[Binary ADC sample packet]
    DISPLAY[Update status display]
    UNPACK[Unpack 32-bit dual ADC words]
    CH1[Extract channel 1\nMEMS or reference]
    CH2[Extract channel 2\nMEMS or reference]
    SCALE[Convert counts to voltage\nusing ADC resolution and Vref]
    FILTER[Optional filtering / FFT / amplitude calculation]
    PLOT[Update real-time plots]
    LOG{Logging enabled?}
    SAVE[Write samples to file]
    DROP[Discard after plotting]

    RX --> KIND
    KIND -->|ASCII/status| TEXT --> DISPLAY
    KIND -->|ADC stream| BINARY --> UNPACK
    UNPACK --> CH1 --> SCALE
    UNPACK --> CH2 --> SCALE
    SCALE --> FILTER --> PLOT --> LOG
    LOG -->|Yes| SAVE
    LOG -->|No| DROP
    SAVE --> RX
    DROP --> RX
    DISPLAY --> RX
```

## 12. Combined Embedded and GUI Flowchart

```mermaid
flowchart LR
    subgraph GUI[PC GUI Code]
        UI[User changes settings\nor presses Start/Stop]
        CMD[Build ASCII command]
        TX[Send via UDP or USB CDC]
        RX[Receive ADC/status data]
        DEC[Decode samples]
        PLOT[Plot and log data]
    end

    subgraph FW[STM32 Embedded Code]
        COMMS[Receive command]
        PARSER[parse_command]
        CFG[Configure ADC/TIM/DDS/GPIO]
        TRIG[TIM6 trigger]
        ADC[Dual ADC sample]
        DMA[DMA circular buffer]
        CB[Half/full callback]
        STREAM[Send sample chunks]
    end

    UI --> CMD --> TX --> COMMS --> PARSER --> CFG
    CFG --> TRIG --> ADC --> DMA --> CB --> STREAM --> RX
    RX --> DEC --> PLOT
    PLOT --> UI
```
