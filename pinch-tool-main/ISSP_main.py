from Pinch_main import Pinchmain
from Modules.ISSP.ISSP import ISSP
from Modules.HeatPumpIntegration.HeatPumpIntegration import HeatPumpIntegration as HPI
import matplotlib.pyplot as plt

class ISSPmain():
    def __init__(self, streamsDataFile, TS, TProcess, batchtimeSeconds, fromPinch = False, intermediateCircuit = {}):
        self.pyPinchISSP = Pinchmain(streamsDataFile, options= {})
        self.pyPinchHPI = Pinchmain(streamsDataFile, options= {})
        self.HPI = HPI(streamsDataFile, TS, self.pyPinchHPI)
        self.fromPinch = bool(fromPinch)
        self.intermediateCircuit = bool(intermediateCircuit)
        self.ISSP = ISSP(streamsDataFile, TS, TProcess, batchtimeSeconds, self.pyPinchISSP, self.HPI, self.fromPinch, self.intermediateCircuit)

    def solveISSP(self):
        self.ISSP.CCinkWh()
        self.ISSP.drawISSPHotIntermediate()
        self.ISSP.drawISSPColdIntermediate()
        #self.HPI.drawGrandCompositeCurve()
        plt.show()
#ISSPmain('Prozess_neu.csv', 200, 170, batchtimeSeconds= 9240, fromPinch=False).solveISSP()
ISSPmain('Example.csv', 143, 113, batchtimeSeconds= 1000, fromPinch=False).solveISSP()