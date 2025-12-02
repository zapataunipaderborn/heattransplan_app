from Pinch_main import Pinchmain
from Modules.HeatPumpIntegration.HeatPumpIntegration import HeatPumpIntegration as HPI
import matplotlib.pyplot as plt

class HPImain():
    def __init__(self, streamsDataFile, TS = None):
        self.pyPinchHPI = Pinchmain(streamsDataFile, options= {})
        self.HPI = HPI(streamsDataFile, TS, self.pyPinchHPI)
    def showHPI(self):
        self.HPI.HPI()
        plt.show()
HPImain('Example.csv').showHPI()