"""
A script to convert from a .csv CAN format to
candump -L format (.log)

Columns:
seconds,bus,id,data
"""

import can

inf = "candump_murphy_11-11-24.csv"
outf = "candump_murphy_11-11-24.log"

if __name__ == "__main__":
    with open(inf, "r") as f:
        with can.CanutilsLogWriter(file=outf) as writer:
            next(f)
            for line in f:
                timestamp, busnum, can_id, data = line.strip().split(",")

                writer.on_message_received(
                    can.Message(
                        timestamp=float(timestamp),
                        is_extended_id=int(can_id, 16) >= 0x800,
                        arbitration_id=int(can_id, 16),
                        channel=f"PCAN_USBBUS{int(busnum)}",
                        data=bytes.fromhex(data),
                    )
                )
