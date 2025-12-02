import os
import csv

class PinchExport:
    def __init__(self):
         pass
    def csvProblemTable(self, problemTable, _temperatures, newpath):
        colLabels = ['$Interval: S_i - S_{i+1}$', '$\\Delta T (\\degree C)$', '$\\Delta CP (kW / \\degree C)$', '$\\Delta H (kW)$', '']
        cellText = []

        i = 1
        for interval in problemTable:
            cellRow = []
            cellRow.extend(['{}: {} - {}'.format(i, _temperatures[i - 1], _temperatures[i]),
                interval['deltaS'], interval['deltaCP'], interval['deltaH']])

            if interval['deltaH'] > 0:
                cellRow.append('Surplus')
            elif interval['deltaH'] == 0:
                cellRow.append('-')
            else:
                cellRow.append('Deficit')
            cellText.append(cellRow)
            i = i + 1


        if not os.path.exists(newpath):
            os.makedirs(newpath)
        fileName = 'ProblemTable.csv'

        path = os.path.join(newpath, fileName)
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow(['Interval: S1 - S2', 'delta T (degC)', 'delta CP (kW / degC)', 'delta H (kW)', ''])
            for rowText in cellText:
                writer.writerow(rowText)

    def csvHeatCascade(self, unfeasibleHeatCascade, hotUtility, heatCascade, pinchTemperature, newpath):
        cellText = [['Unfeasible Heat Cascade: ']]
        cellText.append(['', '', 'Hot Utility: 0 kW'])
        cellText.append(['Interval', 'Delta H (kW)', 'Exit H (total kW)'])

        i = 1
        for interval in unfeasibleHeatCascade:
            cellText.append([str(i), interval['deltaH'], interval['exitH']])
            i = i + 1

        cellText.append(['', '', 'Cold Utility: {} kW'.format(unfeasibleHeatCascade[-1]['exitH'])])
        cellText.append([''])

        cellText.append(['Feasible Heat Cascade: '])
        cellText.append(['', '', 'Hot Utility: {} kW'.format(hotUtility)])
        cellText.append(['Interval', 'Delta H (kW)', 'Exit H (total kW)'])

        i = 1
        for interval in heatCascade:
            cellText.append([str(i), interval['deltaH'], interval['exitH']])
            i = i + 1

        cellText.append(['', '', 'Cold Utility: {} kW'.format(heatCascade[-1]['exitH'])])
        cellText.append(['','', 'Pinch Temperature: {} degC'.format(pinchTemperature)])

        if not os.path.exists(newpath):
            os.makedirs(newpath)
        fileName = 'HeatCascade.csv'

        path = os.path.join(newpath, fileName)

        with open(path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=',')
            for rowText in cellText:
                writer.writerow(rowText)


    def csvShiftedCompositeDiagram(self, newpath, shiftedCompositeDiagram):
        if not os.path.exists(newpath):
            os.makedirs(newpath)
        fileName = 'ShiftedCompositeDiagram.csv'

        path = os.path.join(newpath, fileName)
        
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow(['Hot H', 'Hot T'])
            for i in range(0, len(shiftedCompositeDiagram['hot']['H'])):
                writer.writerow([shiftedCompositeDiagram['hot']['H'][i],
                    shiftedCompositeDiagram['hot']['T'][i]])

            writer.writerow([''])
            writer.writerow(['Cold H', 'Cold T'])
            for i in range(0, len(shiftedCompositeDiagram['cold']['H'])):
                writer.writerow([shiftedCompositeDiagram['cold']['H'][i],
                    shiftedCompositeDiagram['cold']['T'][i]])


    def csvCompositeDiagram(self, newpath, compositeDiagram):
        if not os.path.exists(newpath):
            os.makedirs(newpath)
        fileName = 'CompositeDiagram.csv'

        path = os.path.join(newpath, fileName)
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow(['Hot H', 'Hot T'])
            for i in range(0, len(compositeDiagram['hot']['H'])):
                writer.writerow([compositeDiagram['hot']['H'][i],
                    compositeDiagram['hot']['T'][i]])

            writer.writerow([''])
            writer.writerow(['Cold H', 'Cold T'])
            for i in range(0, len(compositeDiagram['cold']['H'])):
                writer.writerow([compositeDiagram['cold']['H'][i],
                    compositeDiagram['cold']['T'][i]])



    def csvGrandCompositeCurve(self, newpath, grandCompositeCurve):
        if not os.path.exists(newpath):
            os.makedirs(newpath)
        fileName = 'GrandCompositeCurve.csv'

        path = os.path.join(newpath, fileName)
        with open(path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow(['Net H (kW)', 'T(degC)'])
            for i in range(0, len(grandCompositeCurve['H'])):
                writer.writerow([grandCompositeCurve['H'][i],
                    grandCompositeCurve['T'][i]])

