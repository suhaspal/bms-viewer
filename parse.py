### IMPORTS ###
from queue import Queue
from time import time

import can

from data_processing import CANMessage


class CANMessageListener(can.Listener):
    def __init__(self, max_queue_size=1000):
        """Set up a queue for storing CAN messages, capped at a specified size"""
        self.messages = Queue(maxsize=max_queue_size)
        self.overflow_count = 0

    def on_message_received(self, msg: can.Message):
        """Transform the incoming CAN message into our custom CANMessage format"""
        can_message = CANMessage(msg.arbitration_id, msg.data)
        if not self.messages.full():
            self.messages.put_nowait(can_message)
        else:
            self.overflow_count += 1
            self.messages.get_nowait()
            self.messages.put_nowait(can_message)

    def get_message(self, timeout=0.5) -> can.Message | None:
        """Extract a message from the queue if available, blocks for given timeout or until a message is received (whichever is shorter)."""
        if not self.messages.empty():
            return self.messages.get(timeout=timeout)
        return None

    def get_overflow_count(self) -> int:
        """Report the total number of messages that exceeded queue capacity"""
        return self.overflow_count


class CANFakeBus(can.BusABC):
    def __init__(self, can_data_file: str):
        try:
            self.reader = can.CanutilsLogReader(can_data_file)
        except OSError:
            print(
                f"Error: Invalid path provided for supplied CAN data: {can_data_file}"
            )
            exit(-1)

        self.set_filters(None)

        self.message_index = 0
        self.messages = [next(iter(self.reader))]
        self.bus_start_time = self.messages[0].timestamp
        self.real_start_time = time()

    def bus_time(self):
        return self.bus_start_time + (time() - self.real_start_time)

    def next_msg(self):
        # file is done reading (or array is filled up to target index), read from array
        if self.reader is None or self.message_index < len(self.messages):
            msg = self.messages[self.message_index % len(self.messages)]

            self.message_index += 1
            if self.reader is None:
                self.message_index %= len(self.messages)

            return msg

        else:
            # attempt to read from file
            msg = next(iter(self.reader), None)

            # reached end of file, close reader, set to None
            if msg is None:
                self.reader.stop()
                self.reader = None
                return self.next_msg()

            self.messages.append(msg)
            self.message_index += 1

            return msg

    # cannot send messages
    def send(msg, timeout=None): ...

    def _recv_internal(self, timeout=None):
        # checking for timeout
        recv_start_time = time()

        # get message
        msg = self.next_msg()

        # wait until real time has elapsed
        while msg.timestamp > self.bus_time():
            # or, until timeout has elapsed
            if timeout is not None and time() - recv_start_time > timeout:
                break

        # reset timer if looping back to start of log
        if self.message_index == 0:
            self.real_start_time = time()

        # (message, filtered?)
        return (msg, False)

    def _apply_filters(self, filters): ...


class CANMessageParser:
    def __init__(self, filtering, can_bus, max_queue_size=1000):
        """Establish a connection to the CAN bus along with setting the max queue size."""
        self.bus = can_bus
        self.bus.set_filters(filtering)
        self.listener = CANMessageListener(max_queue_size)
        self.notifier = can.Notifier(self.bus, [self.listener])

    def get_messages(self, num_messages: int, timeout=0.5) -> list[can.Message]:
        """Collect a specified number of messages from the listener"""
        messages = []
        for i in range(num_messages):
            message = self.listener.get_message(timeout)
            if message is not None:
                messages.append(message)
        return messages

    def send_can_messages(self, msg: CANMessage, is_extended_id=False):
        """Construct a CAN message from the provided CANMessage object"""
        message = can.Message(
            arbitration_id=msg.arbitration_id,
            data=msg.data,
            is_extended_id=is_extended_id,
        )
        try:
            self.bus.send(message)
        except can.CanError:
            print("Failed to send message")

    def get_overflow_count(self) -> int:
        """Retrieve the total count of messages that exceeded queue capacity"""
        return self.listener.get_overflow_count()

    def empty_queue(self):
        """Clear all messages from the queue"""
        while not self.listener.messages.empty():
            self.listener.messages.get_nowait()

    def stop(self):
        """Stop notifier and close CAN bus connection"""
        self.notifier.stop()
        self.bus.shutdown()
