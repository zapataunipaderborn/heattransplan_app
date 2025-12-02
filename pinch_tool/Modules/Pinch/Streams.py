import csv

class Streams:

    def __init__(self, streamsDataFile):

        self.tmin =              0
        self.numberOf =          0
        self.streamsData =       []

        self._rawStreamsData =   []
        self._index =            0
        self._length =           0




        with open(streamsDataFile, newline='') as f:
            reader = csv.reader(f)
            for row in reader:
                self._rawStreamsData.append(row)

        if (self._rawStreamsData[0][0].strip() != 'Tmin' or
                [ item.strip() for item in self._rawStreamsData[1] ] != ['CP', 'TSUPPLY', 'TTARGET']):
            raise Exception("""\n[ERROR] Bad formatting in streams data file. \n
                    The first two rows of the streams data file should be: \n
                    `` Tmin, <TMIN VALUE> ''
                    `` CP, TSUPPLY, TTARGET ''\n
                    Where CP is the heat capacity (kW / degC);
                    TSUPPLY is the starting temperature of the given stream (degC);
                    TTARGET is the ending temperature of the given stream (degC);\n""")

        self.createStreams()


    def createStreams(self):
        try:
            self.tmin = float(self._rawStreamsData[0][1])
        except ValueError:
            print("\n[ERROR] Wrong type supplied for Tmin in the streams data file. Perhaps used characters?\n")
            raise
        except IndexError:
            print("\n[ERROR] Missing value for Tmin in the streams data file.\n")
            raise
        except:
            print("\n[ERROR] Unexpected error for Tmin. Try using the supplied streams data file format.\n")
            raise


        for rawStream in self._rawStreamsData[2:]:
            try:
                stream = {}

                if float(rawStream[1]) > float(rawStream[2]):
                    stream["type"] = "HOT"
                else:
                    stream["type"] = "COLD"

                stream["cp"] = float(rawStream[0])
                stream["ts"] = float(rawStream[1])
                stream["tt"] = float(rawStream[2])

                self.streamsData.append(stream)

            except ValueError:
                print("\n[ERROR] Wrong number type supplied in the streams data file. Perhaps used characters?\n")
                raise
            except IndexError:
                print("\n[ERROR] Missing number in the streams data file.\n")
                raise
            except:
                print("\n[ERROR] Unexpected error. Try using the supplied streams data file format.\n")
                raise

        self._length = len(self.streamsData)
        self.numberOf = len(self.streamsData)
        if (self._length < 2):
            raise Exception("\n[ERROR] Need to supply at least 2 streams in the streams data file.\n")


    def __iter__(self):
        return self


    def __next__(self):
        if self._index == self._length:
            self._index = 0
            raise StopIteration
        self._index = self._index + 1

        return self.streamsData[self._index - 1]


    def printTmin(self):
        print(self.tmin)


    def printStreams(self):
        for stream in self.streamsData:
            print(stream)


    def printRawStreams(self):
        for rawStream in self._rawStreamsData:
            print(rawStream)