### IMPORTS ###
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

### CONSTANTS ###
RED_COLOR = QColor(255, 0, 0)
BLUE_COLOR = QColor(0, 0, 255)
GRAY_COLOR = QColor(30, 31, 30)
BORDER_SELECTED_COLOR = Qt.black
BORDER_UNSELECTED_COLOR = Qt.gray
BORDER_SELECTED_WIDTH = 2
BORDER_UNSELECTED_WIDTH = 1
BORDER_STYLE = Qt.SolidLine
BORDER_ADJUSTMENT_LEFT = 1
BORDER_ADJUSTMENT_TOP = 1
BORDER_ADJUSTMENT_RIGHT = -1
BORDER_ADJUSTMENT_BOTTOM = -1
TABLE_SIZE = 12


class TableBorder(QStyledItemDelegate):
    """
    Literally just adds a border around each cell in the heatmap,
    why this is so complex in PyQT I have no idea.
    Also highlights a cell if it's selected.
    """

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):
        super().paint(painter, option, index)

        if option.state & QStyle.State_Selected:
            painter.setPen(
                QPen(BORDER_SELECTED_COLOR, BORDER_SELECTED_WIDTH, BORDER_STYLE)
            )
        else:
            painter.setPen(
                QPen(BORDER_UNSELECTED_COLOR, BORDER_UNSELECTED_WIDTH, BORDER_STYLE)
            )

        rect = option.rect.adjusted(
            BORDER_ADJUSTMENT_LEFT,
            BORDER_ADJUSTMENT_TOP,
            BORDER_ADJUSTMENT_RIGHT,
            BORDER_ADJUSTMENT_BOTTOM,
        )
        painter.drawRect(rect)


class Heatmap(QWidget):
    """A widget for displaying a heatmap
    Attributes:
        max_safe_value (float): The maximum safe value for the heatmap
        min_safe_value (float): The minimum safe value for the heatmap
        title (str): The title of the heatmap
    """

    def __init__(self, min_safe, max_safe, title):
        super().__init__()
        self.max_safe_value = max_safe
        self.min_safe_value = min_safe

        self.title = title
        self.table_title = QLabel(self.title + " Heatmap")
        self.table_title.setStyleSheet("font-size: 13px; font-weight: bold;")
        self.table_title.setAlignment(Qt.AlignCenter)
        self.table = QTableWidget(TABLE_SIZE, TABLE_SIZE)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)

        border = TableBorder(self.table)
        self.table.setItemDelegate(border)
        layout = QVBoxLayout()
        layout.addWidget(self.table_title)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def plot(self, heatmapData):
        """Update the table with new heatmap data."""
        for i in range(TABLE_SIZE):
            for j in range(TABLE_SIZE):
                value = heatmapData[i][j]

                if value is None:
                    item = QTableWidgetItem("N/A")
                    item.setBackground(GRAY_COLOR)
                else:
                    item = QTableWidgetItem(f"{value:.3f}")
                    if value > self.max_safe_value:
                        item.setBackground(RED_COLOR)
                    elif value < self.min_safe_value:
                        item.setBackground(BLUE_COLOR)

                self.table.setItem(i, j, item)
