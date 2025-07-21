class CANMessage:
    """
    This class provides a standard format for how a CANMessage can be
    stored and referenced throughout a program.
    """

    def __init__(self, arbitration_id: int, data: bytearray | list[int]):
        self.arbitration_id = arbitration_id
        self.data = data


class ProcessedData:
    """
    This class provides a standard format for how the decoded values of a
    CANMessage can be stored and referenced throughout a program.
    """

    def __init__(self, message_type: str, values: dict):
        self.message_type = message_type
        self.values = values


class CANMessageHandler:
    """
    This class two functions, encode and decode, that the user can use when
    sending or receiving can messages. The class is initalized using a lookup table,
    which is referenced when the function routes the can message to its appropriate decoding function.
    Keep in mind that these two functions are only supposed to be used when encoding or decoding
    individual can messages.

    For projects like the BMS viewer, use the BMS_data_processing file in order to process messages
    in a way that is more optimized for that use case.
    """

    def __init__(self, lookup: dict):
        """Intialize this class with a lookup table. The lookup table should be in the form of a dictionary."""
        self.lookup = lookup

    def decode_message(self, message: CANMessage) -> ProcessedData | None:
        """Process a CAN message based on its arbitration ID using the lookup table."""
        if message.arbitration_id in self.lookup:
            return self.lookup[message.arbitration_id][0](message.data)
        else:
            print("Arbitration ID not recognized.")
            return None

    def encode_message(self, message: ProcessedData) -> CANMessage | None:
        """Encode a ProcessedData message based on its message type using the lookup table."""
        if message.message_type in self.lookup:
            return self.lookup[message.message_type](message.values)
        else:
            print("Message Type not recognized.")
            return None
