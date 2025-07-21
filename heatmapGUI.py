### IMPORTS ###
import sys
import time

import numpy as np
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtWidgets import QCheckBox, QComboBox

from BMS_data_processing import BMSData
from BMS_dispatcher import BMSFILTERS, encode_manual_charge, encode_polling
from heatmap import Heatmap
from parse import CANMessageParser
from worker import TimedWorker, Worker

### CONSTANTS ###
MIN_SAFE_VOLTAGE = 3.0
MAX_SAFE_VOLTAGE = 4.2
MIN_SAFE_TEMPERATURE = 0.0
MAX_SAFE_TEMPERATURE = 60.0
QUIT_BUTTON_WIDTH = 50
BUTTON_WIDTH = 150
BUTTON_HEIGHT = 50
TABLE_SIZE = 12
BUTTON_BORDER_RADIUS = 5
QUIT_BUTTON_STYLE = "grey"
START_BUTTON_STYLE = "green"
STOP_BUTTON_STYLE = "red"
NUM_MESSAGES = 200

### GLOBAL VARIABLES ###
charge_voltage = 0
charge_current = 0
discharge_balance = 0
discharge_threshold = 0
discharge_balance_value = 0


class HeatmapGUI(QMainWindow):
    """Top level code for BMS VIEWER"""

    ####### PURE PyQT VISUALIZATION ELEMENTS / STRUCTURING APPEARANCE OF GUI #######

    def __init__(self, can_bus):
        ### INITIALIZES MAIN WINDOW + CHARGE STATE + NECESSARY CLASS INITIALIZATION ###
        super().__init__()
        self.setWindowTitle("BMS Viewer")
        self.threadpool = QThreadPool()
        self.bottomLayout = QHBoxLayout()
        self.is_charging = False
        self.charge_worker = None
        self.poll_worker = Worker(self.poll_thread_function)
        self.threadpool.start(self.poll_worker)
        self.parser = CANMessageParser(filtering=BMSFILTERS, can_bus=can_bus)
        self.data_retriever = BMSData()

        ### INTIALIZE UI ###
        widget = QWidget(self)
        widget.setLayout(self.bottomLayout)
        self.create_buttons()
        self.create_inputs()
        self.set_layout()

        ### INITIALIZE HEATMAPS AND SIDE TABLES ###
        self.voltage_heatmap = Heatmap(MIN_SAFE_VOLTAGE, MAX_SAFE_VOLTAGE, "Voltage")
        self.temperature_heatmap = Heatmap(
            MIN_SAFE_TEMPERATURE, MAX_SAFE_TEMPERATURE, "Temperature"
        )
        self.combined_voltage_temperature_table = self.create_table(
            [
                (
                    "System Voltage",
                    [
                        "Max Voltage",
                        "Min Voltage",
                        "Voltage Delta",
                        "Max Voltage Cell",
                        "Min Voltage Cell",
                        "Charger Voltage",
                        "Charger Current",
                    ],
                ),
                (
                    "System Temperature",
                    [
                        "Max Temperature",
                        "Min Temperature",
                        "Temperature Delta",
                        "Max Temperature Cell",
                        "Min Temperature Cell",
                    ],
                ),
            ]
        )
        self.combined_faults_pack_data_table = self.create_table(
            [
                (
                    "Faults",
                    [
                        "Over Voltage",
                        "Under Voltage",
                        "Over Temp",
                        "Under Temp",
                        "Hardware Malfunction",
                        "Charger Temperature",
                        "Input Voltage Error",
                        "Battery Connection Error",
                        "Communication Timeout",
                    ],
                ),
                ("Pack Data", ["Pack Voltage", "Pack Current", "Pack Power"]),
            ]
        )

        ### SET UP MAIN LAYOUT ###
        gridLayout = QGridLayout()
        gridLayout.addWidget(self.voltage_heatmap, 0, 0, 1, 3)
        gridLayout.addWidget(self.temperature_heatmap, 1, 0, 1, 3)
        gridLayout.addWidget(self.combined_voltage_temperature_table, 0, 3, 1, 2)
        gridLayout.addWidget(self.combined_faults_pack_data_table, 1, 3, 1, 2)
        gridLayout.addWidget(widget, 2, 0, 1, 5)
        gridLayout.setColumnStretch(0, 2)
        gridLayout.setColumnStretch(1, 2)
        gridLayout.setColumnStretch(2, 2)
        gridLayout.setColumnStretch(3, 2)
        gridLayout.setColumnStretch(4, 2)
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        central_widget.setLayout(gridLayout)

        ### START WORKERS AND MAXIMIZE WINDOW ###
        QTimer.singleShot(0, self.start_workers)
        self.showMaximized()

    def create_buttons(self):
        """
        Make the main buttons (Quit, Start, Stop).
        Sets how they look and what they do when clicked.
        """
        self.quitButton = QPushButton("Quit")
        self.quitButton.setStyleSheet(
            f"background-color: {QUIT_BUTTON_STYLE}; border-radius: {BUTTON_BORDER_RADIUS}px;"
        )
        self.quitButton.setFixedSize(QUIT_BUTTON_WIDTH, BUTTON_HEIGHT)
        self.quitButton.clicked.connect(self.quit_button_clicked)

        self.startButton = QPushButton("Start")
        self.startButton.setStyleSheet(
            f"background-color: {START_BUTTON_STYLE}; border-radius: {BUTTON_BORDER_RADIUS}px;"
        )
        self.startButton.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        self.startButton.clicked.connect(self.start_button_clicked)

        self.stopButton = QPushButton("Stop")
        self.stopButton.setStyleSheet(
            f"background-color: {STOP_BUTTON_STYLE}; border-radius: {BUTTON_BORDER_RADIUS}px;"
        )
        self.stopButton.setFixedSize(BUTTON_WIDTH, BUTTON_HEIGHT)
        self.stopButton.clicked.connect(self.stop_button_clicked)

    def create_inputs(self):
        """
        Make input boxes for voltage, current, discharge balance, and threshold.
        Adds text boxes, checkboxes, and dropdown menus.
        """
        self.textbox1 = QLineEdit(self)
        self.textbox2 = QLineEdit(self)
        self.balance_enable_checkbox = QCheckBox(self)
        self.balance_cell_cnt_dropdown = QComboBox(self)
        self.textbox4 = QLineEdit(self)

        self.textbox1.setPlaceholderText("Enter voltage")
        self.textbox2.setPlaceholderText("Enter current")
        self.textbox4.setPlaceholderText("Enter discharge threshold")

        self.balance_cell_cnt_dropdown.addItems(["1", "2", "3", "4", "6", "12"])
        self.balance_cell_cnt_dropdown.setFixedSize(80, 30)

        self.textbox1.textChanged.connect(
            lambda: self.update_charge_voltage(self.textbox1, 1)
        )
        self.textbox2.textChanged.connect(
            lambda: self.update_charge_current(self.textbox2, 2)
        )
        self.balance_enable_checkbox.stateChanged.connect(
            self.update_discharge_balance
        )
        self.balance_cell_cnt_dropdown.currentTextChanged.connect(
            self.update_discharge_balance_value
        )
        self.textbox4.textChanged.connect(
            lambda: self.update_discharge_voltage_limit(self.textbox4, 4)
        )

        self.style_inputs()

    def style_inputs(self):
        """
        Make the input boxes look nice.
        Sets colors, borders, and other visual details.
        """
        style = """
        QLineEdit, QComboBox {
            background-color: #f0f0f0;
            border: 2px solid #c0c0c0;
            border-radius: 5px;
            padding: 5px;
            font-size: 14px;
        }
        QLineEdit:focus, QComboBox:focus {
            border-color: #a0a0a0;
        }
        """
        for widget in [
            self.textbox1,
            self.textbox2,
            self.textbox4,
            self.balance_cell_cnt_dropdown,
        ]:
            widget.setStyleSheet(style)
            if isinstance(widget, QLineEdit):
                widget.setFixedSize(150, 30)

    def set_layout(self):
        """
        Arrange all UI elements in the bottom layout of the main window.
        Organizes labels, input fields, and buttons horizontally with proper spacing.
        """
        voltage_label = QLabel("Voltage:")
        current_label = QLabel("Current:")
        balance_enable_label = QLabel("Enable Balancing:")
        balance_cell_cnt_label = QLabel("Max. Cells/Segment:")
        discharge_threshold_label = QLabel("Discharge Threshold:")

        for label in [
            voltage_label,
            current_label,
            balance_enable_label,
            balance_cell_cnt_label,
            discharge_threshold_label,
        ]:
            label.setStyleSheet("font-weight: bold; font-size: 14px;")

        list_widgets = (self.quitButton, voltage_label, self.textbox1, current_label, 
                        self.textbox2, balance_enable_label, self.balance_enable_checkbox, balance_cell_cnt_label,
                        self.balance_cell_cnt_dropdown, discharge_threshold_label, self.textbox4, self.startButton,
                        self.stopButton)
        
        for wid in list_widgets:
            self.bottomLayout.addWidget(wid)

        self.bottomLayout.setSpacing(10)
        self.bottomLayout.setContentsMargins(10, 10, 10, 10)

    def create_table(self, sections):
        """
        Construct a table widget with several sections to display various BMS data values.
        """
        total_rows = sum(len(row_labels) for _, row_labels in sections) + len(sections)
        table = QTableWidget(total_rows, 2)
        table.setHorizontalHeaderLabels(["Parameter", "Value"])

        row_index = 0
        for title, row_labels in sections:
            title_item = QTableWidgetItem(title)
            title_item.setFont(QFont("Arial", 11, QFont.Bold))
            title_item.setBackground(QColor(80, 80, 80))
            title_item.setForeground(QColor(255, 255, 255))
            table.setItem(row_index, 0, title_item)
            table.setItem(row_index, 1, QTableWidgetItem(""))
            table.item(row_index, 1).setBackground(QColor(80, 80, 80))
            row_index += 1

            for label in row_labels:
                item = QTableWidgetItem(label)
                item.setFont(QFont("Arial", 10))
                table.setItem(row_index, 0, item)
                table.setItem(row_index, 1, QTableWidgetItem("N/A"))
                row_index += 1

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setFont(QFont("Arial", 12, QFont.Bold))
        table.verticalHeader().setVisible(False)
        self.set_table_style(table)
        return table

    def set_table_style(self, table):
        """
        Apply custom styling to the table widgit.
        """
        table.setStyleSheet(
            """
            QTableWidget {
                font-family: Arial, sans-serif;
                font-size: 10pt;  /* Increased font size */
                border: 2px solid #444444;
            }
            QTableWidget::item {
                padding: 3px;  /* Increased padding */
            }
            QHeaderView::section {
                background-color: black;
                color: white;
                padding: 5px;  /* Increased padding */
                border: 1px solid #666666;
                font-weight: bold;
            }
            QTableWidget::item:selected {
                background-color: #666666;
            }
            QTableWidget::item[title="true"] {
                background-color: #505050;
                color: white;
                font-weight: bold;
            }
        """
        )

        header_font = QFont("Arial", 12, QFont.Bold)
        table.horizontalHeader().setFont(header_font)

        cell_font = QFont("Arial", 10)
        table.setFont(cell_font)

        for row in range(table.rowCount()):
            if table.item(row, 0) and table.item(row, 0).background().color() == QColor(
                80, 80, 80
            ):
                table.item(row, 0).setData(Qt.UserRole, "true")
                table.item(row, 1).setData(Qt.UserRole, "true")

    ####### WORKERS + CONNECTED FUNCTIONS/JOBS #######

    def start_workers(self):
        """
        Start all background tasks.
        These tasks handle data processing and updating the display.
        """
        self.can_worker = TimedWorker(self.process_can_messages)
        self.threadpool.start(self.can_worker)

        self.voltage_worker = TimedWorker(self.refresh_voltage_data)
        self.voltage_worker.signals.result.connect(self.voltage_heatmap.plot)
        self.threadpool.start(self.voltage_worker)

        self.temperature_worker = TimedWorker(self.refresh_temperature_data)
        self.temperature_worker.signals.result.connect(self.temperature_heatmap.plot)
        self.threadpool.start(self.temperature_worker)

        self.system_voltage_worker = TimedWorker(self.refresh_system_voltage_data)
        self.system_voltage_worker.signals.result.connect(
            self.update_system_voltage_table
        )
        self.threadpool.start(self.system_voltage_worker)

        self.system_temperature_worker = TimedWorker(
            self.refresh_system_temperature_data
        )
        self.system_temperature_worker.signals.result.connect(
            self.update_system_temperature_table
        )
        self.threadpool.start(self.system_temperature_worker)

        self.fault_worker = TimedWorker(self.refresh_fault_data)
        self.fault_worker.signals.result.connect(self.update_fault_table)
        self.threadpool.start(self.fault_worker)

        self.pack_worker = TimedWorker(self.refresh_pack_data)
        self.pack_worker.signals.result.connect(self.update_pack_data_table)
        self.threadpool.start(self.pack_worker)

        self.charger_out_worker = TimedWorker(self.refresh_charger_out_data)
        self.charger_out_worker.signals.result.connect(self.update_charger_out_table)
        self.threadpool.start(self.charger_out_worker)

    def process_can_messages(self):
        """
        Deal with incoming messages from the BMS.
        Gets messages and updates stored data.
        """
        messages = self.parser.get_messages(NUM_MESSAGES)
        self.data_retriever.process_bms_messages(messages)
        self.parser.empty_queue()

    def refresh_voltage_data(self):
        """
        Get the latest voltage readings for all cells.
        Returns a grid of voltage values to show on the heatmap.
        """
        cell_values = self.data_retriever.get_bms_cell_vals()
        voltage_data = np.array(
            [cell.values["cell_voltage"] if cell else None for cell in cell_values]
        )
        # if None not in voltage_data:
        #     avg_voltage = np.sum(voltage_data) / 144
        #     self.update_table_value(self.combined_voltage_temperature_table, "Average Voltage", f"{avg_voltage:.3f}V")
        voltage_data = voltage_data.reshape(TABLE_SIZE, TABLE_SIZE)
        return voltage_data

    def refresh_temperature_data(self):
        """
        Get the latest temperature readings for all cells.
        Returns a grid of temperature values to show on the heatmap.
        """
        cell_values = self.data_retriever.get_bms_cell_vals()
        temp_data = np.array(
            [cell.values["cell_temperature"] if cell else None for cell in cell_values]
        )
        # if None not in temp_data:
        #     avg_temp = np.sum(temp_data) / 144
        #     self.update_table_value(self.combined_voltage_temperature_table, "Avg Temperature", f"{avg_temp:.1f}°C")
        temp_data = temp_data.reshape(TABLE_SIZE, TABLE_SIZE)
        return temp_data

    def refresh_system_voltage_data(self):
        """
        Get the latest overall voltage info.
        """
        voltage_info = self.data_retriever.get_bms_system_voltage()
        if voltage_info:
            max_voltage = voltage_info.values["max_voltage"]
            min_voltage = voltage_info.values["min_voltage"]
            avg_voltage = voltage_info.values["avg_voltage"]
            max_voltage_cell = voltage_info.values["max_voltage_cell"]
            min_voltage_cell = voltage_info.values["min_voltage_cell"]
        else:
            max_voltage = None
            min_voltage = None
            avg_voltage = None
            max_voltage_cell = None
            min_voltage_cell = None
        return max_voltage, min_voltage, avg_voltage, max_voltage_cell, min_voltage_cell

    def refresh_system_temperature_data(self):
        """
        Get the latest overall temperature info.
        """
        temp_info = self.data_retriever.get_bms_system_temp()
        if temp_info:
            max_temp = temp_info.values["max_temp"]
            min_temp = temp_info.values["min_temp"]
            avg_temp = temp_info.values["avg_temp"]
            max_temp_cell = temp_info.values["max_temp_cell"]
            min_temp_cell = temp_info.values["min_temp_cell"]
        else:
            max_temp = None
            min_temp = None
            avg_temp = None
            max_temp_cell = None
            min_temp_cell = None
        return max_temp, min_temp, avg_temp, max_temp_cell, min_temp_cell

    def refresh_fault_data(self):
        """
        Get the latest error report from the BMS.
        """
        fault_info = self.data_retriever.get_bms_processed_faults()
        if fault_info:
            faults = fault_info.values["faults"]
        else:
            faults = {}
        return faults

    def refresh_pack_data(self):
        """
        Get the latest overall battery pack info.
        """
        pack_info = self.data_retriever.get_bms_pack_status()
        if pack_info.values:
            pack_voltage = pack_info.values["pack_voltage"]
            pack_current = pack_info.values["pack_current"]
            pack_power = pack_info.values["pack_power"]
        else:
            pack_voltage = None
            pack_current = None
            pack_power = None
        return pack_voltage, pack_current, pack_power

    def refresh_charger_out_data(self):
        """
        Get the latest charger output information.
        """
        charger_out_info = self.data_retriever.get_bms_charger_out()
        if charger_out_info.values:
            charger_voltage = charger_out_info.values["charger_voltage"]
            charger_current = charger_out_info.values["charger_current"]
            status_errors = charger_out_info.values["status_errors"]
        else:
            charger_voltage = None
            charger_current = None
            status_errors = []
        return charger_voltage, charger_current, status_errors

    def update_table_value(self, table, row_name, value):
        """
        Modify a specific value in the given table.
        """
        for row in range(table.rowCount()):
            if table.item(row, 0) and table.item(row, 0).text() == row_name:
                table.item(row, 1).setText(str(value))
                break

    ####### FUNCTIONS FOR UPDATING DATA IN REAL TIME #######

    def update_system_voltage_table(self, data):
        """
        Refresh the system voltage section of the combined table with new data.
        """
        max_voltage, min_voltage, avg_voltage, max_voltage_cell, min_voltage_cell = data
        
        volt_delta = max_voltage - min_voltage if min_voltage is not None and max_voltage is not None else 0
        self.update_table_value(
            self.combined_voltage_temperature_table,
            "Max Voltage",
            f"{max_voltage:.3f}V" if max_voltage is not None else "None",
        )
        self.update_table_value(
            self.combined_voltage_temperature_table,
            "Min Voltage",
            f"{min_voltage:.3f}V" if min_voltage is not None else "None",
        )
        self.update_table_value(
            self.combined_voltage_temperature_table,
            "Voltage Delta",
            f"{volt_delta:.3f}V",
        )
        self.update_table_value(
            self.combined_voltage_temperature_table,
            "Max Voltage Cell",
            str(max_voltage_cell) if max_voltage_cell is not None else "None",
        )
        self.update_table_value(
            self.combined_voltage_temperature_table,
            "Min Voltage Cell",
            str(min_voltage_cell) if min_voltage_cell is not None else "None",
        )

    def update_system_temperature_table(self, data):
        """
        Refresh the system temperature section of the combined table with new data.
        """
        max_temp, min_temp, avg_temp, max_temp_cell, min_temp_cell = data
        temp_delta = max_temp - min_temp if max_temp is not None and min_temp is not None else 0
        self.update_table_value(
            self.combined_voltage_temperature_table,
            "Max Temperature",
            f"{max_temp:.1f}°C" if max_temp is not None else "None",
        )
        self.update_table_value(
            self.combined_voltage_temperature_table,
            "Min Temperature",
            f"{min_temp:.1f}°C" if min_temp is not None else "None",
        )
        self.update_table_value(
            self.combined_voltage_temperature_table,
            "Temperature Delta",
            f"{temp_delta:.3f}V",
        )
        self.update_table_value(
            self.combined_voltage_temperature_table,
            "Max Temperature Cell",
            str(max_temp_cell) if max_temp_cell is not None else "None",
        )
        self.update_table_value(
            self.combined_voltage_temperature_table,
            "Min Temperature Cell",
            str(min_temp_cell) if min_temp_cell is not None else "None",
        )

    def update_charger_out_table(self, data):
        """
        Refresh the charger output section of the table and update fault status.
        """
        charger_voltage, charger_current, status_errors = data

        self.update_table_value(
            self.combined_voltage_temperature_table,
            "Charger Voltage",
            f"{charger_voltage:.3f}V" if charger_voltage is not None else "BIG CHILLIN",
        )
        self.update_table_value(
            self.combined_voltage_temperature_table,
            "Charger Current",
            f"{charger_current:.3f}A" if charger_current is not None else "BIG CHILLIN",
        )

        error_names = [
            "Hardware Malfunction",
            "Charger Temperature",
            "Input Voltage Error",
            "Battery Connection Error",
            "Communication Timeout",
        ]

        for error_name in error_names:
            if error_name in status_errors:
                self.update_table_value(
                    self.combined_faults_pack_data_table, error_name, "Fault Detected"
                )
            else:
                self.update_table_value(
                    self.combined_faults_pack_data_table, error_name, "BIG CHILLIN"
                )

    def update_fault_table(self, faults):
        """
        Refresh the fault section of the table with current fault status.
        """
        fault_names = ["Over Voltage", "Under Voltage", "Over Temp", "Under Temp"]
        for fault_name in fault_names:
            if fault_name in faults.keys():
                self.update_table_value(
                    self.combined_faults_pack_data_table,
                    fault_name,
                    f"Fault Detected ({faults[fault_name]})",
                )
            else:
                self.update_table_value(
                    self.combined_faults_pack_data_table, fault_name, "BIG CHILLIN"
                )

    def update_pack_data_table(self, data):
        """
        Refresh the pack data section of the table with new values.
        """
        pack_voltage, pack_current, pack_power = data
        self.update_table_value(
            self.combined_faults_pack_data_table,
            "Pack Voltage",
            f"{pack_voltage:.3f}V" if pack_voltage is not None else "None",
        )
        self.update_table_value(
            self.combined_faults_pack_data_table,
            "Pack Current",
            f"{pack_current:.3f}A" if pack_current is not None else "None",
        )
        self.update_table_value(
            self.combined_faults_pack_data_table,
            "Pack Power",
            f"{pack_power:.3f}W" if pack_power is not None else "None",
        )

    def update_charge_voltage(self, textbox, box_number):
        """
        Modify the global charge voltage based on user input.
        """
        global charge_voltage
        value = textbox.text()
        try:
            temp_charge_voltage = float(value)
            charge_voltage = temp_charge_voltage if temp_charge_voltage < 600 else 0
        except:
            charge_voltage = float(0)
        print(f"Updated global_value{box_number}: {value}")

    def update_charge_current(self, textbox, box_number):
        """
        Modify the global charge current based on user input.
        """
        global charge_current
        value = textbox.text()
        try:
            temp_charge_current = float(value)
            charge_current = temp_charge_current if temp_charge_current < 10 else 0
        except:
            charge_current = float(0)
        print(f"Updated global_value{box_number}: {value}")

    def update_discharge_balance(self, state):
        """
        Modify the global discharge balance flag based on checkbox state.
        """
        global discharge_balance
        discharge_balance = 0xff if state == Qt.Checked else 0
        print(f"Updated discharge_balance: {discharge_balance}")

    def update_discharge_balance_value(self):
        """
        Modify the global discharge balance value based on checkbox and dropdown selection.
        """
        global discharge_balance_value
        global discharge_balance
        if discharge_balance:
            balance_value = int(self.balance_cell_cnt_dropdown.currentText())
            discharge_balance_value = 0xF0 | balance_value
        else:
            discharge_balance_value = 0x00
        print(f"Updated discharge_balance_value: {discharge_balance_value:#04x}")

    def update_discharge_voltage_limit(self, textbox, box_number):
        """
        Modify the global discharge threshold based on user input.
        """
        global discharge_threshold
        value = textbox.text()
        try:
            discharge_threshold = float(value)
        except:
            discharge_threshold = float(0)
        print(f"Updated global_value{box_number}: {value}")

    ####### FUNCTION FOR CHARGING FUNCTINOALITY #######

    def charge_thread_function(self):
        """
        Continuously transmits charge commands while charging is active.
        """
        while self.is_charging:
            message_to_send = encode_manual_charge(
                {
                    "charge_enable": 0xFF if discharge_balance == 0 else 0x00,
                    "voltage": charge_voltage,
                    "current": charge_current,
                    "discharge_balance": discharge_balance_value,
                    "discharge_threshold": discharge_threshold,
                }
            )
            self.parser.send_can_messages(message_to_send, is_extended_id=False)
            time.sleep(1)

    def poll_thread_function(self):
        """
        Continuously transmits polling messages while BMS viewer is connected
        """
        while True:
            message_to_send = encode_polling()
            self.parser.send_can_messages(message_to_send, is_extended_id=False)
            time.sleep(1)

    def start_button_clicked(self):
        """
        Event handler for the Start button click.
        Starts charging process and updates button states.
        """
        self.update_discharge_balance_value()
        if not self.is_charging:
            self.is_charging = True
            self.charge_worker = Worker(self.charge_thread_function)
            self.threadpool.start(self.charge_worker)
            self.startButton.setEnabled(False)
            self.stopButton.setEnabled(True)

    def stop_button_clicked(self):
        """
        Event handler for the Stop button click.
        Halts charging process and updates button states.
        """
        if self.is_charging:
            self.is_charging = False
            if self.charge_worker:
                self.charge_worker.stop()
            self.startButton.setEnabled(True)
            self.stopButton.setEnabled(False)

    ####### APPLICATION CLEANUP LOGIC ######

    def quit_thread_function(self):
        """
        Cleanup function when exiting the application.
        Halts all worker threads and deactivates charging.
        """
        if self.can_worker:
            self.can_worker.stop()
        if self.voltage_worker:
            self.voltage_worker.stop()
        if self.temperature_worker:
            self.temperature_worker.stop()
        if self.system_voltage_worker:
            self.system_voltage_worker.stop()
        if self.system_temperature_worker:
            self.system_temperature_worker.stop()
        if self.fault_worker:
            self.fault_worker.stop()
        if self.pack_worker:
            self.pack_worker.stop()
        if self.charger_out_worker:
            self.charger_out_worker.stop()
        if self.is_charging:
            self.is_charging = False
        if self.charge_worker:
            self.charge_worker.stop()
        print("Quit button clicked")
        QApplication.quit()

    def quit_button_clicked(self):
        """
        Event handler for the Quit button click.
        Terminates application.
        """
        worker = Worker(self.quit_thread_function)
        self.threadpool.start(worker)

    def closeEvent(self, event):
        """Handle the window close event."""
        self.quit_thread_function()
        self.threadpool.waitForDone()
        self.parser.stop()
        event.accept()

    def __del__(self):
        sys.exit(0)\
            
