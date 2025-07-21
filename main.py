import argparse

import can
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from heatmapGUI import HeatmapGUI
from parse import CANFakeBus


def main():
    """
    1. Parse arguments
    2. Create the QApplication instance
    3. Create the CAN bus instance
    4. Create the HeatmapGUI instance
    5. Start the application event loop
    """
    parser = argparse.ArgumentParser(description="BMS Data Viewer")
    parser.add_argument(
        "--interface",
        help="Specify interface such as pcan, fake, socketcan",
        choices=["fake", "socketcan", "pcan", "virtual"],
        default="pcan",
    )
    parser.add_argument(
        "--channel",
        help="Specify channel such as PCAN_USBBUS1, vcan0, can0",
        default="PCAN_USBBUS1",
    )
    parser.add_argument(
        "--file", metavar="CAN DATA SOURCE FILE", default="can_data.log"
    )
    args = parser.parse_args()

    # Create CAN bus
    if args.interface == "fake":
        if args.file is None:
            print(
                'ERROR: Provide CAN data file with "--file FILE" to use fake interface.'
            )
            exit(-1)

        bus = CANFakeBus(args.file)
    else:
        try:
            bus = can.Bus(
                channel=args.channel,
                interface=args.interface,
                receive_own_messages=False,
            )
        except can.interfaces.pcan.pcan.PcanCanInitializationError:
            print("ERROR: Invalid interface/channel specified!")
            exit(-1)

    app = QApplication([])
    heatmapGUI = HeatmapGUI(bus)
    app.exec_()


if __name__ == "__main__":
    main()
