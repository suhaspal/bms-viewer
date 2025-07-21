##### IMPORTS #####
from data_processing import CANMessage, ProcessedData
import cantools

##### CONSTANTS #####
VOLTAGE_OFFSET = 10000.0
DISCHARGE_THRESHOLD_OFFSET = 10000
TEMPERATURE_OFFSET = 1000.0
DECIMAL_OFFSET = 10.0
CELLVALUE_HEX = 0x620
BMSSTAT_HEX = 0x220
BMSVINF_HEX = 0x720
BMSTINF_HEX = 0x721
PACKSTAT_HEX = 0x180
CHARGER_OUT_HEX = 0x405
CHARGER_IN_HEX = 0x381
POLLING_HEX = 0x380

db = cantools.database.load_file('can_1.dbc')

##### BMS DECODING FUNCTIONS #####
def decode_cell_value(data: bytearray) -> ProcessedData:
    data.extend([0] * (8 - len(data)))
    decoded = db.decode_message(CELLVALUE_HEX, data)
    ret = ProcessedData(
        message_type="CELLVALUE",
        values={
            "cell_number": decoded["idx_cell_data"],
            "cell_voltage": decoded["vlt_cell_data"],
            "cell_temperature": decoded["temp_cell_data"],
        },
    )
    return ret

def decode_bmsvinf(data: bytearray) -> ProcessedData:
    data.extend([0] * (6 - len(data)))
    decoded = db.decode_message(BMSVINF_HEX, data)
    return ProcessedData(
        message_type="BMSVINF",
        values={
            "max_voltage": decoded["vlt_cell_max"],
            "min_voltage": decoded["vlt_cell_min"],
            "avg_voltage": 0,
            "max_voltage_cell": decoded["idx_vlt_min"],
            "min_voltage_cell": decoded["idx_vlt_max"],
        },
    )


def decode_bmstinf(data: bytearray) -> ProcessedData:
    data.extend([0] * (6 - len(data)))
    decoded = db.decode_message(BMSTINF_HEX, data)
    return ProcessedData(
        message_type="BMSTINF",
        values={
            "max_temp": decoded["temp_cell_max"],
            "min_temp": decoded["temp_cell_min"],
            "avg_temp": 0,
            "max_temp_cell": decoded["idx_temp_min"],
            "min_temp_cell": decoded["idx_temp_max"],
        },
    )


def decode_bmsstat(data: bytearray) -> ProcessedData:
    data.extend([0] * (6 - len(data)))
    decoded = db.decode_message(BMSSTAT_HEX, data)
    faults = {}
    if decoded["bms_fault_ovp"]:
        faults["Over Voltage"] = decoded["bms_fault_ovp"]
    if decoded["bms_fault_uvp"]:
        faults["Under Voltage"] = decoded["bms_fault_uvp"]
    if decoded["bms_fault_otp"]:
        faults["Over Temp"] = decoded["bms_fault_otp"]
    if decoded["bms_fault_utp"]:
        faults["Under Temp"] = decoded["bms_fault_utp"]

    return ProcessedData(message_type="BMSSTAT", values={"faults": faults})


# Removed
def decode_packstat(data: bytearray) -> ProcessedData:
    pack_voltage = ((data[0] << 8) | data[1]) / DECIMAL_OFFSET
    pack_current = ((data[2] << 8) | data[3]) / DECIMAL_OFFSET
    pack_power = ((data[4] << 8) | data[5]) / DECIMAL_OFFSET

    return ProcessedData(
        message_type="PACKSTAT",
        values={
            "pack_voltage": pack_voltage,
            "pack_current": pack_current,
            "pack_power": pack_power,
        },
    )


def decode_charger_out(message: CANMessage) -> ProcessedData:
    charger_voltage = ((message.data[0] << 8) | message.data[1]) / DECIMAL_OFFSET
    charger_current = ((message.data[2] << 8) | message.data[3]) / DECIMAL_OFFSET
    status_byte = message.data[4]

    status_errors = []
    if status_byte & 0x01:
        status_errors.append("Hardware Malfunction")
    if status_byte & 0x02:
        status_errors.append("Charger Temperature")
    if status_byte & 0x04:
        status_errors.append("Input Voltage Error")
    if status_byte & 0x08:
        status_errors.append("Battery Connection Error")
    if status_byte & 0x10:
        status_errors.append("Communication Timeout")

    return ProcessedData(
        message_type="CHARGEROUT",
        values={
            "charger_voltage": charger_voltage,
            "charger_current": charger_current,
            "status_errors": status_errors,
        },
    )


### BMS ENCODING FUNCTIONS ###
def encode_manual_charge(values: dict) -> CANMessage:
    charge_enable = values["charge_enable"]
    voltage = values["voltage"]
    current = values["current"]
    discharge_balance_enable = values["discharge_balance"]
    discharge_threshold = values["discharge_threshold"]

    voltage_raw = int(voltage * DECIMAL_OFFSET)
    current_raw = int(current * DECIMAL_OFFSET)
    discharge_threshold_raw = int(discharge_threshold * DISCHARGE_THRESHOLD_OFFSET)

    voltage_high_byte = (voltage_raw >> 8) & 0xFF
    voltage_low_byte = voltage_raw & 0xFF
    current_high_byte = (current_raw >> 8) & 0xFF
    current_low_byte = current_raw & 0xFF
    discharge_raw_high_byte = (discharge_threshold_raw >> 8) & 0xFF
    discharge_raw_low_byte = discharge_threshold_raw & 0xFF

    return CANMessage(
        arbitration_id=CHARGER_IN_HEX,
        data=[
            charge_enable,
            voltage_high_byte,
            voltage_low_byte,
            current_high_byte,
            current_low_byte,
            discharge_balance_enable,
            discharge_raw_high_byte,
            discharge_raw_low_byte,
        ],
    )

def encode_polling() -> CANMessage:
    return CANMessage(
        arbitration_id=POLLING_HEX,
        data=[0xFF]
    )

### BMS LOOKUP TABLE ###
"""
If the key in this dictionary is a number, then 
you know that message is one that is meant to be received
and decoded.

If the key is a string, then that message is one that
is meant to be encoded and sent elsewhere.
"""
BMSLOOKUP = {
    CELLVALUE_HEX: (decode_cell_value, "CELLVALUE"),
    BMSSTAT_HEX: (decode_bmsstat, "BMSSTAT"),
    BMSVINF_HEX: (decode_bmsvinf, "BMSVINF"),
    BMSTINF_HEX: (decode_bmstinf, "BMSTINF"),
    PACKSTAT_HEX: (decode_packstat, "PACKSTAT"),
    CHARGER_OUT_HEX: (decode_charger_out, "CHARGEROUT"),
    "CHARGERIN": encode_manual_charge,
}

### BMS CAN BUS FILTERS ###
BMSFILTERS = [
    {"can_id": CELLVALUE_HEX, "can_mask": 0xFFF, "extended": False},
    {"can_id": BMSSTAT_HEX, "can_mask": 0xFFF, "extended": False},
    {"can_id": BMSVINF_HEX, "can_mask": 0xFFF, "extended": False},
    {"can_id": BMSTINF_HEX, "can_mask": 0xFFF, "extended": False},
    {"can_id": PACKSTAT_HEX, "can_mask": 0xFFF, "extended": False},
    {"can_id": CHARGER_OUT_HEX, "can_mask": 0xFFF, "extended": False},
    {"can_id": CHARGER_IN_HEX, "can_mask": 0xFFF, "extended": False},
]
