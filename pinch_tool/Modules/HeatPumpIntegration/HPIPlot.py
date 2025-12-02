from matplotlib import pyplot as plt

class HPIPlot():
    def __init__(self, processdesignation, Tsinkout, pyPinch, EvWP, KoWP, COPWerte, COPT, GCCdraw, _temperatures, COPRegression):
        self.processdesignation = processdesignation
        self.grandCompositeCurve = GCCdraw
        self.KoWP = KoWP
        self.EvWP = EvWP
        self.COPWerte = COPWerte
        self.COPT = COPT
        self.Tsinkout = Tsinkout
        self.pyPinch = pyPinch
        self._temperatures = _temperatures
        self.COPRegression = COPRegression
    def drawCOPKo(self):
        self.x = []
        self.y = []
        fig1 = plt.figure()
        for i in self.KoWP[::3]:
            self.x.append(i)
        for i in self.COPWerte[::3]:
            self.y.append(i)
        plt.plot(self.x,self.y)
        plt.grid(True)
        plt.title('COP gegen Qpunkt Ko')#plt.title('Grand Composite Curve')
        plt.xlabel('Qpunkt Ko [kW]')#plt.xlabel('Net Enthalpy Change ∆H (kW)')
        plt.ylabel('COP [-]')#plt.ylabel('Shifted Temperature S (degC)')
    
    def drawGrandCompositeCurve(self):
        grandCompositeCurve = self.grandCompositeCurve
        Tempplus = 0
        self.heatCascade = self.pyPinch.heatCascade
        plt.close('all')
        fig = plt.figure()
        if self.heatCascade[0]['deltaH'] > 0:  
            plt.plot([grandCompositeCurve['H'][0],grandCompositeCurve['H'][1]], [self.grandCompositeCurve['T'][0],self.grandCompositeCurve['T'][1]], 'tab:red')
            plt.plot([grandCompositeCurve['H'][0],grandCompositeCurve['H'][1]], [self.grandCompositeCurve['T'][0],self.grandCompositeCurve['T'][1]], 'ro')
        elif self.heatCascade[0]['deltaH'] < 0:
            plt.plot([grandCompositeCurve['H'][0],grandCompositeCurve['H'][1]], [self.grandCompositeCurve['T'][0],self.grandCompositeCurve['T'][1]], 'tab:blue')
            plt.plot([grandCompositeCurve['H'][0],grandCompositeCurve['H'][1]], [grandCompositeCurve['T'][0],grandCompositeCurve['T'][1]], 'bo')

        for i in range(1, len(self._temperatures)-1):
            if self.heatCascade[i]['deltaH'] > 0:
                plt.plot([grandCompositeCurve['H'][i],grandCompositeCurve['H'][i+1]], [grandCompositeCurve['T'][i],grandCompositeCurve['T'][i+1]], 'tab:red')
                plt.plot([grandCompositeCurve['H'][i],grandCompositeCurve['H'][i+1]], [grandCompositeCurve['T'][i],grandCompositeCurve['T'][i+1]], 'ro')
            elif self.heatCascade[i]['deltaH'] < 0:
                plt.plot([grandCompositeCurve['H'][i],grandCompositeCurve['H'][i+1]], [grandCompositeCurve['T'][i],grandCompositeCurve['T'][i+1]], 'tab:blue')
                plt.plot([grandCompositeCurve['H'][i],grandCompositeCurve['H'][i+1]], [grandCompositeCurve['T'][i],grandCompositeCurve['T'][i+1]], 'bo')
            elif self.heatCascade[i]['deltaH'] == 0 and grandCompositeCurve['H'][i]!=0:
                plt.plot([grandCompositeCurve['H'][i],grandCompositeCurve['H'][i+1]], [grandCompositeCurve['T'][i],grandCompositeCurve['T'][i+1]], 'tab:blue')
                plt.plot([grandCompositeCurve['H'][i],grandCompositeCurve['H'][i+1]], [grandCompositeCurve['T'][i],grandCompositeCurve['T'][i+1]], 'bo')

        plt.plot(self.EvWP[-1],self.COPT[-1],'g^')
        plt.plot(self.KoWP[-1],self.Tsinkout,'g^')
        plt.text(0.94*self.KoWP[-1],0.93*self.Tsinkout,round(self.COPWerte[-1],2))
        plt.grid(True)
        name = self.processdesignation
        plt.suptitle('Großverbundkurve {} °C ({})'.format(round(self.Tsinkout,1),name))#plt.title('Grand Composite Curve')
        plt.title(self.COPRegression)
        plt.xlabel('Nettoenthalpiestromänderung ∆H in kW')#plt.xlabel('Net Enthalpy Change ∆H (kW)')
        plt.ylabel('Verschobene Temperatur in °C')#plt.ylabel('Shifted Temperature S (degC)')
