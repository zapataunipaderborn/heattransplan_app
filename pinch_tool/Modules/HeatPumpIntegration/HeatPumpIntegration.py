from tabulate import tabulate
from Modules.HeatPumpIntegration.HPIPlot import HPIPlot
from Modules.Utility.TemperaturePocketDeletion import TemperaturePocketDeletion as TPD

class HeatPumpIntegration():
    def __init__(self,streamsDataFile, Tsinkout, pyPinch):
        self.Integrationtype = None
        if Tsinkout == None:
            self.Integrationtype = 'Itterativ'
        self.processdesignation = streamsDataFile[:-4]
        self.streamsDataFile = streamsDataFile
        self.options = {'draw', 'debug'}
        self.KoWP = []
        self.EvWP = []
        self.COPwerte = []
        self.COPT = []
        self.SchrittweiteTemp = 0.05
        self.Tsinkout = Tsinkout

        self.pyPinch = pyPinch

    def COP(self,T):
        COPList = []
        StringList = []
        if 144 <= self.Tsinkout <= 212 and 25 <= self.Tsinkout-T <= 190: #Prototypical Stirling
            COPList.append(1.28792 * ((self.Tsinkout-(T)) + 2 * 0.54103)**(-0.37606) * (self.Tsinkout+273 + 0.54103)**0.35992)
            StringList.append('Prototypical Stirling')
        if 80 <= self.Tsinkout <= 160 and 25 <= self.Tsinkout-T <= 95: #VHTHP (HFC/HFO)
            COPList.append(1.9118 * ((self.Tsinkout-(T)) + 2 * 0.04419)**(-0.89094) * (self.Tsinkout+273 + 0.04419)**0.67895)
            StringList.append('VHTHP (HFC/HFO)')
        if 25 <= self.Tsinkout <= 100 and 10 <= self.Tsinkout-T <= 78: #SHP and HTHPs (HFC/HFO)
            COPList.append(1.4480*(10**12) * ((self.Tsinkout-(T)) + 2 * 88.73)**(-4.9469))
            StringList.append('SHP and HTHPs (HFC/HFO)')
        if 70 <= self.Tsinkout <= 85 and 30 <= self.Tsinkout-T <= 75: #SHP and HTHPs (R717)
            COPList.append(40.789 * ((self.Tsinkout-(T)) + 2 * 1.0305)**(-1.0489) * (self.Tsinkout+273 + 1.0305)**0.29998)
            StringList.append('SHP and HTHPs (R717)')
        if len(COPList) == 0:
            COPList.append((self.Tsinkout+273.15)/(self.Tsinkout-T)*0.5) # Carnot
            StringList.append('Carnot')
        return max(COPList),StringList[COPList.index(max(COPList))]
    
    def get_available_heat_pumps(self, T):
        """Returns list of all heat pump types with their COPs and availability status"""
        hp_list = []
        delta_T = self.Tsinkout - T
        
        # Prototypical Stirling
        if 144 <= self.Tsinkout <= 212 and 25 <= delta_T <= 190:
            cop = 1.28792 * ((self.Tsinkout-(T)) + 2 * 0.54103)**(-0.37606) * (self.Tsinkout+273 + 0.54103)**0.35992
            hp_list.append({'name': 'Prototypical Stirling', 'cop': cop, 'available': True, 'reason': ''})
        else:
            hp_list.append({'name': 'Prototypical Stirling', 'cop': None, 'available': False, 
                          'reason': f'Requires: 144°C≤T_sink≤212°C, 25°C≤ΔT≤190°C (Current: T_sink={self.Tsinkout:.1f}°C, ΔT={delta_T:.1f}°C)'})
        
        # VHTHP (HFC/HFO)
        if 80 <= self.Tsinkout <= 160 and 25 <= delta_T <= 95:
            cop = 1.9118 * ((self.Tsinkout-(T)) + 2 * 0.04419)**(-0.89094) * (self.Tsinkout+273 + 0.04419)**0.67895
            hp_list.append({'name': 'VHTHP (HFC/HFO)', 'cop': cop, 'available': True, 'reason': ''})
        else:
            hp_list.append({'name': 'VHTHP (HFC/HFO)', 'cop': None, 'available': False,
                          'reason': f'Requires: 80°C≤T_sink≤160°C, 25°C≤ΔT≤95°C (Current: T_sink={self.Tsinkout:.1f}°C, ΔT={delta_T:.1f}°C)'})
        
        # SHP and HTHPs (HFC/HFO)
        if 25 <= self.Tsinkout <= 100 and 10 <= delta_T <= 78:
            cop = 1.4480*(10**12) * ((self.Tsinkout-(T)) + 2 * 88.73)**(-4.9469)
            hp_list.append({'name': 'SHP and HTHPs (HFC/HFO)', 'cop': cop, 'available': True, 'reason': ''})
        else:
            hp_list.append({'name': 'SHP and HTHPs (HFC/HFO)', 'cop': None, 'available': False,
                          'reason': f'Requires: 25°C≤T_sink≤100°C, 10°C≤ΔT≤78°C (Current: T_sink={self.Tsinkout:.1f}°C, ΔT={delta_T:.1f}°C)'})
        
        # SHP and HTHPs (R717)
        if 70 <= self.Tsinkout <= 85 and 30 <= delta_T <= 75:
            cop = 40.789 * ((self.Tsinkout-(T)) + 2 * 1.0305)**(-1.0489) * (self.Tsinkout+273 + 1.0305)**0.29998
            hp_list.append({'name': 'SHP and HTHPs (R717)', 'cop': cop, 'available': True, 'reason': ''})
        else:
            hp_list.append({'name': 'SHP and HTHPs (R717)', 'cop': None, 'available': False,
                          'reason': f'Requires: 70°C≤T_sink≤85°C, 30°C≤ΔT≤75°C (Current: T_sink={self.Tsinkout:.1f}°C, ΔT={delta_T:.1f}°C)'})
        
        # Carnot (always available)
        cop_carnot = (self.Tsinkout+273.15)/(self.Tsinkout-T)*0.5
        hp_list.append({'name': 'Carnot', 'cop': cop_carnot, 'available': True, 'reason': ''})
        
        return hp_list
    
    def COP_specific(self, T, hp_type):
        """Calculate COP for a specific heat pump type"""
        if hp_type == 'Prototypical Stirling':
            if 144 <= self.Tsinkout <= 212 and 25 <= self.Tsinkout-T <= 190:
                return 1.28792 * ((self.Tsinkout-(T)) + 2 * 0.54103)**(-0.37606) * (self.Tsinkout+273 + 0.54103)**0.35992
        elif hp_type == 'VHTHP (HFC/HFO)':
            if 80 <= self.Tsinkout <= 160 and 25 <= self.Tsinkout-T <= 95:
                return 1.9118 * ((self.Tsinkout-(T)) + 2 * 0.04419)**(-0.89094) * (self.Tsinkout+273 + 0.04419)**0.67895
        elif hp_type == 'SHP and HTHPs (HFC/HFO)':
            if 25 <= self.Tsinkout <= 100 and 10 <= self.Tsinkout-T <= 78:
                return 1.4480*(10**12) * ((self.Tsinkout-(T)) + 2 * 88.73)**(-4.9469)
        elif hp_type == 'SHP and HTHPs (R717)':
            if 70 <= self.Tsinkout <= 85 and 30 <= self.Tsinkout-T <= 75:
                return 40.789 * ((self.Tsinkout-(T)) + 2 * 1.0305)**(-1.0489) * (self.Tsinkout+273 + 1.0305)**0.29998
        # Fallback to Carnot
        return (self.Tsinkout+273.15)/(self.Tsinkout-T)*0.5
        
    def deleteTemperaturePockets(self):
        self.pyPinch = self.pyPinch.PinchAnalyse
        self.hotUtility = self.pyPinch.hotUtility
        self.heatCascade = self.pyPinch.heatCascade
        self._temperatures = self.pyPinch._temperatures
        self.deletedPocketdict = TPD(self.hotUtility, self.heatCascade, self._temperatures).deleteTemperaturePockets()

    def splitHotandCold(self):
        self.splitHotTemperatures = []
        self.splitColdTemperatures = []
        self.splitHotH = []
        self.splitColdH = []
        testHot = 0
        testCold = 0
    
        for i in range(len(self.deletedPocketdict['T'][0])):
            if i >= len(self.deletedPocketdict['deltaH'][0]):
                continue
            if self.deletedPocketdict['deltaH'][0][i] > 0 and testHot == 0:
                    self.splitHotTemperatures.append(self.deletedPocketdict['T'][0][i])
                    self.splitHotH.append(self.deletedPocketdict['H'][0][i])
                    self.splitHotTemperatures.append(self.deletedPocketdict['T'][0][i+1])
                    self.splitHotH.append(self.deletedPocketdict['H'][0][i+1])
                    testHot = 1

            elif self.deletedPocketdict['deltaH'][0][i] > 0 and testHot == 1:
                    self.splitHotTemperatures.append(self.deletedPocketdict['T'][0][i+1])
                    self.splitHotH.append(self.deletedPocketdict['H'][0][i+1])

            elif self.deletedPocketdict['deltaH'][0][i] < 0 and testCold == 0:
                    self.splitColdTemperatures.append(self.deletedPocketdict['T'][0][i])
                    self.splitColdH.append(self.deletedPocketdict['H'][0][i])
                    self.splitColdTemperatures.append(self.deletedPocketdict['T'][0][i+1])
                    self.splitColdH.append(self.deletedPocketdict['H'][0][i+1])
                    testCold = 1
            elif self.deletedPocketdict['deltaH'][0][i] < 0 and testCold == 1:
                    self.splitColdTemperatures.append(self.deletedPocketdict['T'][0][i+1])
                    self.splitColdH.append(self.deletedPocketdict['H'][0][i+1])
            elif self.deletedPocketdict['deltaH'][0][i] == 0:
                    if self.deletedPocketdict['deltaH'][0][i-1] < 0:
                        self.splitColdTemperatures.append(self.deletedPocketdict['T'][0][i+1])
                        self.splitColdH.append(self.deletedPocketdict['H'][0][i+1])

                    elif self.deletedPocketdict['deltaH'][0][i-1] > 0:
                        self.splitHotTemperatures.append(self.deletedPocketdict['T'][0][i+1])
                        self.splitHotH.append(self.deletedPocketdict['H'][0][i+1])
                    else:
                        pass

            else:
                    pass
        
        

        self.splitColddeltaH = []
        self.splitHotdeltaH = []                
        for i in range(len(self.splitColdH)-1):
            self.splitColddeltaH.append(self.splitColdH[i+1]-self.splitColdH[i])

        for i in range(len(self.splitHotH)-1):
            self.splitHotdeltaH.append(self.splitHotH[i+1]-self.splitHotH[i])   
            
        return {'H':self.splitHotH, 'T':self.splitHotTemperatures, 'deltaH':self.splitHotdeltaH},{'H':self.splitColdH, 'T':self.splitColdTemperatures, 'deltaH':self.splitColddeltaH}
    
    def QpunktEv(self,T,Quelle): # FEHLER
        return self.GCCSource['H'][Quelle] + ((self.GCCSource['H'][Quelle+1]-self.GCCSource['H'][Quelle])/(self.GCCSource['T'][Quelle+1]-self.GCCSource['T'][Quelle])) * (T-self.GCCSource['T'][Quelle])
    
    def QpunktKo(self,T,Quelle):
        return self.GCCSink['H'][Quelle-1] + ((self.GCCSink['H'][Quelle-1]-self.GCCSink['H'][Quelle])/(self.GCCSink['T'][Quelle-1]-self.GCCSink['T'][Quelle])) * (T-self.GCCSink['T'][Quelle-1])

    def TKo(self,H,Quelle):
        return self.GCCSink['T'][Quelle] - ((self.GCCSink['T'][Quelle]-self.GCCSink['T'][Quelle+1])/(self.GCCSink['H'][Quelle]-self.GCCSink['H'][Quelle+1])) * (self.GCCSink['H'][Quelle]-H)

    def IntegrateHeatPump(self):
        Test = 0
        TSTest = 0

        #Starttemperatur
        if self.Integrationtype == 'Itterativ':
            self.Tsinkout = self.GCCSink['T'][0]
        else:
            pass
        Quelle = 0
        self.SchrittweiteTemp = (self.GCCSource['T'][Quelle] - self.GCCSource['T'][Quelle+1])/10
        T = self.GCCSource['T'][Quelle]-self.SchrittweiteTemp

        while T > self.GCCSource['T'][-1]:
            if T <= self.GCCSource['T'][Quelle+1]:
                Quelle +=1
                self.SchrittweiteTemp = (self.GCCSource['T'][Quelle] - self.GCCSource['T'][Quelle+1])/10
                T = self.GCCSource['T'][Quelle]-self.SchrittweiteTemp
                if self.GCCSource['deltaH'][Quelle] == 0.0:
                    Quelle +=1
                    self.SchrittweiteTemp = (self.GCCSource['T'][Quelle] - self.GCCSource['T'][Quelle+1])/10
                    T = self.GCCSource['T'][Quelle]-self.SchrittweiteTemp
            if T < self.GCCSource['T'][Quelle+1]:
                T = self.GCCSource['T'][Quelle+1]
            COP = self.COP(T)
            QpunktEv = self.QpunktEv(T,Quelle)
            QpunktKo = QpunktEv * ((1-(1/COP[0]))**(-1))
            self.COPwerte.append(round(COP[0],3))
            self.EvWP.append(round(QpunktEv))
            self.KoWP.append(round(QpunktKo))
            self.COPT.append(T)
            for i in range(len(self.GCCSink['T'])):
                if self.GCCSink['T'][i] <= self.Tsinkout:
                    KoQuelle = i
                    break
            if QpunktKo >= self.QpunktKo(self.Tsinkout, KoQuelle) and self.Integrationtype == None and TSTest == 1 and self.Tsinkout < self.GCCSink['T'][0]:
                break
            if QpunktKo >= self.QpunktKo(self.Tsinkout, KoQuelle) and self.Integrationtype == None and TSTest == 0:
                if self.Tsinkout <= self.GCCSink['T'][0]:
                    T+=self.SchrittweiteTemp
                    self.SchrittweiteTemp = self.SchrittweiteTemp/200
                    TSTest = 1
                else:
                    break
            if QpunktKo >= self.GCCSink['H'][0] and Test == 0:
                T+=self.SchrittweiteTemp
                self.SchrittweiteTemp = self.SchrittweiteTemp/200
                Test = 1
            elif QpunktKo >= self.GCCSink['H'][0] and Test == 1:
                break
            T-=self.SchrittweiteTemp
            if T < self.GCCSource['T'][Quelle+1]:
                T = self.GCCSource['T'][Quelle+1]

            if T <= self.GCCSource['T'][-1]:
                T = self.GCCSource['T'][-1]
                COP = self.COP(T)
                QpunktEv = self.GCCSource['H'][-1]
                QpunktKo = QpunktEv * (1-(1/COP[0]))**(-1)
                if self.Integrationtype == 'Itterativ':
                    for i in range(len(self.GCCSink['H'])):
                        if QpunktKo >= self.GCCSink['H'][i]:
                            QuelleSenke = i-1
                            break
                    self.Tsinkout = self.TKo(QpunktKo,QuelleSenke)
                    COP = self.COP(T)
                    QpunktKo = QpunktEv * (1-(1/COP[0]))**(-1)
                    TSinktest = self.TKo(QpunktKo, QuelleSenke)
                    while abs(self.Tsinkout - TSinktest) >= 1:
                        for i in range(len(self.GCCSink['H'])):
                            if QpunktKo >= self.GCCSink['H'][i]:
                                QuelleSenke = i-1
                                break
                        self.Tsinkout = self.TKo(QpunktKo,QuelleSenke)
                        COP = self.COP(T)
                        QpunktKo = QpunktEv * (1-(1/COP[0]))**(-1)
                        TSinktest = self.TKo(QpunktKo, QuelleSenke)
                
                self.COPwerte.append(COP[0])
                self.EvWP.append(round(QpunktEv))
                self.KoWP.append(round(QpunktKo))
                self.COPT.append(T)
        self.COPRegression = COP[1]
        table = {'COP':self.COPwerte[::30],'QQuelle':self.EvWP[::30],'QSenke':self.KoWP[::30]}
        self.tableISSP = {'Temp': self.COPT, 'COP':self.COPwerte,'QQuelle':self.EvWP,'QSenke':self.KoWP}
        print(tabulate(table,headers='keys'))
        print({'COP':self.COPwerte[-1],'QQuelle':self.EvWP[-1],'QSenke':self.KoWP[-1]})

    def findIntegration(self):#Genaue Integration implementieren!
        self.IntegrationPoint = {'Temp': [], 'COP':[],'QQuelle':[],'QSenke':[]}
        for i in range(len(self.tableISSP['QSenke'])):
            if self.tableISSP['QSenke'][i] >= self.GCCdraw['H'][0]:
                self.IntegrationPoint['Temp'].append(self.tableISSP['Temp'][0]+self.SchrittweiteTemp)
                self.IntegrationPoint['Temp'].append(self.tableISSP['Temp'][i])
                self.IntegrationPoint['COP'].append(self.tableISSP['COP'][i])
                self.IntegrationPoint['QQuelle'].append(self.tableISSP['QQuelle'][i])
                #self.IntegrationPoint['QQuelle'].append(self.tableISSP['QQuelle'][self.tableISSP['Temp'].index(self.IntegrationPoint['Temp'][-1])])
                self.IntegrationPoint['QSenke'].append(self.tableISSP['QSenke'][i])
                break
            else:
                self.IntegrationPoint['Temp'].append(self.tableISSP['Temp'][0]+self.SchrittweiteTemp)
                self.IntegrationPoint['Temp'].append(self.tableISSP['Temp'][-1])
                self.IntegrationPoint['COP'].append(self.tableISSP['COP'][-1])
                self.IntegrationPoint['QQuelle'].append(self.tableISSP['QQuelle'][-1])
                #self.IntegrationPoint['QQuelle'].append(self.tableISSP['QQuelle'][self.tableISSP['Temp'].index(self.IntegrationPoint['Temp'][-1])])
                self.IntegrationPoint['QSenke'].append(self.tableISSP['QSenke'][-1])
                break
    
    def IntegrateHeatPump_specific(self, hp_type):
        """Same as IntegrateHeatPump but uses specific heat pump type"""
        self.selected_hp_type = hp_type
        # Store original COP method
        original_COP = self.COP
        # Replace COP method temporarily
        def COP_wrapper(T):
            cop_val = self.COP_specific(T, hp_type)
            return (cop_val, hp_type) if cop_val else original_COP(T)
        self.COP = COP_wrapper
        # Run integration
        self.IntegrateHeatPump()
        # Restore original method
        self.COP = original_COP

    
    def solveforISSP(self):
        self.GCCdraw = self.pyPinch.solvePinchforHPI().grandCompositeCurve
        self.GCC = self.deleteTemperaturePockets()
        self.IntegrateHeatPump()
        self.findIntegration()
        return self.IntegrationPoint
    
    def HPI(self):
        self.GCCdraw = self.pyPinch.solvePinchforHPI().grandCompositeCurve
        Temperaturesdraw = []
        for i in self.pyPinch.PinchAnalyse._temperatures:
            Temperaturesdraw.append(i)
        self.deleteTemperaturePockets()
        self.GCCSource, self.GCCSink = self.splitHotandCold()
        self.IntegrateHeatPump()
        self.findIntegration()
        HPIPlot(self.streamsDataFile[:-4],self.Tsinkout,self.pyPinch,self.EvWP,self.KoWP, 
                self.COPwerte,self.COPT,self.GCCdraw, Temperaturesdraw, self.COPRegression).drawCOPKo()
        HPIPlot(self.streamsDataFile[:-4],self.Tsinkout,self.pyPinch,self.EvWP,self.KoWP, 
                self.COPwerte,self.COPT,self.GCCdraw, Temperaturesdraw, self.COPRegression).drawGrandCompositeCurve()

