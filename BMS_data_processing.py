import can

from BMS_dispatcher import BMSLOOKUP
from data_processing import CANMessage, CANMessageHandler, ProcessedData


class BMSData:
    """
    This class is meant act as a retriver for the visualization component of the BMS viewer.
    It serves three main purposes:
    1. Contains the logic to receive a CANMessage and route it to the appropriate decoding function
    2. Store the decoded values of the most recent type of every CANMessage (CELLVAL, BMSVINF, BMSTINF, etc.)
    3. Contains getter functions to access those values from other parts of the program.
    """

    def __init__(self):
        """
        Containers for storing most recent decoded values.
        Each container should be of the ProcessedData object type,
        except for the cell val container, which will be a
        144 item list of ProcessedData objects.
        """
        self.processed_bms_cell_vals = [None] * 144
        self.processed_bms_system_voltage = None
        self.processed_bms_system_temp = None
        self.processed_bms_faults = None
        self.processed_pack_status = None
        self.processed_charger_out = None

    def process_bms_messages(self, messages: list[can.Message]) -> None:
        """
        This function contains the logic for routing a received CANMessage to
        its appropriate decoding function. It then places the returned ProcessedData
        object in its appropriate container.
        """
        handler = CANMessageHandler(BMSLOOKUP)
        for individual_message in messages:
            if individual_message.arbitration_id in BMSLOOKUP:
                decoded_message = handler.decode_message(individual_message)
                match BMSLOOKUP[individual_message.arbitration_id][1]:
                    case "CELLVALUE":
                        self.processed_bms_cell_vals[
                            decoded_message.values["cell_number"] - 1
                        ] = decoded_message
                    case "BMSSTAT":
                        self.processed_bms_faults = decoded_message
                    case "BMSVINF":
                        self.processed_bms_system_voltage = decoded_message
                    case "BMSTINF":
                        self.processed_bms_system_temp = decoded_message
                    case "PACKSTAT":
                        self.processed_pack_status = decoded_message
                    case "CHARGEROUT":
                        self.processed_charger_out = decoded_message
                    case _:
                        print(f'failed to decode {decoded_message}')

    def get_bms_cell_vals(self) -> list[ProcessedData] | list[None]:
        return self.processed_bms_cell_vals

    def get_bms_system_voltage(self) -> ProcessedData:
        return self.processed_bms_system_voltage

    def get_bms_system_temp(self) -> ProcessedData:
        return self.processed_bms_system_temp

    def get_bms_processed_faults(self) -> ProcessedData:
        return self.processed_bms_faults

    def get_bms_pack_status(self) -> ProcessedData:
        return self.processed_pack_status

    def get_bms_charger_out(self) -> ProcessedData:
        return self.processed_charger_out
