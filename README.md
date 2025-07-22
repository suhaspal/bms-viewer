# BMS Viewer

A real-time Battery Management System (BMS) data visualization tool built with PyQt5. This application provides a graphical interface for monitoring battery cell voltages, temperatures, and system status through CAN bus communication.

## Overview

The BMS Viewer displays battery pack data in an intuitive heatmap format, allowing users to monitor the health and performance of individual battery cells in real-time. The application supports multiple CAN interfaces and can process both live data streams and recorded CAN data files.

## Features

### Real-time Monitoring
- **Cell Voltage Visualization**: Displays voltage data for up to 144 battery cells in a 12x12 heatmap grid
- **Temperature Monitoring**: Real-time temperature visualization with safety threshold indicators
- **System Status**: Monitors BMS system voltage, pack status, and charger output
- **Fault Detection**: Displays BMS fault conditions and alerts

### Data Visualization
- **Interactive Heatmap**: Color-coded visualization where cells are colored based on voltage/temperature values
- **Safety Thresholds**: Built-in safe operating ranges (3.0-4.2V for voltage, 0-60°C for temperature)
- **Cell Selection**: Click on individual cells to view detailed information
- **Real-time Updates**: Continuous data refresh for live monitoring

### CAN Bus Support
- **Multiple Interfaces**: Support for PCAN, SocketCAN, Virtual, and Fake interfaces
- **Flexible Configuration**: Configurable channel and interface selection
- **Data Playback**: Ability to replay recorded CAN data from log files
- **Message Processing**: Automatic decoding of BMS-specific CAN messages

### User Interface
- **Control Panel**: Start/stop data acquisition controls
- **Status Indicators**: Visual feedback for connection and data flow status
- **Responsive Layout**: Organized layout with data visualization and control elements

## Installation

### Prerequisites
- Python 3.7 or higher
- PyQt5
- python-can library

### Dependencies
Install the required packages using pip:

```bash
pip install -r requirements.txt
```

Required packages:
- numpy
- python-can
- PyQt5
- cantools
- uptime

## Usage

### Command Line Arguments

```bash
python main.py [options]
```

**Options:**
- `--interface`: CAN interface type (choices: fake, socketcan, pcan, virtual)
  - Default: `pcan`
- `--channel`: CAN channel specification (e.g., PCAN_USBBUS1, vcan0, can0)
  - Default: `PCAN_USBBUS1`
- `--file`: CAN data source file (required when using fake interface)
  - Default: `can_data.log`

### Examples

**Live monitoring with PCAN interface:**
```bash
python main.py --interface pcan --channel PCAN_USBBUS1
```

**Playback from recorded data:**
```bash
python main.py --interface fake --file my_can_data.log
```

**SocketCAN interface:**
```bash
python main.py --interface socketcan --channel can0
```

### Interface Guide

1. **Launch the Application**: Run the main.py script with appropriate arguments
2. **Connect to CAN Bus**: The application automatically connects to the specified CAN interface
3. **Start Monitoring**: Use the start button to begin data acquisition
4. **View Data**: Monitor the heatmap display for real-time cell data
5. **Cell Details**: Click on individual cells to view specific voltage/temperature values
6. **Stop Monitoring**: Use the stop button to pause data acquisition

## Project Structure

### Core Components

- **main.py**: Application entry point and argument parsing
- **heatmapGUI.py**: Main GUI implementation and user interface logic
- **heatmap.py**: Heatmap visualization widget and cell rendering
- **BMS_data_processing.py**: BMS message decoding and data storage
- **parse.py**: CAN message parsing and fake bus implementation
- **data_processing.py**: Core data structures and message handling
- **BMS_dispatcher.py**: Message routing and encoding functions
- **worker.py**: Background threading for data acquisition
- **convert.py**: Data conversion utilities

### Data Types Supported

The application processes the following BMS data types:
- **CELLVAL**: Individual cell voltage measurements
- **BMSVINF**: BMS voltage information
- **BMSTINF**: BMS temperature information  
- **BMS Faults**: System fault conditions
- **Pack Status**: Overall battery pack status
- **Charger Output**: Charging system information

## Technical Details

### Safety Parameters
- **Voltage Range**: 3.0V - 4.2V (safe operating range)
- **Temperature Range**: 0°C - 60°C (safe operating range)
- **Cell Count**: Supports up to 144 cells in 12x12 configuration

### Performance
- **Message Queue**: Handles up to 1000 CAN messages with overflow protection
- **Update Rate**: Real-time visualization with configurable refresh intervals
- **Memory Management**: Efficient data structure management for continuous operation

### CAN Message Format
The application expects BMS-specific CAN message formats with appropriate arbitration IDs and data payloads. Message decoding is handled automatically based on the configured BMS protocol.