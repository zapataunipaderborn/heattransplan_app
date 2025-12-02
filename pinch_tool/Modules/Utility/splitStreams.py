

class splitStreams():
    def __init__(self, deletedPocketdict,splitdict):
        self.deletedPocketdict = deletedPocketdict
        
        self.splitdict = splitdict

    def splitHotandCold(self):
        self.splitHotTemperatures = []
        self.splitColdTemperatures = []
        self.splitHotH = []
        self.splitColdH = []
        testHot = 0
        testCold = 0
    
        for i in range(len(self.deletedPocketdict['T'])):
            for j in range(len(self.deletedPocketdict['T'][i])):
                if j >= len(self.deletedPocketdict['deltaH'][i]):
                    continue
                if self.deletedPocketdict['deltaH'][i][j] > 0 and testHot == 0:
                    self.splitHotTemperatures.append(self.deletedPocketdict['T'][i][j])
                    self.splitHotH.append(self.deletedPocketdict['H'][i][j])
                    self.splitHotTemperatures.append(self.deletedPocketdict['T'][i][j+1])
                    self.splitHotH.append(self.deletedPocketdict['H'][i][j+1])
                    testHot = 1

                elif self.deletedPocketdict['deltaH'][i][j] > 0 and testHot == 1:
                    if j == len(self.deletedPocketdict['deltaH'][i])-1:
                        self.splitHotTemperatures.append(self.deletedPocketdict['T'][i][j+1])
                        self.splitHotH.append(self.deletedPocketdict['H'][i][j+1])
                    elif self.deletedPocketdict['deltaH'][i][j+1] < 0:
                        self.splitHotTemperatures.append(self.deletedPocketdict['T'][i][j])
                        self.splitHotH.append(self.splitHotH[-1])
                        self.splitHotTemperatures.append(self.deletedPocketdict['T'][i][j+1])
                        self.splitHotH.append(self.splitHotH[-1] + self.deletedPocketdict['deltaH'][i][j])# Anpassen
                    else:
                        self.splitHotTemperatures.append(self.deletedPocketdict['T'][i][j+1])
                        self.splitHotH.append(self.deletedPocketdict['H'][i][j+1])

                elif self.deletedPocketdict['deltaH'][i][j] < 0 and testCold == 0:
                    self.splitColdTemperatures.append(self.deletedPocketdict['T'][i][j])
                    self.splitColdH.append(self.deletedPocketdict['H'][i][j])
                    self.splitColdTemperatures.append(self.deletedPocketdict['T'][i][j+1])
                    self.splitColdH.append(self.deletedPocketdict['H'][i][j+1])
                    testCold = 1
                elif self.deletedPocketdict['deltaH'][i][j] < 0 and testCold == 1:
                    if j == len(self.deletedPocketdict['deltaH'][i])-1:
                        if self.splitColdH[-1] < 0:
                            self.splitColdTemperatures.append(self.deletedPocketdict['T'][i][j+1])
                            self.splitColdH.append(self.deletedPocketdict['deltaH'][i][j] + self.splitColdH[-1])
                        else:
                            self.splitColdTemperatures.append(self.deletedPocketdict['T'][i][j+1])
                            self.splitColdH.append(self.deletedPocketdict['H'][i][j+1])
                    elif self.deletedPocketdict['deltaH'][i][j+1] > 0 or self.deletedPocketdict['deltaH'][i][j-1]:
                        self.splitColdTemperatures.append(self.deletedPocketdict['T'][i][j])
                        self.splitColdH.append(self.splitColdH[-1])
                        self.splitColdTemperatures.append(self.deletedPocketdict['T'][i][j+1])
                        self.splitColdH.append(self.deletedPocketdict['deltaH'][i][j] + self.splitColdH[-1])# Anpassen
                    else:
                        if self.splitColdH[-1] < 0:
                            self.splitColdTemperatures.append(self.deletedPocketdict['T'][i][j+1])
                            self.splitColdH.append(self.deletedPocketdict['deltaH'][i][j] + self.splitColdH[-1])
                        else:
                            self.splitColdTemperatures.append(self.deletedPocketdict['T'][i][j+1])
                            self.splitColdH.append(self.deletedPocketdict['H'][i][j+1])
                elif self.deletedPocketdict['deltaH'][i][j] == 0:
                    if self.deletedPocketdict['deltaH'][i][j-1] < 0:
                        self.splitColdTemperatures.append(self.deletedPocketdict['T'][i][j+1])
                        self.splitColdH.append(self.deletedPocketdict['H'][i][j+1])

                    elif self.deletedPocketdict['deltaH'][i][j-1] > 0:
                        self.splitHotTemperatures.append(self.deletedPocketdict['T'][i][j+1])
                        self.splitHotH.append(self.deletedPocketdict['H'][i][j+1])
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

        self.splitHotTemperatures
        #self.splitHotH.sort(reverse=True)
        self.splitHotdeltaH
        self.splitColdTemperatures
        self.splitColdH
        self.splitColddeltaH

        self.splitdict['HotTemperatures'].append(self.splitHotTemperatures)
        self.splitdict['HotH'].append(self.splitHotH)
        self.splitdict['HotdeltaH'].append(self.splitHotdeltaH)
        self.splitdict['ColdTemperatures'].append(self.splitColdTemperatures)
        self.splitdict['ColdH'].append(self.splitColdH)
        self.splitdict['ColddeltaH'].append(self.splitColddeltaH)

        return self.splitdict