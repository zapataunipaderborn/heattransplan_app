from Pinch_main import Pinchmain as Pinch
import csv
import ast
from Modules.TotalSiteProfile.TSPPlot import TSPPlot
from Modules.Utility.TemperaturePocketDeletion import TemperaturePocketDeletion as TPD
from Modules.Utility.splitStreams import splitStreams

class TotalSiteProfile:

    def __init__(self, siteDesignation, options = {}):
    
        self.siteDesignation = siteDesignation

        self.heatCascadedeltaH = []
        self.heatCascadeexitH = []

        self.deletedPocketdict = []
        self.heatCascadedeltaHdict = []
        self.heatCascadeexitHdict = []
        self.deletedPocketdictlist = []
        
        self.splitHotTemperatures = []
        self.splitColdTemperatures = []
        self.splitHotH = []
        self.splitColdH = []
        self.splitHotdeltaH = []
        self.splitColddeltaH = []
        self.splitdict = {'HotTemperatures': [], 'ColdTemperatures': [], 'HotH': [], 'ColdH': [], 'HotdeltaH': [], 'ColddeltaH': [], 'SteigungHot': [], 'SteigungCold': []}

        self.tstHotConstructionAid = {'T': [], 'Process': [], 'Stream': []}
        self.tstColdConstructionAid = {'T': [], 'Process': [], 'Stream': []}

        self.tstHotTemperatures = []
        self.tstColdTemperatures = []
        self.tstHotH = []
        self.tstColdH = []

        self.emptyintervalsHot = []
        self.emptyintervalsCold = []

        self._options = {'debug': False, 'draw': False, 'csv': False}

        if 'debug' in options:
            self._options['debug'] = True
        if 'draw' in options:
            self._options['draw'] = True
        if 'csv' in options:
            self._options['csv'] = True


    def importData(self, siteProfilecsv):
        nooption = {}
        Pinch('{}'.format(siteProfilecsv),nooption).solvePinch()
        with open('Buffer file for TotalSiteProfile creation.csv', newline='') as f:
            reader = csv.reader(f)
            csvdata=[]
            for row in reader:
                csvdata.append(row)
        self._temperatures = csvdata[0]
        self.heatCascade = csvdata[1]
        for i in range(len(self.heatCascade)):
            self.heatCascade[i] = ast.literal_eval(self.heatCascade[i])
        self.hotUtility = float(csvdata[2][0])
        for i in range(len(self._temperatures)):
            self._temperatures[i] = float(self._temperatures[i])

    def deleteTemperaturePockets(self):
        self.deletedPocketdict = TPD(self.hotUtility, self.heatCascade, self._temperatures).deleteTemperaturePockets()
        

    def noDeletionHelper(self):
        self.deletedPocketdict = {'H': [], 'deltaH': [], 'T': []}
        self.heatCascadedeltaH = []
        self.heatCascadeexitH = []
        self.heatCascadeexitH.append(self.hotUtility)
        
        for o in range(len(self.heatCascade)):
            self.heatCascadedeltaH.append(self.heatCascade[o]['deltaH'])
            self.heatCascadeexitH.append(self.heatCascade[o]['exitH'])

        self.deletedPocketdict['H'].append(self.heatCascadeexitH)
        self.deletedPocketdict['deltaH'].append(self.heatCascadedeltaH)
        self.deletedPocketdict['T'].append(self._temperatures)
        self.deletedPocketdictlist.append(self.deletedPocketdict)

    def splitHotandCold(self): # Fall für 2 aufeinander folgende heiße Ströme ohne deletion implementieren
        self.splitdict = splitStreams(self.deletedPocketdict, self.splitdict).splitHotandCold()

    def constructTotalSiteProfile(self, localisation): #Temperaturen sind in jedem Prozess bereits einzigartig für Heiß/Kalt
       #Mit ColddeltaH und Temperaturen jeweils Steigungen für alle Schritte in Reihenfolge ermitteln
       #Dann abfragen, welche Steigung im aktuellen Temperaturintervall benötigt wird(einfach der Reihe nach oder wenn T kleiner als die aktuelle Temperatur aber größer als die vorherige)
       #Anschließend jeweils die Steigungen addieren und mal dem aktuellen Temperaturintervall rechnen und mit dem vorherigen Wert addiert anfügen
       
       
        for i in range(len(self.splitdict['HotTemperatures'])):
            for j in range(len(self.splitdict['HotTemperatures'][i])):
                self.tstHotTemperatures.append(self.splitdict['HotTemperatures'][i][j])
                
                if self.splitdict['HotTemperatures'][i][j] not in self.tstHotConstructionAid['T']:
                    self.tstHotConstructionAid['T'].append(self.splitdict['HotTemperatures'][i][j])
                    self.tstHotConstructionAid['Process'].append([i])
                    self.tstHotConstructionAid['Stream'].append([j])
                
                elif self.splitdict['HotTemperatures'][i][j] in self.tstHotConstructionAid['T']:
                    temp = self.tstHotConstructionAid['T'].index(self.splitdict['HotTemperatures'][i][j])
                    self.tstHotConstructionAid['Process'][temp].append(i)
                    self.tstHotConstructionAid['Stream'][temp].append(j)

        self.tstHotTemperatures = list(set(self.tstHotTemperatures))
        self.tstHotTemperatures.sort()

        for i in range(len(self.splitdict['ColdTemperatures'])):
            for j in range(len(self.splitdict['ColdTemperatures'][i])):
                self.tstColdTemperatures.append(self.splitdict['ColdTemperatures'][i][j])
                
                if self.splitdict['ColdTemperatures'][i][j] not in self.tstColdConstructionAid['T']:
                    self.tstColdConstructionAid['T'].append(self.splitdict['ColdTemperatures'][i][j])
                    self.tstColdConstructionAid['Process'].append([i])
                    self.tstColdConstructionAid['Stream'].append([j])
                
                elif self.splitdict['ColdTemperatures'][i][j] in self.tstColdConstructionAid['T']:
                    temp = self.tstColdConstructionAid['T'].index(self.splitdict['ColdTemperatures'][i][j])
                    self.tstColdConstructionAid['Process'][temp].append(i)
                    self.tstColdConstructionAid['Stream'][temp].append(j)

        self.tstColdTemperatures = list(set(self.tstColdTemperatures))
        self.tstColdTemperatures.sort()

        Steigung = []
        for Prozess in range(len(self.splitdict['ColdTemperatures'])):
            for Temperatur in range(len(self.splitdict['ColdTemperatures'][Prozess])-1):
                if self.splitdict['ColdTemperatures'][Prozess][Temperatur]-self.splitdict['ColdTemperatures'][Prozess][Temperatur+1] == 0:
                    Steigung.append(0.0)
                elif self.splitdict['ColdH'][Prozess][Temperatur]-self.splitdict['ColdH'][Prozess][Temperatur+1]<0:
                    Steigung.append(0.0)
                else:
                    Steigung.append((self.splitdict['ColdH'][Prozess][Temperatur]-self.splitdict['ColdH'][Prozess][Temperatur+1])/(self.splitdict['ColdTemperatures'][Prozess][Temperatur]-self.splitdict['ColdTemperatures'][Prozess][Temperatur+1]))
            self.splitdict['SteigungCold'].append(Steigung)
            Steigung = []
        
        
        Steigung = []
        for Prozess in range(len(self.splitdict['HotTemperatures'])):
            for Temperatur in range(len(self.splitdict['HotTemperatures'][Prozess])-1):
                if self.splitdict['HotH'][Prozess][Temperatur]-self.splitdict['HotH'][Prozess][Temperatur+1]>0:
                    Steigung.append(0.0)
                else:
                    Steigung.append((self.splitdict['HotH'][Prozess][Temperatur]-self.splitdict['HotH'][Prozess][Temperatur+1])/(self.splitdict['HotTemperatures'][Prozess][Temperatur]-self.splitdict['HotTemperatures'][Prozess][Temperatur+1]))
            self.splitdict['SteigungHot'].append(Steigung)
            Steigung = []

        kW = 0.0
        for Temperatur in self.tstHotTemperatures:
            for Prozess in reversed(range(len(self.splitdict['HotTemperatures']))):
                if self.splitdict['HotTemperatures'][Prozess] == []:
                    continue
                elif self.splitdict['HotTemperatures'][Prozess][-1] >= Temperatur:
                    continue

                for Prozesstemperatur in reversed(range(len(self.splitdict['HotTemperatures'][Prozess]))):
                    if Temperatur == self.splitdict['HotTemperatures'][Prozess][Prozesstemperatur]:
                        if letzteTemperaturHot > self.splitdict['HotTemperatures'][Prozess][Prozesstemperatur+1] and letzteTemperaturHot < self.splitdict['HotTemperatures'][Prozess][Prozesstemperatur]:
                            kW += self.splitdict['SteigungHot'][Prozess][Prozesstemperatur] * (self.splitdict['HotTemperatures'][Prozess][Prozesstemperatur] - letzteTemperaturHot)
                            break
                        else:
                            kW += self.splitdict['SteigungHot'][Prozess][Prozesstemperatur] * (Temperatur - self.splitdict['HotTemperatures'][Prozess][Prozesstemperatur+1])
                            break

                    elif Temperatur > self.splitdict['HotTemperatures'][Prozess][Prozesstemperatur] and Temperatur < self.splitdict['HotTemperatures'][Prozess][Prozesstemperatur-1]:
                        if letzteTemperaturHot > self.splitdict['HotTemperatures'][Prozess][Prozesstemperatur] and letzteTemperaturHot < self.splitdict['HotTemperatures'][Prozess][Prozesstemperatur-1]:
                            kW += self.splitdict['SteigungHot'][Prozess][Prozesstemperatur-1] * (Temperatur - letzteTemperaturHot)
                        else:
                            kW += self.splitdict['SteigungHot'][Prozess][Prozesstemperatur-1] * (Temperatur - self.splitdict['HotTemperatures'][Prozess][Prozesstemperatur])
                        break
                    else:
                        continue
            if self.tstHotH == []:
                self.tstHotH.append(kW)
            else:
                self.tstHotH.append(self.tstHotH[-1] + kW)
            kW = 0.0
            letzteTemperaturHot = Temperatur

        kW = 0.0
        for Temperatur in self.tstColdTemperatures:
            for Prozess in reversed(range(len(self.splitdict['ColdTemperatures']))):
                if self.splitdict['ColdTemperatures'][Prozess][-1] >= Temperatur:
                    continue

                for Prozesstemperatur in reversed(range(len(self.splitdict['ColdTemperatures'][Prozess]))):
                    if Temperatur == self.splitdict['ColdTemperatures'][Prozess][Prozesstemperatur]:
                        if letzteTemperaturCold > self.splitdict['ColdTemperatures'][Prozess][Prozesstemperatur+1] and letzteTemperaturCold < self.splitdict['ColdTemperatures'][Prozess][Prozesstemperatur]:
                            kW += self.splitdict['SteigungCold'][Prozess][Prozesstemperatur] * (self.splitdict['ColdTemperatures'][Prozess][Prozesstemperatur] - letzteTemperaturCold)
                            break
                        else:
                            kW += self.splitdict['SteigungCold'][Prozess][Prozesstemperatur] * (Temperatur - self.splitdict['ColdTemperatures'][Prozess][Prozesstemperatur+1])
                            break

                    elif Temperatur > self.splitdict['ColdTemperatures'][Prozess][Prozesstemperatur] and Temperatur < self.splitdict['ColdTemperatures'][Prozess][Prozesstemperatur-1]:
                        if letzteTemperaturCold > self.splitdict['ColdTemperatures'][Prozess][Prozesstemperatur] and letzteTemperaturCold < self.splitdict['ColdTemperatures'][Prozess][Prozesstemperatur-1]:
                            kW += self.splitdict['SteigungCold'][Prozess][Prozesstemperatur-1] * (Temperatur - letzteTemperaturCold)
                        else:
                            kW += self.splitdict['SteigungCold'][Prozess][Prozesstemperatur-1] * (Temperatur - self.splitdict['ColdTemperatures'][Prozess][Prozesstemperatur])
                        break
                    else:
                        continue
            if self.tstColdH == []:
                self.tstColdH.append(kW)
            else:
                self.tstColdH.append(self.tstColdH[-1] + kW)
            kW = 0.0
            letzteTemperaturCold = Temperatur

        maxheiß = self.tstHotH[-1]
        self.tstHotH = [wert - maxheiß for wert in self.tstHotH]
        a = 1
        for i in range(len(self.tstHotH)):
            self.tstHotH[i] = -self.tstHotH[i]
        if self._options['draw'] == True:
            TSPPlot().drawTotalSiteProfile(self.siteDesignation, self.tstHotH, 
                                           self.tstHotTemperatures, self.tstColdH, self.tstColdTemperatures, localisation)
        
