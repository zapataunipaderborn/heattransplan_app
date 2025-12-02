from matplotlib import pyplot as plt
from Modules.Utility.Thermodynamic_Properties import ThermodynamicProperties as Props

class ISSP():
    def __init__(self, streamsDataFile, TS, TProcess, batchtimeSeconds, pyPinch, HPI, fromPinch, intermediateCircuit = {}):

        self.processdesignation = streamsDataFile[:-4]
        self.streamsDataFile = streamsDataFile
        self.options = {'draw', 'debug'}
        self.fromPinch = bool(fromPinch)
        self.intermediateCircuit = bool(intermediateCircuit)
        self.TS = TS
        self.TProcess = TProcess

        self.IntegrationPoint = HPI.solveforISSP()
        self.Pinch = pyPinch.solvePinchforISSP()
        self.CC = self.Pinch[0]
        self.pyPinch = self.Pinch[1]

        self.deltaTmin = self.pyPinch.tmin

        self.t = batchtimeSeconds/3600
    
    def CCinkWh(self):
        for i in range(len(self.CC['hot']['H'])):
            self.CC['hot']['H'][i] = self.CC['hot']['H'][i]*self.t
        self.CC['hot']['kWh'] = self.CC['hot']['H']
        del self.CC['hot']['H']

        for i in range(len(self.CC['cold']['H'])):
            self.CC['cold']['H'][i] = self.CC['cold']['H'][i]*self.t
        self.CC['cold']['kWh'] = self.CC['cold']['H']
        del self.CC['cold']['H']
    
    def ISSPHotIntermediateGerade(self, kWh, Tempdiff):
        return (self.IntegrationPoint['Temp'][-1]-Tempdiff) + ((self.IntegrationPoint['Temp'][0]-self.TemperaturKorrektur) - (self.IntegrationPoint['Temp'][-1]-Tempdiff))/(self.IntegrationPoint['QQuelle'][0]*self.t) * (kWh-self.DifferenzHot)
  
    def drawISSPHotIntermediate(self):#Verdichter
        if self.fromPinch == True:
            self.TemperaturKorrektur = 1.25 * self.deltaTmin
        else:
            self.TemperaturKorrektur = 0.25 * self.deltaTmin
        deltaTZwischenlreislauf0 = 2/4 * self.deltaTmin
        self.DifferenzHot = self.CC['hot']['kWh'][-1] - self.IntegrationPoint['QQuelle'][0]*self.t
        self.coldUtility = self.pyPinch.coldUtility*self.t
        self.hotUtility = self.pyPinch.hotUtility*self.t
        self._temperatures = self.pyPinch._temperatures
        self.pinchTemperature = self.pyPinch.pinchTemperature
        m = 0
        for i in range(len(self.CC['hot']['T'])):
            if self.CC['hot']['T'][i] >= self.IntegrationPoint['Temp'][-1]:
                
                try: m = self.CC['hot']['T'][i-1] + (self.CC['hot']['T'][i] - self.CC['hot']['T'][i-1])/(self.CC['hot']['kWh'][i] - self.CC['hot']['kWh'][i-1]) * (self.DifferenzHot-self.CC['hot']['kWh'][i-1])

                except: print('error m') #m = self.CC['hot']['T'][1] + (self.CC['hot']['T'][i+1] - self.CC['hot']['T'][i])/(self.CC['hot']['kWh'][i+1] - self.CC['hot']['kWh'][i]) * (self.IntegrationPoint['QQuelle'][0]*self.t - self.CC['hot']['kWh'][i])
                if m != 0:
                    break
        if float(self.DifferenzHot) == 0.0 and float(self.CC['hot']['kWh'][-2]) == 0.0:
            ZwischenkreislaufTemp = self.CC['hot']['T'][-1] - deltaTZwischenlreislauf0
        else:
            ZwischenkreislaufTemp = (self.CC['hot']['T'][-2] - deltaTZwischenlreislauf0) + (self.CC['hot']['T'][-2] - m) / (self.CC['hot']['kWh'][-2] - self.DifferenzHot) * (self.CC['hot']['kWh'][-1] -self.CC['hot']['kWh'][-2]) 
            self.TemperaturKorrektur = (self.CC['hot']['T'][-2] - self.TemperaturKorrektur) + (self.CC['hot']['T'][-2] - m) / (self.CC['hot']['kWh'][-2] - self.DifferenzHot) * (self.CC['hot']['kWh'][-1] -self.CC['hot']['kWh'][-2]) 
        
        self.VolumenWWSpeicher = round(self.IntegrationPoint['QQuelle'][0]*self.t * 3600 / (4.18 * (ZwischenkreislaufTemp-(m-deltaTZwischenlreislauf0)))/1000,1) #m^3
        plt.close('all')
        fig = plt.figure(num='{} Verd'.format(self.processdesignation))
        if self.intermediateCircuit == True:
            plt.plot(self.CC['hot']['kWh'], self.CC['hot']['T'], 'tab:red')
            plt.plot([self.DifferenzHot,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot], [self.IntegrationPoint['Temp'][-1]-1.25*self.deltaTmin,+self.TemperaturKorrektur], 'tab:blue')
            plt.plot([self.DifferenzHot,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot], [m-deltaTZwischenlreislauf0,ZwischenkreislaufTemp], 'k')

            #plt.plot(self.CC['hot']['kWh'], self.CC['hot']['T'], 'ro')
            plt.plot([self.DifferenzHot,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot], [self.IntegrationPoint['Temp'][-1]-1.25*self.deltaTmin,self.TemperaturKorrektur], 'bo')
            plt.plot([self.DifferenzHot,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot],[(m-deltaTZwischenlreislauf0),ZwischenkreislaufTemp],'ko')
        elif self.fromPinch == False: 
            plt.plot([0,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot], [self._temperatures[-1]+0.5*self.deltaTmin,ZwischenkreislaufTemp-self.deltaTmin], 'tab:red')
            plt.plot([0,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot], [self._temperatures[-1]+0.25*self.deltaTmin,self._temperatures[-1]+0.25*self.deltaTmin])#,self.TemperaturKorrektur], 'tab:blue')
            plt.plot([0,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot], [self._temperatures[-1]+0.5*self.deltaTmin,ZwischenkreislaufTemp-self.deltaTmin],linestyle = (0, (5, 10)), color = 'black')

            #plt.plot(self.CC['hot']['kWh'], self.CC['hot']['T'], 'ro')
            plt.plot([0,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot], [self._temperatures[-1]+0.25*self.deltaTmin,self._temperatures[-1]+0.25*self.deltaTmin], 'bo') #self.TemperaturKorrektur
            plt.plot([0,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot],[self._temperatures[-1]+0.5*self.deltaTmin,ZwischenkreislaufTemp-self.deltaTmin],'ko')
        elif self.fromPinch == True:
            plt.plot([0,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot], [m-deltaTZwischenlreislauf0,ZwischenkreislaufTemp], 'tab:red')
            plt.plot([0,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot], [self._temperatures[-1]+0.25*self.deltaTmin,self._temperatures[-1]+0.25*self.deltaTmin])#,self.TemperaturKorrektur], 'tab:blue')
            plt.plot([0,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot], [m-deltaTZwischenlreislauf0,ZwischenkreislaufTemp],linestyle = (0, (5, 10)), color = 'black')

            #plt.plot(self.CC['hot']['kWh'], self.CC['hot']['T'], 'ro')
            plt.plot([0,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot], [self.IntegrationPoint['Temp'][-1]-1.25*self.deltaTmin,self.IntegrationPoint['Temp'][-1]-1.25*self.deltaTmin], 'bo') #self.TemperaturKorrektur
            plt.plot([0,self.IntegrationPoint['QQuelle'][0]*self.t+self.DifferenzHot],[(m-deltaTZwischenlreislauf0),ZwischenkreislaufTemp],'ko')


        plt.grid(True,linewidth=1.5)
        plt.tick_params(axis='both', which='major', labelsize=12)
        plt.title('a) ISSP stratified TES', fontsize=14)
        plt.xlabel('ΔH / Batch in kWh', fontsize=14)
        plt.ylabel('Shifted temperature T in °C', fontsize=14)

    def drawISSPColdIntermediate(self):
        deltaTZwischenkreislauf = 3/4 * self.deltaTmin
        if self.fromPinch == True:
            Verschiebung = 1.25 * self.deltaTmin
            Verschiebung2 = 1.25 * self.deltaTmin
        else:
            Verschiebung = 0.25 * self.deltaTmin
            Verschiebung2 = 0.25 * self.deltaTmin
        self.Dampfmasse = (self.IntegrationPoint['QSenke'][0]*self.t * 3600)/Props.get_latentheat(self.TS)
            #vStrich1 = 1/925.014712422 #140 °C
        h1_prime = Props.get_hprime(self.TS)
        h1_double_prime = Props.get_hdouble_prime(self.TS)
        v1_prime = Props.get_vprime(self.TS)
        h2_prime = Props.get_hprime(self.TProcess)
        h2_double_prime = Props.get_hdouble_prime(self.TProcess)

        Füllgrad = 0.9     
        self.VolumenDampfSpeicher = round(self.Dampfmasse/ ((Füllgrad/v1_prime)*((h1_prime-h2_prime)/(0.5*(h1_double_prime+h2_double_prime)-h2_prime))),1)
        #http://berndglueck.de/Waermespeicher

        fig = plt.figure(num='{} Kond'.format(self.processdesignation))
        if self.intermediateCircuit == True:
            plt.plot([self.CC['cold']['kWh'][-1],self.IntegrationPoint['QSenke'][0]*self.t+self.CC['cold']['kWh'][-1]], [self.CC['cold']['T'][-1]+Verschiebung,self.CC['cold']['T'][0]+Verschiebung], 'tab:red')
            plt.plot(self.CC['cold']['kWh'], self.CC['cold']['T'], 'tab:blue')
            plt.plot([self.CC['cold']['kWh'][-1],self.IntegrationPoint['QSenke'][0]*self.t+self.CC['cold']['kWh'][-1]], [self.CC['cold']['T'][-1]+Verschiebung-deltaTZwischenkreislauf,self.CC['cold']['T'][0]+Verschiebung-deltaTZwischenkreislauf], 'k')

            plt.plot([self.CC['cold']['kWh'][-1],self.IntegrationPoint['QSenke'][0]*self.t+self.CC['cold']['kWh'][-1]], [self.CC['cold']['T'][-1]+Verschiebung,self.CC['cold']['T'][0]+Verschiebung], 'ro')
            plt.plot(self.CC['cold']['kWh'], self.CC['cold']['T'], 'bo')
            plt.plot([self.CC['cold']['kWh'][-1],self.IntegrationPoint['QSenke'][0]*self.t+self.CC['cold']['kWh'][-1]], [self.CC['cold']['T'][-1]+Verschiebung-deltaTZwischenkreislauf,self.CC['cold']['T'][0]+Verschiebung-deltaTZwischenkreislauf], 'ko')
        else:
            plt.plot([0,self.IntegrationPoint['QSenke'][0]*self.t], [self.CC['cold']['T'][0]+Verschiebung2,self.CC['cold']['T'][0]+Verschiebung2], 'tab:red')
            plt.plot([0,self.IntegrationPoint['QSenke'][0]*self.t], [self.CC['cold']['T'][-1]+Verschiebung-deltaTZwischenkreislauf,self.CC['cold']['T'][0]+Verschiebung-deltaTZwischenkreislauf], 'tab:blue')
            plt.plot([0,self.IntegrationPoint['QSenke'][0]*self.t], [self.CC['cold']['T'][-1]+Verschiebung-deltaTZwischenkreislauf,self.CC['cold']['T'][0]+Verschiebung-deltaTZwischenkreislauf],linestyle = (0, (5, 10)), color = 'black')

            plt.plot([0,self.IntegrationPoint['QSenke'][0]*self.t], [self.CC['cold']['T'][0]+Verschiebung2,self.CC['cold']['T'][0]+Verschiebung2], 'ro')
            #plt.plot(self.CC['cold']['kWh'], self.CC['cold']['T'], 'bo')
            plt.plot([0,self.IntegrationPoint['QSenke'][0]*self.t], [self.CC['cold']['T'][-1]+Verschiebung-deltaTZwischenkreislauf,self.CC['cold']['T'][0]+Verschiebung-deltaTZwischenkreislauf], 'ko')

        plt.grid(True,linewidth=1.5)
        plt.tick_params(axis='both', which='major', labelsize=12)
        plt.title('b) ISSP steam RSA', fontsize=14)
        plt.xlabel('ΔH / Batch in kWh', fontsize=14)
        plt.xlim(right = 2500)
        plt.ylabel('Shifted temperature T in °C', fontsize=14)