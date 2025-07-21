### IMPORTS ###
import sys
import time

from PyQt5.QtCore import *


class WorkerSignals(QObject):
    """Establish communication channels"""

    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)


class Worker(QRunnable):
    def __init__(self, function):
        super(Worker, self).__init__()
        self.function = function
        self.is_running = True

    @pyqtSlot()
    def run(self):
        """Keep executing assigned job while active"""
        while self.is_running:
            self.function()

    def stop(self):
        """Instruct the worker to stop"""
        self.is_running = False


class TimedWorker(QRunnable):

    def __init__(self, fn, *args, **kwargs):
        super(TimedWorker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.is_running = True

    @pyqtSlot()
    def run(self):
        """Run repeatedly every second."""
        try:
            while self.is_running:
                result = self.fn(*self.args, **self.kwargs)
                self.signals.result.emit(result)
                time.sleep(0.5)

        except Exception as e:
            exctype, value, tb = sys.exc_info()
            self.signals.error.emit((exctype, value, tb))
        finally:
            self.signals.finished.emit()

    def stop(self):
        """Stop the worker loop."""
        self.is_running = False
