from Modules.TotalSiteProfile.TSPPlot  import TSPPlot

class TemperaturePocketDeletion:
    def __init__(self, hotUtility, heatCascade, _temperatures):
        self.hotUtility = hotUtility
        self.heatCascade = heatCascade
        self._temperatures = _temperatures
        self._options = {'draw': True}

    def deleteDoubleEmpty(self,u):
        if u < len(self.heatCascadedeltaH)-2:
            if self.heatCascadedeltaH[u+1] == 0.0 and self.heatCascadedeltaH[u+2] == 0.0:
                self.heatCascadedeltaH.pop(u+1)
                self.heatCascadeexitH.pop(u+2)
                self._temperatures.pop(u+2)

    def deleteTemperaturePockets(self):
            self.deletedPocketdict = {'H': [], 'deltaH': [], 'T': []}
            self.deletedPocketdictlist=[]
            
            i = 0
            j = 0
            k = 0
            u = 0
            plottest = 0
            self.heatCascadedeltaH = []
            self.heatCascadeexitH = []
            self.heatCascadeexitH.append(self.hotUtility)
            
            for o in range(len(self.heatCascade)):
                self.heatCascadedeltaH.append(self.heatCascade[o]['deltaH'])
                self.heatCascadeexitH.append(self.heatCascade[o]['exitH'])

            for i in range(len(self.heatCascadeexitH)-1):
                if self.heatCascadeexitH[i] <= 1e-22:
                    j = i
                    k = i
                    break
            if j == 0 and k == 0:
                if  self.heatCascadeexitH[-1] <= 1e-22:
                    k = len(self.heatCascadeexitH)-1
                    j = len(self.heatCascadeexitH)-1
                    plottest = 1
                elif self.heatCascadeexitH[0] <= 1e-22:
                    j = 0
            while j < len(self.heatCascadeexitH)-1:
                if self.heatCascadedeltaH[j] == 0:
                    j += 1
                
                if j >= len(self.heatCascadedeltaH)-1:
                    break

                if self.heatCascadedeltaH[j] > 0: 
                    if self.heatCascadedeltaH[j + 1] < 0:
                        if abs(self.heatCascadedeltaH[j+1]) < abs(self.heatCascadedeltaH[j]):
                            self._temperatures[j+1] = self._temperatures[j] + ((self._temperatures[j]-self._temperatures[j+1]) / (self.heatCascadeexitH[j] - self.heatCascadeexitH[j+1]))* (self.heatCascadeexitH[j+2])  # lineare regression der Temperatur
                            self.heatCascadedeltaH[j] = self.heatCascadeexitH[j+2] - self.heatCascadeexitH[j]
                            self.heatCascadeexitH[j+1]=self.heatCascadeexitH[j+2]
                            self.heatCascadedeltaH[j+1] = 0.0
                            self.deleteDoubleEmpty(j)
                            if self.heatCascadedeltaH[-1] == 0.0:
                                    self.heatCascadedeltaH.pop()
                                    self._temperatures.pop()
                                    self.heatCascadeexitH.pop()
                                    break
                            j = i
                        elif abs(self.heatCascadedeltaH[j+1]) > abs(self.heatCascadedeltaH[j]):
                            self._temperatures[j+1] = self._temperatures[j+2] + ((self._temperatures[j+1]-self._temperatures[j+2]) / (self.heatCascadeexitH[j+1] - self.heatCascadeexitH[j+2]))* (self.heatCascadeexitH[j] - self.heatCascadeexitH[j+2])  # lineare regression der Temperatur
                            self.heatCascadeexitH[j+1]=self.heatCascadeexitH[j]
                            self.heatCascadedeltaH[j] = 0.0
                            self.deleteDoubleEmpty(j)
                            if self.heatCascadedeltaH[-1] == 0.0:
                                    self.heatCascadedeltaH.pop()
                                    self._temperatures.pop()
                                    self.heatCascadeexitH.pop()
                                    break
                            j=i
                        else:
                            self.heatCascadedeltaH = 0.0
                            self.heatCascadedeltaH.pop(j+1)
                            self.heatCascadeexitH.pop(j+1)
                            self._temperatures.pop(j+1)
                            self.deleteDoubleEmpty(j)
                            if self.heatCascadedeltaH[-1] == 0.0:
                                    self.heatCascadedeltaH.pop()
                                    self._temperatures.pop()
                                    self.heatCascadeexitH.pop()
                                    break
                            j=i
                    elif self.heatCascadedeltaH[j+1] == 0:
                        if self.heatCascadedeltaH[j+2]<0:
                            if abs(self.heatCascadedeltaH[j+2]) > abs(self.heatCascadedeltaH[j]):
                                self._temperatures[j+2] = self._temperatures[j+3] + ((self._temperatures[j+2]-self._temperatures[j+3]) / (self.heatCascadeexitH[j+2] - self.heatCascadeexitH[j+3]))* (self.heatCascadeexitH[j]-self.heatCascadeexitH[j+3])
                                self.heatCascadeexitH[j+2] = self.heatCascadeexitH[j]
                                self.heatCascadedeltaH[j+2] = self.heatCascadedeltaH[j+2] + self.heatCascadedeltaH[j]
                                self._temperatures.pop(j+1)
                                self.heatCascadeexitH.pop(j+1)
                                self.heatCascadedeltaH.pop(j)
                                self.deleteDoubleEmpty(j)
                                if self.heatCascadedeltaH[-1] == 0.0:
                                    self.heatCascadedeltaH.pop()
                                    self._temperatures.pop()
                                    self.heatCascadeexitH.pop()
                                    break
                                j=i
                            elif abs(self.heatCascadedeltaH[j+2]) < abs(self.heatCascadedeltaH[j]):
                                self._temperatures[j+1] = self._temperatures[j+1] - ((self._temperatures[j]-self._temperatures[j+1]) / (self.heatCascadeexitH[j] - self.heatCascadeexitH[j+1]))* (self.heatCascadeexitH[j+1]-self.heatCascadeexitH[j+3])  # lineare regression der Temperatur
                                self.heatCascadeexitH[j+1] = self.heatCascadeexitH[j+3]
                                self.heatCascadeexitH.pop(j+2)
                                self.heatCascadedeltaH[j] = self.heatCascadedeltaH[j] + self.heatCascadedeltaH[j+2]
                                self.heatCascadedeltaH.pop(j+2)
                                self._temperatures.pop(j+2)
                                self.deleteDoubleEmpty(j)
                                if self.heatCascadedeltaH[-1] == 0.0:
                                    self.heatCascadedeltaH.pop()
                                    self._temperatures.pop()
                                    self.heatCascadeexitH.pop()
                                    break
                                j=i
                            else:
                                self.heatCascadedeltaH.pop(j+1)
                                self._temperatures.pop(j+1)
                                self.heatCascadeexitH.pop(j+1)
                                self.heatCascadedeltaH.pop(j+1)
                                self._temperatures.pop(j+1)
                                self.heatCascadeexitH.pop(j+1)
                                self.heatCascadedeltaH[j] = 0.0
                                self.deleteDoubleEmpty(j)
                                if self.heatCascadedeltaH[-1] == 0.0:
                                    self.heatCascadedeltaH.pop()
                                    self._temperatures.pop()
                                    self.heatCascadeexitH.pop()
                                    break
                                j=i
                        else:
                            j+=1
                    else:
                        j += 1
                else:
                    j += 1
            while u < k-1:
                if u >= len(self.heatCascadedeltaH)-1:
                    break
                #unterscheidung einfügen ob u=0
                if self.heatCascadedeltaH[u] > 0 and u == 0:        #löscht nur den obersten, wenn der oberste direkt dran ist      
                    if self.heatCascadedeltaH[u+1] < 0:
                        if abs(self.heatCascadedeltaH[u+1]) > abs(self.heatCascadedeltaH[u]):
                            #kalt größer heiß
                            self._temperatures[u+1] = self._temperatures[u+2] + ((self._temperatures[u+1]-self._temperatures[u+2]) / (self.heatCascadeexitH[u+1] - self.heatCascadeexitH[u+2]))* (self.heatCascadeexitH[u]-self.heatCascadeexitH[u+2])  # lineare regression der Temperatur
                            self.heatCascadedeltaH[u] = self.heatCascadeexitH[u+2] - self.heatCascadeexitH[u]
                            self._temperatures.pop(u)
                            self.heatCascadeexitH.pop(u+1)
                            self.heatCascadedeltaH.pop(u+1)
                            self.deleteDoubleEmpty(u)
                            u = 0
                        elif abs(self.heatCascadedeltaH[u+1]) < abs(self.heatCascadedeltaH[u]):
                            self._temperatures[u+1] = self._temperatures[u] + ((self._temperatures[u+1]-self._temperatures[u]) / (self.heatCascadeexitH[u+1] - self.heatCascadeexitH[u]))* (self.heatCascadeexitH[u+2]-self.heatCascadeexitH[u])  # lineare regression der Temperatur
                            self.heatCascadedeltaH[u] = self.heatCascadeexitH[u] + self.heatCascadeexitH[u+1]
                            self.heatCascadeexitH[u+1] = self.heatCascadeexitH[u+2]
                            self.heatCascadedeltaH[u+1] = 0.0
                            self.deleteDoubleEmpty(u)
                            u = 0
                        else:
                            self._temperatures.pop(u)
                            self.heatCascadeexitH.pop(u)
                            self.heatCascadedeltaH.pop(u)
                            self._temperatures.pop(u)
                            self.heatCascadeexitH.pop(u)
                            self.heatCascadedeltaH.pop(u)
                            u=0
                    elif self.heatCascadedeltaH[u+1] == 0:
                        if self.heatCascadedeltaH[u+2]<0:
                            if abs(self.heatCascadedeltaH[u+2]) > abs(self.heatCascadedeltaH[u]):
                                self._temperatures[u+2] = self._temperatures[u+3] + ((self._temperatures[u+2]-self._temperatures[u+3]) / (self.heatCascadeexitH[u+2] - self.heatCascadeexitH[u+3]))* (self.heatCascadeexitH[u]-self.heatCascadeexitH[u+3])
                                self.heatCascadeexitH[u+2] = self.heatCascadeexitH[u]
                                self.heatCascadedeltaH[u+2] = self.heatCascadedeltaH[u+2] + self.heatCascadedeltaH[u]
                                self._temperatures.pop(u+1)
                                self.heatCascadeexitH.pop(u+1)
                                self.heatCascadedeltaH.pop(u)
                                self.deleteDoubleEmpty(u)
                                self._temperatures.pop(u)
                                self.heatCascadedeltaH.pop(u)
                                self.heatCascadeexitH.pop(u)
                                u=0
                            elif abs(self.heatCascadedeltaH[u+2]) < abs(self.heatCascadedeltaH[u]):
                                self._temperatures[u+1] = self._temperatures[u+1] - ((self._temperatures[u]-self._temperatures[u+1]) / (self.heatCascadeexitH[u] - self.heatCascadeexitH[u+1]))* (self.heatCascadeexitH[u+1]-self.heatCascadeexitH[u+3])  # lineare regression der Temperatur
                                self.heatCascadeexitH[u+1] = self.heatCascadeexitH[u+3]
                                self.heatCascadeexitH.pop(u+2)
                                self.heatCascadedeltaH[u] = self.heatCascadedeltaH[u] + self.heatCascadedeltaH[u+2]
                                self.heatCascadedeltaH.pop(u+2)
                                self._temperatures.pop(u+2)
                                self.deleteDoubleEmpty(u)
                                self._temperatures.pop(u)
                                self.heatCascadedeltaH.pop(u)
                                self.heatCascadeexitH.pop(u)
                                u=0
                            else:
                                self._temperatures.pop(u)
                                self.heatCascadeexitH.pop(u)
                                self.heatCascadedeltaH.pop(u)
                                self._temperatures.pop(u)
                                self.heatCascadeexitH.pop(u)
                                self.heatCascadedeltaH.pop(u)
                                self._temperatures.pop(u)
                                self.heatCascadeexitH.pop(u)
                                self.heatCascadedeltaH.pop(u)
                                u=0
                        else:
                            u+=1
                    else:
                        u += 1
                elif self.heatCascadedeltaH[u] > 0 and u != 0:
                    if self.heatCascadedeltaH[u + 1] < 0:
                        if abs(self.heatCascadedeltaH[u+1]) > abs(self.heatCascadedeltaH[u]):
                            self._temperatures[u+1] = self._temperatures[u+2] + ((self._temperatures[u+1]-self._temperatures[u+2]) / (self.heatCascadeexitH[u+1] - self.heatCascadeexitH[u+2]))* (self.heatCascadeexitH[u]-self.heatCascadeexitH[u+2])  # lineare regression der Temperatur
                            self.heatCascadedeltaH[u+1] = self.heatCascadedeltaH[u+1] + self.heatCascadedeltaH[u]
                            self.heatCascadeexitH[u+1] = self.heatCascadeexitH[u]
                            self.heatCascadedeltaH[u] = 0.0
                            self.deleteDoubleEmpty(u)
                            u = 0
                        elif abs(self.heatCascadedeltaH[u+1]) < abs(self.heatCascadedeltaH[u]):
                            self._temperatures[u+1] = self._temperatures[u] + ((self._temperatures[u+1]-self._temperatures[u]) / (self.heatCascadeexitH[u+1] - self.heatCascadeexitH[u]))* (self.heatCascadeexitH[u+2]-self.heatCascadeexitH[u])  # lineare regression der Temperatur
                            self.heatCascadedeltaH[u] = self.heatCascadeexitH[u] + self.heatCascadeexitH[u+1]
                            self.heatCascadeexitH[u+1] = self.heatCascadeexitH[u+2]
                            self.heatCascadedeltaH[u+1] = 0.0
                            self.deleteDoubleEmpty(u)
                            u = 0 # selbes wie u==0
                        else:
                            self._temperatures.pop(u+1)
                            self.heatCascadeexitH.pop(u+1)
                            self.heatCascadedeltaH[u] = 0.0
                            self.heatCascadedeltaH.pop(u+1)
                            self.deleteDoubleEmpty(u)
                            u=0
                    elif self.heatCascadedeltaH[u + 1] == 0:
                        if self.heatCascadedeltaH[u+2]<0:
                            if abs(self.heatCascadedeltaH[u+2]) > abs(self.heatCascadedeltaH[u]):
                                self._temperatures[u+2] = self._temperatures[u+3] + ((self._temperatures[u+2]-self._temperatures[u+3]) / (self.heatCascadeexitH[u+2] - self.heatCascadeexitH[u+3]))* (self.heatCascadeexitH[u]-self.heatCascadeexitH[u+3])
                                self.heatCascadeexitH[u+2] = self.heatCascadeexitH[u]
                                self.heatCascadedeltaH[u+2] = self.heatCascadedeltaH[u+2] + self.heatCascadedeltaH[u]
                                self._temperatures.pop(u+1)
                                self.heatCascadeexitH.pop(u+1)
                                self.heatCascadedeltaH.pop(u)
                                self.deleteDoubleEmpty(u)
                                u=0
                            elif abs(self.heatCascadedeltaH[u+2]) < abs(self.heatCascadedeltaH[u]):
                                self._temperatures[u+1] = self._temperatures[u+1] - ((self._temperatures[u]-self._temperatures[u+1]) / (self.heatCascadeexitH[u] - self.heatCascadeexitH[u+1]))* (self.heatCascadeexitH[u+1]-self.heatCascadeexitH[u+3])  # lineare regression der Temperatur
                                self.heatCascadeexitH[u+1] = self.heatCascadeexitH[u+3]
                                self.heatCascadeexitH.pop(u+2)
                                self.heatCascadedeltaH[u] = self.heatCascadedeltaH[u] + self.heatCascadedeltaH[u+2]
                                self.heatCascadedeltaH.pop(u+2)
                                self._temperatures.pop(u+2)
                                self.deleteDoubleEmpty(u)
                                u=0
                            else:
                                self._temperatures.pop(u+1)
                                self.heatCascadeexitH.pop(u+1)
                                self._temperatures.pop(u+1)
                                self.heatCascadeexitH.pop(u+1)
                                self.heatCascadedeltaH[u] = 0.0
                                self.heatCascadedeltaH.pop(u+1)
                                self.heatCascadedeltaH.pop(u+1)
                                self.deleteDoubleEmpty(u)
                                u=0
                        else:
                            u+=1
                    else:
                        u+=1
                else:
                    u+=1

            self.deletedPocketdict['H'].append(self.heatCascadeexitH)
            self.deletedPocketdict['deltaH'].append(self.heatCascadedeltaH)
            self.deletedPocketdict['T'].append(self._temperatures)
            self.deletedPocketdictlist.append(self.deletedPocketdict)

            if self._options['draw'] == True:
                TSPPlot.drawDeletedCurve(self, self.heatCascadedeltaH, self.deletedPocketdict, self._temperatures, plottest)

            return self.deletedPocketdict