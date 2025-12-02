import csv
from Modules.Pinch.Pinch import Pinch
from Modules.Pinch.PinchPlot import PinchPlot

class Pinchmain():
    def __init__(self, CSV, options = {}):
        self.PinchAnalyse = Pinch(CSV, options)
        self._options = {}
       
    def solvePinch(self, localisation = 'DE'):

        self.PinchAnalyse.shiftTemperatures()
        self.PinchAnalyse.constructTemperatureInterval()
        self.PinchAnalyse.constructProblemTable()
        self.PinchAnalyse.constructHeatCascade()
        self.PinchAnalyse.constructShiftedCompositeDiagram(localisation)
        self.PinchAnalyse.constructCompositeDiagram(localisation)
        self.PinchAnalyse.constructGrandCompositeCurve(localisation)

        with open("Buffer file for TotalSiteProfile creation.csv", "w", newline="") as csvfile:
            self.newstreamsdata = csv.writer(csvfile)
            self.newstreamsdata.writerow(self.PinchAnalyse._temperatures)
            self.newstreamsdata.writerow(self.PinchAnalyse.heatCascade)
            self.newstreamsdata.writerow([self.PinchAnalyse.hotUtility])


        if self.PinchAnalyse._options['draw'] == True:
            PinchPlot.showPlots()  

    def solvePinchforISSP(self, localisation = 'DE'):

        self.PinchAnalyse.shiftTemperatures()
        self.PinchAnalyse.constructTemperatureInterval()
        self.PinchAnalyse.constructProblemTable()
        self.PinchAnalyse.constructHeatCascade()
        self.PinchAnalyse.constructShiftedCompositeDiagram(localisation)

        return[self.PinchAnalyse.shiftedCompositeDiagram, self.PinchAnalyse]
    
    def solvePinchforHPI(self, localisation = 'DE'):

        self.PinchAnalyse.shiftTemperatures()
        self.PinchAnalyse.constructTemperatureInterval()
        self.PinchAnalyse.constructProblemTable()
        self.PinchAnalyse.constructHeatCascade()
        self.PinchAnalyse.constructShiftedCompositeDiagram(localisation)
        self.PinchAnalyse.constructCompositeDiagram(localisation)
        self.PinchAnalyse.constructGrandCompositeCurve(localisation)

        return(self.PinchAnalyse)

#Pinchmain('Example.csv', options={'draw', 'csv'}).solvePinch()
#Pinchmain('Prozess_neu.csv', options={'draw', 'csv'}).solvePinch()