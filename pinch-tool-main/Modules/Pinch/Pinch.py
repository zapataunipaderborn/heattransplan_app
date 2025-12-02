#Based on:
    #!/usr/bin/env python3
    # -*- coding: utf-8 -*-
    # File              : PyPinch.py
    # License           : License: GNU v3.0
    # Author            : Andrei Leonard Nicusan <aln705@student.bham.ac.uk>
    # Date              : 25.05.2019

import csv
import os
import numpy as np
from Modules.Pinch.Streams import Streams 
from Modules.Pinch.PinchPlot import PinchPlot
from Modules.Pinch.PinchExport import PinchExport


class Pinch:

    def __init__(self, streamsDataFile, options = {}):

        self.tmin =                      0
        self.streams =                   []
        self.temperatureInterval =       []
        self.problemTable =              []
        self.hotUtility =                0
        self.coldUtility =               0
        self.unfeasibleHeatCascade =     []
        self.heatCascade =               []
        self.pinchTemperature =          0
        self.shiftedCompositeDiagram =   {'hot': {'H': [], 'T': []}, 'cold': {'H': [], 'T': []}}
        self.compositeDiagram =          {'hot': {'H': [], 'T': []}, 'cold': {'H': [], 'T': []}}
        self.grandCompositeCurve =       {'H': [], 'T': []}

        self._temperatures =             []
        self._deltaHHot =                []
        self._deltaHCold =               []
        self._options =                  {'debug': False, 'draw': False, 'csv': False}
        self._temperaturesHOT=           []
        self._temperaturesCOLD =         []
        self.emptyintervalstartHOT=         []
        self.emptyintervalstartCOLD = []
        self.lastHotStream = 0
        self.lastColdStream = 0

        self.emptyintervalsHot = {'H': [], 'T': []}
        self.emptyintervalsCold = {'H': [], 'T': []}

        self.processdesignation = streamsDataFile[:-4]
        path = r"{} Pinch".format(self.processdesignation)
        self.newpath = 'Output'+ '\\' + path

        self.streams = Streams(streamsDataFile)
        self.tmin = self.streams.tmin

        if 'debug' in options:
            self._options['debug'] = True
        if 'draw' in options:
            self._options['draw'] = True
        if 'csv' in options:
            self._options['csv'] = True


    def shiftTemperatures(self):
        for stream in self.streams:
            if stream['type'] == 'HOT':
                stream['ss'] = stream['ts'] - self.tmin / 2
                stream['st'] = stream['tt'] - self.tmin / 2
            else:
                stream['ss'] = stream['ts'] + self.tmin / 2
                stream['st'] = stream['tt'] + self.tmin / 2

        if self._options['debug'] == True:
            print("\nStreams: ")
            for stream in self.streams:
                print(stream)
            print("Tmin = {}".format(self.tmin))


    def constructTemperatureInterval(self):
        # Take all shifted temperatures and reverse sort them,
        # removing all duplicates
        for stream in self.streams:
            self._temperatures.append(stream['ss'])
            self._temperatures.append(stream['st'])

            if (stream["type"] == "HOT"):
                self._temperaturesHOT.append(stream['ss'])
                self._temperaturesHOT.append(stream['st'])

            else:
                self._temperaturesCOLD.append(stream['ss'])
                self._temperaturesCOLD.append(stream['st'])


        self._temperaturesHOT = list(set(self._temperaturesHOT))
        self._temperaturesHOT.sort()
        self._temperaturesCOLD = list(set(self._temperaturesCOLD))
        self._temperaturesCOLD.sort()
        self._temperatures = list(set(self._temperatures))
        self._temperatures.sort(reverse = True)

        # Save the stream number of all the streams that pass
        # through each shifted temperature interval
        for i in range(len(self._temperatures) - 1):
            t1 = self._temperatures[i]
            t2 = self._temperatures[i + 1]
            interval = {'t1': t1, 't2': t2, 'streamNumbers': []}

            
            j = 0
            for stream in self.streams:
                if (stream['type'] == 'HOT'):
                    if (stream['ss'] >= t1 and stream['st'] <= t2):
                        interval['streamNumbers'].append(j)
                else:
                    if (stream['st'] >= t1 and stream['ss'] <= t2):
                        interval['streamNumbers'].append(j)
                j = j + 1

            self.temperatureInterval.append(interval)
        


        if self._options['debug'] == True:
            print("\nTemperature Intervals: ")
            i = 0
            print(self._temperatures)
            for interval in self.temperatureInterval:
                print("Interval {} : {}".format(i, interval))
                i = i + 1

        if self._options['draw'] == True:
            PinchPlot().drawTemperatureInterval(self._temperatures, self.streams)



    def constructProblemTable(self):

        for interval in self.temperatureInterval:
            row = {}
            row['deltaS'] = interval['t1'] - interval['t2']
            row['deltaCP'] = 0

            for i in interval['streamNumbers']:
                if interval['streamNumbers'] != []:
                    if self.streams.streamsData[i]['type'] == 'HOT':
                        row['deltaCP'] = row['deltaCP'] + self.streams.streamsData[i]['cp']
                    else:
                        row['deltaCP'] = row['deltaCP'] - self.streams.streamsData[i]['cp']
                else:
                    row['deltaCP'] = 0

            row['deltaH'] = row['deltaS'] * row['deltaCP']
            self.problemTable.append(row)

        if self._options['debug'] == True:
            print("\nProblem Table: ")
            i = 0
            for interval in self.problemTable:
                print("Interval {} : {}".format(i, interval))
                i = i + 1

        if self._options['draw'] == True:
            PinchPlot().drawProblemTable(self.problemTable, self._temperatures)

        if self._options['csv'] == True:
            PinchExport().csvProblemTable(self.problemTable, self._temperatures, self.newpath)
 

    def constructHeatCascade(self):

        exitH = 0
        lowestExitH = 0

        i = 0
        pinchInterval = 0
        for interval in self.problemTable:
            row = {}
            row['deltaH'] = interval['deltaH']

            exitH = exitH + row['deltaH']
            row['exitH'] = exitH
            if exitH < lowestExitH:
                lowestExitH = exitH
                pinchInterval = i

            self.unfeasibleHeatCascade.append(row)
            i = i + 1

        self.hotUtility = -lowestExitH
        exitH = self.hotUtility

        for interval in self.problemTable:
            row = {}
            row['deltaH'] = interval['deltaH']

            exitH = exitH + row['deltaH']
            row['exitH'] = exitH

            self.heatCascade.append(row)

        self.coldUtility = exitH
        if pinchInterval == 0:
            self.pinchTemperature = self.temperatureInterval[pinchInterval]['t1']
        else:
            self.pinchTemperature = self.temperatureInterval[pinchInterval]['t2']

        if self._options['debug'] == True:
            print("\nUnfeasible Heat Cascade: ")
            i = 0
            for interval in self.unfeasibleHeatCascade:
                print("Interval {} : {}".format(i, interval))
                i = i + 1

            print("\nFeasible Heat Cascade: ")
            i = 0
            for interval in self.heatCascade:
                print("Interval {} : {}".format(i, interval))
                i = i + 1

            print("\nPinch Temperature (degC): {}".format(self.pinchTemperature))
            print("Minimum Hot Utility (kW): {}".format(self.hotUtility))
            print("Minimum Cold Utility (kW): {}".format(self.coldUtility))

        if self._options['draw'] == True:
            PinchPlot().drawHeatCascade(self.unfeasibleHeatCascade, self.heatCascade, self.hotUtility)

        if self._options['csv'] == True:
            PinchExport().csvHeatCascade(self.unfeasibleHeatCascade, self.hotUtility, self.heatCascade, self.pinchTemperature, self.newpath)


    def constructShiftedCompositeDiagram(self, localisation):
        emptylist = []
        for interval in self.temperatureInterval:
            hotH = 0
            coldH = 0
            # Add CP values for the hot and cold streams
            # in a given temperature interval
            for i in interval['streamNumbers']:
                if interval['streamNumbers'] != []:
                    if self.streams.streamsData[i]['type'] == 'HOT':
                        hotH = hotH + self.streams.streamsData[i]['cp']
                        #self.shiftedCompositeDiagram['hot']['T'].append(self.streamsData[i]['ss'])
                        #self.shiftedCompositeDiagram['hot']['T'].append(self.streamsData[i]['st'])
                    else:
                        coldH = coldH + self.streams.streamsData[i]['cp']
                        #self.shiftedCompositeDiagram['cold']['T'].append(self.streamsData[i]['ss'])
                        #self.shiftedCompositeDiagram['cold']['T'].append(self.streamsData[i]['st'])
                else:
                    hotH = 0
                    emptylist.append(i)
            # Enthalpy = CP * deltaT 
            #checken ob geprüftes interval einen heißen strom enthält und erst dann anfangen
            #dann immer wieder prüfen, ob danach noch ein heoßer strom kommt
            
            hotH = hotH * (interval['t1'] - interval['t2'])
            self._deltaHHot.append(hotH)



            coldH = coldH * (interval['t1'] - interval['t2'])
            self._deltaHCold.append(coldH)


