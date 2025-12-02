import matplotlib.pyplot as plt

class TSPPlot():
    
    def drawDeletedCurve(self, heatCascadedeltaH, deletedPocketdict, _temperatures, plottest):
        fig = plt.figure()
        if heatCascadedeltaH[0] > 0:  
            plt.plot([deletedPocketdict['H'][0][0],deletedPocketdict['H'][0][1]], [deletedPocketdict['T'][0][0],deletedPocketdict['T'][0][1]], 'tab:red')
            plt.plot([deletedPocketdict['H'][0][0],deletedPocketdict['H'][0][1]], [deletedPocketdict['T'][0][0],deletedPocketdict['T'][0][1]], 'ro')
        elif heatCascadedeltaH[0] < 0:
            plt.plot([deletedPocketdict['H'][0][0],deletedPocketdict['H'][0][1]], [deletedPocketdict['T'][0][0],deletedPocketdict['T'][0][1]], 'tab:blue')
            plt.plot([deletedPocketdict['H'][0][0],deletedPocketdict['H'][0][1]], [deletedPocketdict['T'][0][0],deletedPocketdict['T'][0][1]], 'bo')
        
        if plottest == 1:
            for i in range(1, len(_temperatures)-2):
                if heatCascadedeltaH[i] > 0:
                    plt.plot([deletedPocketdict['H'][0][i],deletedPocketdict['H'][0][i+1]], [deletedPocketdict['T'][0][i],deletedPocketdict['T'][0][i+1]], 'tab:red')
                    plt.plot([deletedPocketdict['H'][0][i],deletedPocketdict['H'][0][i+1]], [deletedPocketdict['T'][0][i],deletedPocketdict['T'][0][i+1]], 'ro')
                elif heatCascadedeltaH[i] < 0:
                    plt.plot([deletedPocketdict['H'][0][i],deletedPocketdict['H'][0][i+1]], [deletedPocketdict['T'][0][i],deletedPocketdict['T'][0][i+1]], 'tab:blue')
                    plt.plot([deletedPocketdict['H'][0][i],deletedPocketdict['H'][0][i+1]], [deletedPocketdict['T'][0][i],deletedPocketdict['T'][0][i+1]], 'bo')
                else:
                    plt.plot([deletedPocketdict['H'][0][i],deletedPocketdict['H'][0][i+1]], [deletedPocketdict['T'][0][i],deletedPocketdict['T'][0][i+1]], 'tab:blue')
                    plt.plot([deletedPocketdict['H'][0][i],deletedPocketdict['H'][0][i+1]], [deletedPocketdict['T'][0][i],deletedPocketdict['T'][0][i+1]], 'bo')
        if plottest == 0:
            for i in range(1, len(_temperatures)-1):
                if heatCascadedeltaH[i] > 0:
                    plt.plot([deletedPocketdict['H'][0][i],deletedPocketdict['H'][0][i+1]], [deletedPocketdict['T'][0][i],deletedPocketdict['T'][0][i+1]], 'tab:red')
                    plt.plot([deletedPocketdict['H'][0][i],deletedPocketdict['H'][0][i+1]], [deletedPocketdict['T'][0][i],deletedPocketdict['T'][0][i+1]], 'ro')
                elif heatCascadedeltaH[i] < 0:
                    plt.plot([deletedPocketdict['H'][0][i],deletedPocketdict['H'][0][i+1]], [deletedPocketdict['T'][0][i],deletedPocketdict['T'][0][i+1]], 'tab:blue')
                    plt.plot([deletedPocketdict['H'][0][i],deletedPocketdict['H'][0][i+1]], [deletedPocketdict['T'][0][i],deletedPocketdict['T'][0][i+1]], 'bo')
                else:
                    plt.plot([deletedPocketdict['H'][0][i],deletedPocketdict['H'][0][i+1]], [deletedPocketdict['T'][0][i],deletedPocketdict['T'][0][i+1]], 'tab:blue')
                    plt.plot([deletedPocketdict['H'][0][i],deletedPocketdict['H'][0][i+1]], [deletedPocketdict['T'][0][i],deletedPocketdict['T'][0][i+1]], 'bo')

        # plt.fill_between([0, deletedPocketdict['H'][0][0]], 0, _temperatures[0], color = 'r', alpha = 0.5)
        # plt.fill_between([0, deletedPocketdict['H'][0][-1]], 0, _temperatures[-1], color = 'b', alpha = 0.5)


        plt.grid(True)
        plt.title('Grand Composite Curve')
        plt.xlabel('Net Enthalpy Change ∆H [kW]')
        plt.ylabel('Shifted Temperature T [°C]')


    def drawTotalSiteProfile(self, siteDesignation, tstHotH, tstHotTemperatures, tstColdH, tstColdTemperatures, localisation):
        #Wieder aus den ausgegebenen Werten fuer alle Prozesse Temperaturintervalle erstellen und diese dann plotten
        fig, (ax1, ax2) = plt.subplots(1, 2)
  
        fig.suptitle('Total Site Profile ({})'.format(siteDesignation))
        
        ax1.plot(tstHotH, tstHotTemperatures, 'tab:red')
        if localisation == 'DE':
            ax1.set(xlabel='Nettoenthalpieänderung ∆H in kW', ylabel='Verschobene Temperatur T in °C')
        elif localisation == 'EN':
            ax1.set(xlabel='Net Enthalpy Change ∆H in kW', ylabel='Shifted Temperature T in °C')

        ax1.grid()
        ax2.plot(tstColdH, tstColdTemperatures, 'tab:blue')
        if localisation == 'DE':
            ax2.set_xlabel('Nettoenthalpieänderung ∆H in kW')
        elif localisation == 'EN':
            ax2.set(xlabel='Net Enthalpy Change ∆H in kW')
        
        ax2.grid()

        ax2.set_xlim([0,tstColdH[-1]])
        ax1.set_xlim([tstHotH[0],0]) 

        if tstHotH == [] or tstColdH == []:
            pass

        elif tstHotTemperatures[-1] > tstColdTemperatures[-1]:
            if tstHotTemperatures[0] > tstColdTemperatures[0]:
                ax1.set_ylim([tstColdTemperatures[0]-2.5,tstHotTemperatures[-1]+2.5])
                ax2.set_ylim([tstColdTemperatures[0]-2.5,tstHotTemperatures[-1]+2.5])
            elif tstHotTemperatures[0] < tstColdTemperatures[0]:
                ax1.set_ylim([tstHotTemperatures[0]-2.5,tstHotTemperatures[-1]+2.5])
                ax2.set_ylim([tstHotTemperatures[0]-2.5,tstHotTemperatures[-1]+2.5])
            else:
                pass

        elif tstHotTemperatures[-1] < tstColdTemperatures[-1]:
            if tstHotTemperatures[0] > tstColdTemperatures[0]:
                ax1.set_ylim([tstColdTemperatures[0]-2.5,tstColdTemperatures[-1]+2.5])
                ax2.set_ylim([tstColdTemperatures[0]-2.5,tstColdTemperatures[-1]+2.5])
            elif tstHotTemperatures[0] < tstColdTemperatures[0]:
                ax1.set_ylim([tstHotTemperatures[0]-2.5,tstColdTemperatures[-1]+2.5])
                ax2.set_ylim([tstHotTemperatures[0]-2.5,tstColdTemperatures[-1]+2.5])
            else:
                pass


    def showPlots(self):
        plt.show()
