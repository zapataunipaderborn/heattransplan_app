import csv
from Modules.TotalSiteProfile.TotalSiteProfile import TotalSiteProfile as TSP
from Modules.TotalSiteProfile.TSPPlot import TSPPlot as TSPPlot

class TotalSiteProfilemain():
    def __init__(self, siteDesignation, CSVList, options = {}):
        self.CSVList = CSVList
        
        self.TotalSite = TSP(siteDesignation, options)
        
    def solveTotalSiteProfile(self, localisation = 'DE', internalHeatTransfer = True):
        for siteProfilecsv in self.CSVList:
            self.TotalSite.importData(siteProfilecsv)
            if internalHeatTransfer == True:
                self.TotalSite.deleteTemperaturePockets()
            else:
                self.TotalSite.noDeletionHelper()
            self.TotalSite.splitHotandCold()
        self.TotalSite.constructTotalSiteProfile(localisation)

        if self.TotalSite._options['draw'] == True:
            TSPPlot().showPlots()

    def testsolve(self):

        for siteProfilecsv in self.CSVList:
            self.TotalSite.importData(siteProfilecsv)
            self.TotalSite.deleteTemperaturePockets()

        if self.TotalSite._options['draw'] == True:
            TSPPlot().showPlots()


TotalSiteProfilemain('Test', ['Example.csv', 'Example.csv'], options={'draw', 'csv'}).solveTotalSiteProfile(internalHeatTransfer = False)