# rot bei 0/t1 anfangen
# blau bei coldutility/t2 anfangen
        self.shiftedCompositeDiagram['hot']['T']= []

        self._deltaHHot.reverse()
        self.shiftedCompositeDiagram['hot']['H'].append(0.0)
        for i in range(1, len(self._temperatures)):
            self.shiftedCompositeDiagram['hot']['H'].append(self.shiftedCompositeDiagram['hot']['H'][-1] + self._deltaHHot[i-1])
            self.shiftedCompositeDiagram['hot']['T'].append(self._temperatures[len(self._temperatures)-i])


        self.shiftedCompositeDiagram['hot']['T'].append(self._temperatures[0])
        #Summe aus allen deltaHCold + coldutility machen und für die Schritte jeweils deltaHCold abziehen
        coldgesamt = self.coldUtility
        for i in range(len(self._deltaHCold)):
            coldgesamt += self._deltaHCold[i]

        #Experimentell
        self.shiftedCompositeDiagram['cold']['T']= []

        self.shiftedCompositeDiagram['cold']['H'].append(coldgesamt)

        #Experimentell
        self.shiftedCompositeDiagram['cold']['T'].append(self._temperatures[0])
        for i in range(1, len(self._temperatures)):
            self.shiftedCompositeDiagram['cold']['H'].append(self.shiftedCompositeDiagram['cold']['H'][-1] - self._deltaHCold[i-1])
            self.shiftedCompositeDiagram['cold']['T'].append(self._temperatures[i])
        

        iliste = []
        for i in range(1,(len(self.shiftedCompositeDiagram['cold']['H'])-1)):
            if self.shiftedCompositeDiagram['cold']['H'] == 0.0:
                iliste.append(i+1)
            elif self.shiftedCompositeDiagram['cold']['H'][i] == self.shiftedCompositeDiagram['cold']['H'][0]:
                iliste.append(i-1)
            elif self.shiftedCompositeDiagram['cold']['H'][i] == self.shiftedCompositeDiagram['cold']['H'][-1]:
                iliste.append(i+1)
        iliste.reverse()
        
        for i in iliste:
            self.shiftedCompositeDiagram['cold']['H'].pop(i)
            self.shiftedCompositeDiagram['cold']['T'].pop(i)
        iliste = []
        for i in range(1,(len(self.shiftedCompositeDiagram['hot']['H'])-1)):
            if self.shiftedCompositeDiagram['hot']['H'][i] == 0.0:
                iliste.append(i-1)
            elif self.shiftedCompositeDiagram['hot']['H'][i] == self.shiftedCompositeDiagram['hot']['H'][-1]:
                iliste.append(i+1)
        iliste.reverse()

        for i in iliste:
            self.shiftedCompositeDiagram['hot']['H'].pop(i)
            self.shiftedCompositeDiagram['hot']['T'].pop(i)
        
        if self._options['draw'] == True:
            PinchPlot().drawShiftedCompositeDiagram(self.shiftedCompositeDiagram, self.coldUtility, 
                                                    self._temperatures, self.hotUtility, self.pinchTemperature, 
                                                    self.processdesignation, localisation)

        if self._options['csv'] == True:
            PinchExport().csvShiftedCompositeDiagram(self.newpath, self.shiftedCompositeDiagram)
        


    def constructCompositeDiagram(self, localisation):
        self.compositeDiagram['hot']['T'] = [x + self.tmin / 2 for x in self.shiftedCompositeDiagram['hot']['T']]
        self.compositeDiagram['hot']['H'] = self.shiftedCompositeDiagram['hot']['H']
        self.compositeDiagram['cold']['T'] = [x - self.tmin / 2 for x in self.shiftedCompositeDiagram['cold']['T']]
        self.compositeDiagram['cold']['H'] = self.shiftedCompositeDiagram['cold']['H']
        print(self._temperatures)
        if self._options['draw'] == True:
            PinchPlot().drawCompositeDiagram(self.compositeDiagram, self.shiftedCompositeDiagram, 
                                             self.coldUtility, self._temperatures, self.tmin, self.hotUtility, 
                                             self.pinchTemperature, self.processdesignation, localisation)

        if self._options['csv'] == True:
            PinchExport().csvCompositeDiagram(self.newpath, self.compositeDiagram)



    def constructGrandCompositeCurve(self,localisation):
        self.grandCompositeCurve['H'].append(self.hotUtility)
        self.grandCompositeCurve['T'].append(self._temperatures[0])
        for i in range(1, len(self._temperatures)):
            self.grandCompositeCurve['H'].append(self.heatCascade[i - 1]['exitH'])
            self.grandCompositeCurve['T'].append(self._temperatures[i])
        print(self.grandCompositeCurve)
        print(self.heatCascade)

        if self._options['debug'] == True:
            print("\nGrand Composite Curve: ")
            print("Net H (kW): {}".format(self.grandCompositeCurve['H']))
            print("T (degC): {}".format(self.grandCompositeCurve['T']))
            

        if self._options['draw'] == True:
            PinchPlot().drawGrandCompositeCurve(self.processdesignation, self.heatCascade, 
                                                self.grandCompositeCurve, self._temperatures, self.pinchTemperature, localisation)

        if self._options['csv'] == True:
            PinchExport().csvGrandCompositeCurve(self.newpath, self.grandCompositeCurve)

