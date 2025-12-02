import matplotlib.pyplot as plt 

class PinchPlot:

    def drawTemperatureInterval(self, _temperatures, streams):
        fig, ax = plt.subplots()

        plt.title('Shifted Temperature Interval Diagram')
        plt.ylabel('Shifted Temperature S (degC)')
        ax.set_xticklabels([])

        xOffset = 50

        for temperature in _temperatures:
            plt.plot([0, xOffset * (streams.numberOf + 1)], [temperature, temperature], ':k', alpha=0.8)

        arrow_width = streams.numberOf * 0.05
        head_width = arrow_width * 15
        head_length = _temperatures[0] * 0.02
        i = 1
        for stream in streams:
            if stream['type'] == 'HOT':
                plt.text(xOffset, stream['ss'], str(i), bbox=dict(boxstyle='round', alpha=1, fc='tab:red', ec="k"))
                plt.arrow(xOffset, stream['ss'], 0, stream['st'] - stream['ss'], color='tab:red', ec='k', alpha=1,
                        length_includes_head=True, width=arrow_width, head_width=head_width, head_length=head_length)
            else:
                plt.text(xOffset, stream['ss'], str(i), bbox=dict(boxstyle='round', alpha=1, fc='tab:blue', ec="k"))
                plt.arrow(xOffset, stream['ss'], 0, stream['st'] - stream['ss'], color='tab:blue', ec='k', alpha=1,
                        length_includes_head=True, width=arrow_width, head_width=head_width, head_length=head_length)
            xOffset = xOffset + 50
            i = i + 1

    def drawProblemTable(self, problemTable, _temperatures):
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.axis('tight')
        ax.axis('off')
        ax.set_title('Problem Table')

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

        table = ax.table(cellText=cellText, colLabels=colLabels, loc='center')
        table.auto_set_column_width([0, 1, 2, 3, 4])
        table.scale(1.3, 1.3)


    def drawHeatCascade(self, unfeasibleHeatCascade, heatCascade, hotUtility):
        fig, axs = plt.subplots(1, 2, figsize=(10, 6))
        axs[0].axis('auto')
        axs[0].axis('off')
        axs[1].axis('auto')
        axs[1].axis('off')

        axs[0].set_title('Unfeasible Heat Cascade')
        axs[1].set_title('Feasible Heat Cascade')

        cellText = []
        cellText.append(['', '', 'Hot Utility: 0'])
        cellText.append(['Interval', '$\\Delta H (kW)$', 'Exit H (total kW)'])

        i = 1
        for interval in unfeasibleHeatCascade:
            cellText.append([str(i), interval['deltaH'], interval['exitH']])
            i = i + 1

        cellText.append(['', '', 'Cold Utility: {}'.format(unfeasibleHeatCascade[-1]['exitH'])])
        table = axs[0].table(cellText=cellText, loc='center')
        table.auto_set_column_width([0, 1, 2])
        table.scale(1.3, 1.3)

        cellText = []
        cellText.append(['', '', 'Hot Utility: {}'.format(hotUtility)])
        cellText.append(['Interval', '$\\Delta H (kW)$', 'Exit H (total kW)'])

        i = 1
        for interval in heatCascade:
            cellText.append([str(i), interval['deltaH'], interval['exitH']])
            i = i + 1

        cellText.append(['', '', 'Cold Utility: {}'.format(heatCascade[-1]['exitH'])])
        table = axs[1].table(cellText=cellText, loc='center')
        table.auto_set_column_width([0, 1, 2])
        table.scale(1.3, 1.3)


    def drawShiftedCompositeDiagram(self, shiftedCompositeDiagram, coldUtility, _temperatures, hotUtility, pinchTemperature, processdesignation, localisation):
        fig = plt.figure()
        plt.plot(shiftedCompositeDiagram['hot']['H'], shiftedCompositeDiagram['hot']['T'], 'tab:red')
        plt.plot(shiftedCompositeDiagram['cold']['H'], shiftedCompositeDiagram['cold']['T'], 'tab:blue')

        plt.plot(shiftedCompositeDiagram['hot']['H'], shiftedCompositeDiagram['hot']['T'], 'ro')
        plt.plot(shiftedCompositeDiagram['cold']['H'], shiftedCompositeDiagram['cold']['T'], 'bo')

        maxColdH = max(shiftedCompositeDiagram['cold']['H'])

        try:
            pinchIndex = shiftedCompositeDiagram['cold']['T'].index(pinchTemperature)
            pinchH = shiftedCompositeDiagram['cold']['H'][pinchIndex]
            plt.plot([pinchH, pinchH], [_temperatures[0], _temperatures[-1]], ':')
        except ValueError:
            pass

        a = plt.fill_between([coldUtility, shiftedCompositeDiagram['cold']['H'][0]-hotUtility], [shiftedCompositeDiagram['cold']['T'][0]])
        a.set_hatch('\\')
        a.set_facecolor('w')
        plt.grid(True)
        if localisation == 'DE':
            plt.title('Verschobene Verbundkurven ({})'.format(processdesignation))#plt.title('Shifted Temperature-Enthalpy Composite Diagram')
            plt.xlabel('Enthalpiestrom H in kW')
            plt.ylabel('Verschobene Temperatur in °C')
        elif localisation == 'EN':
            plt.title('Shifted Composite Diagram')
            plt.xlabel('Enthalpy H in kW')
            plt.ylabel('Shifted Temperature T in °C')

    def drawCompositeDiagram(self, compositeDiagram, shiftedCompositeDiagram, coldUtility, 
                             _temperatures, tmin, hotUtility, pinchTemperature, processdesignation, localisation):
        fig = plt.figure()
        plt.plot(compositeDiagram['hot']['H'], compositeDiagram['hot']['T'], 'tab:red')
        plt.plot(compositeDiagram['cold']['H'], compositeDiagram['cold']['T'], 'tab:blue')

        plt.plot(compositeDiagram['hot']['H'], compositeDiagram['hot']['T'], 'ro')
        plt.plot(compositeDiagram['cold']['H'], compositeDiagram['cold']['T'], 'bo')

        maxColdH = max(compositeDiagram['cold']['H'])

        try:
            pinchIndex = shiftedCompositeDiagram['cold']['T'].index(pinchTemperature)
            pinchH = shiftedCompositeDiagram['cold']['H'][pinchIndex]
            plt.plot([pinchH, pinchH], [_temperatures[0], _temperatures[-1]], ':')
        except ValueError:
            pass

        plt.grid(True)
        if localisation == 'DE':
            plt.title('Verbundkurven ({})'.format(processdesignation))#plt.title('Shifted Temperature-Enthalpy Composite Diagram')
            plt.xlabel('Enthalpiestrom H in kW')
            plt.ylabel('Temperatur in °C')
        elif localisation == 'EN':
            plt.title('Composite Diagram ({})'.format(processdesignation))
            plt.xlabel('Enthalpy H in kW')
            plt.ylabel('Temperature T in °C')


    def drawGrandCompositeCurve(self, processdesignation, heatCascade, grandCompositeCurve, _temperatures, pinchTemperature, localisation):
        fig = plt.figure(num='{}'.format(processdesignation))
        if heatCascade[0]['deltaH'] > 0:  
            plt.plot([grandCompositeCurve['H'][0],grandCompositeCurve['H'][1]], [grandCompositeCurve['T'][0],grandCompositeCurve['T'][1]], 'tab:red')
            plt.plot([grandCompositeCurve['H'][0],grandCompositeCurve['H'][1]], [grandCompositeCurve['T'][0],grandCompositeCurve['T'][1]], 'ro')
        elif heatCascade[0]['deltaH'] < 0:
            plt.plot([grandCompositeCurve['H'][0],grandCompositeCurve['H'][1]], [grandCompositeCurve['T'][0],grandCompositeCurve['T'][1]], 'tab:blue')
            plt.plot([grandCompositeCurve['H'][0],grandCompositeCurve['H'][1]], [grandCompositeCurve['T'][0],grandCompositeCurve['T'][1]], 'bo')

        for i in range(1, len(_temperatures)-1):
            if heatCascade[i]['deltaH'] > 0:
                plt.plot([grandCompositeCurve['H'][i],grandCompositeCurve['H'][i+1]], [grandCompositeCurve['T'][i],grandCompositeCurve['T'][i+1]], 'tab:red')
                plt.plot([grandCompositeCurve['H'][i],grandCompositeCurve['H'][i+1]], [grandCompositeCurve['T'][i],grandCompositeCurve['T'][i+1]], 'ro')
            elif heatCascade[i]['deltaH'] < 0:
                plt.plot([grandCompositeCurve['H'][i],grandCompositeCurve['H'][i+1]], [grandCompositeCurve['T'][i],grandCompositeCurve['T'][i+1]], 'tab:blue')
                plt.plot([grandCompositeCurve['H'][i],grandCompositeCurve['H'][i+1]], [grandCompositeCurve['T'][i],grandCompositeCurve['T'][i+1]], 'bo')
            elif heatCascade[i]['deltaH'] == 0 and grandCompositeCurve['H'][i]!=0:
                plt.plot([grandCompositeCurve['H'][i],grandCompositeCurve['H'][i+1]], [grandCompositeCurve['T'][i],grandCompositeCurve['T'][i+1]], 'tab:blue')
                plt.plot([grandCompositeCurve['H'][i],grandCompositeCurve['H'][i+1]], [grandCompositeCurve['T'][i],grandCompositeCurve['T'][i+1]], 'bo')

        plt.plot([0, grandCompositeCurve['H'][-1]], [pinchTemperature, pinchTemperature], ':')

        plt.grid(True)
        if localisation == 'DE':
            plt.title('Großverbundkurve ({})'.format(processdesignation))
            plt.xlabel('Nettoenthalpiestromänderung ∆H [kW]')
            plt.ylabel('Verschobene Temperatur [°C]')
        elif localisation == 'EN':
            plt.title('Grand Composite Diagram ({})'.format(processdesignation))
            plt.xlabel('Net Enthalpy Change ∆H in kW')
            plt.ylabel('Shifted Temperature T in °C')

    def showPlots():
        plt.show()
