import numpy
import parameter
from parameter import u


# A Level is a defined (mean, std) that will be the same across certain Nodes (ie states)
class Level(object):
    def __init__(self, name, mean, std):
        self.name = name
        self.mean = mean
        self.std = std
        self.integrity()  # calls reparameterize()

    def reparameterize(self):
        self.PS = parameter.emptySpace()
        self.PS.append(parameter.getSpace(self.mean))
        self.PS.append(parameter.getSpace(self.std))
        # called by integrity()

    def setMean(self, mean):
        self.mean = mean
        self.integrity()  # calls reparameterize()

    def setStd(self, std):
        self.std = std
        self.integrity()  # calls reparameterize()

    def __repr__(self):
        return '%s\n  Mean %s\n  Std %s' % (self.name, repr(self.mean), repr(self.std))

    def __str__(self):
        #return '%s\n  Mean %s\n  Std %s' % (self.name, str(self.mean), str(self.std))
        return '%s' % (self.name,)

    def integrity(self):
        self.reparameterize()
        assert (isinstance(self.name, basestring))
        assert float(self.std.Value()) >= 0.


# A Node is a state of the channel
class Node(object):
    def __init__(self, name, level):
        self.name = name
        self.level = level
        self.weight = 0.
        self.integrity()

    def setWeight(self, w):
        self.weight = w
        self.integrity()

    def __repr__(self):
        return 'Node %s: %s \n  Weight for initial distribution: %s' % (self.name, repr(self.level), self.weight)

    def __str__(self):
        return '%s' % (self.name,)

    def integrity(self):
        assert (isinstance(self.name, basestring))
        assert (isinstance(self.level, Level))
        assert (self.weight >= 0.)
        assert (not numpy.isinf(self.weight))


# A Channel is a model of an ion channel
class Channel(object):
    def __init__(self, nodes):
        # Define dictionary of nodes
        self.nodes = nodes  # list of nodes, defines order
        self.recordOrder()  # defines nodeOrder dictionary
        self.disconnect()  # QList = 0; calls integrity() which calls reparametrize()

    def timeZeroDistribution(self):
        [n.integrity() for n in self.nodes]
        weights = numpy.array([n.weight for n in self.nodes])
        total = sum(weights)
        if total == 0:  # No weights: use equilibrium distribution
            return None
        else:
            return weights / total  # Weights specified: use normalized weights as distribution

    def clearWeights(self):
        for n in self.nodes:
            n.weight = 0.

    def makeQ(self):
        # make Q with units
        s = len(self.QList[0])  # QList should be square
        Q = numpy.matrix(numpy.zeros([s, s])) / u.millisecond  # QList should be square
        for row in range(s):
            for element in range(s):
                if self.QList[row][element] == 0.:
                    Q[row, element] = 0 / u.millisecond
                else:
                    Q[row, element] = parameter.v(self.QList[row][element])
        # Add diagonal (not zero)
        Qdiag = -Q.sum(axis=1)
        numpy.fill_diagonal(Q, Qdiag)
        return Q

    def makeMean(self):
        return [parameter.v(n.level.mean) for n in self.nodes]  # Records means of nodes (conductances) in list

    def makeStd(self):
        return [parameter.v(n.level.std) for n in self.nodes]  # Records std of nodes (conductances) in list

    def recordOrder(self):
        # Records order of nodes into a dictionary so can reference order by string name
        # Eg returns {'C1':0,'C2':1,'O':2}
        self.nodeOrder = {n.name : i for i, n in enumerate(self.nodes)}

    def getLevels(self):
        return {n.levels for n in self.nodes}  # A set of unique levels

    def getNodeNames(self):
        return {n.name for n in self.nodes}  # Set of unique node names for checking distinctiveness

    def __repr__(self):
        nNodes = len(self.nodes)
        s = 'Channel'
        for l in self.getLevels():
            s += '\n Level: ' + str(l)
        for n in self.nodes:
            s += '\n '
            s += str(n)
        for i in range(0, nNodes - 1):
            for j in range(i + 1, nNodes):
                if self.QList[i][j] == 0. and self.QList[j][i] == 0.:
                    pass
                elif self.QList[j][i] == 0.:
                    s += '\n Edge %s --> %s:\n q (-->) %s' % (
                        self.nodes[i].name, self.nodes[j].name, str(self.QList[i][j]))
                elif self.QList[i][j] == 0:
                    s += '\n Edge %s <-- %s:\n q (<--) %s' % (
                        self.nodes[i].name, self.nodes[j].name, str(self.QList[j][i]))
                else:
                    s += '\n Edge %s <--> %s:\n  q (-->) %s\n  q (<--) %s' % (
                        self.nodes[i].name, self.nodes[j].name, str(self.QList[i][j]), str(self.QList[j][i]))
        s += '\n' + str(self.PS)
        return s

    def padQList(self):
        # Add a new row and column to QList
        newrow = []
        for row in self.QList:
            row.append(0)  # adds new column element by element
            newrow.append(0)  # adds final column
        newrow.append(0)
        self.QList.append(newrow)

    def addNode(self, new):
        self.nodes.append(new)
        self.PS.append(new.level.PS)
        self.recordOrder()
        self.padQList()
        self.integrity()

    # The next three functions define/modify the edges
    def disconnect(self):
        #disconnect() defines a disconnected graph; no transitions
        self.QList = numpy.matrix(numpy.zeros(shape=(len(self.nodes), len(self.nodes)))).tolist()
        self.integrity()  # calls makeQ() and reparameterize()

    def biEdge(self, node1, node2, q12, q21):
        #addBiEdge() modifies parameters of a transition in both directions
        first = self.nodeOrder[node1]
        second = self.nodeOrder[node2]
        self.QList[first][second] = q12  # first row, second column, order reverse in list
        self.QList[second][first] = q21  # second row, first column
        self.integrity()  # calls makeQ() and reparameterize()

    def edge(self, node1, node2, q12):
        #addEdge() modifies parameters of a transition in one direction
        first = self.nodeOrder[node1]
        second = self.nodeOrder[node2]
        self.QList[first][second] = q12
        self.integrity()  # calls makeQ() and reparameterize()

    def reparameterize(self):
        # defines parameter space;  called by integrity()
        self.PS = parameter.emptySpace()  # clear the parameter space
        for n in self.nodes:
            self.PS.append(n.level.PS)  # now recreate the parameter space from just nodes
        for rownum in range(len(self.QList)):
            for element in self.QList[rownum]:
                self.PS.append(parameter.getSpace(element))

    def makeLevelMap(self):
        nonUniqueLevels = []
        for n in self.nodes:
            nonUniqueLevels.append(n.level)
        self.uniqueLevels = list(set(nonUniqueLevels))
        self.levelMap = []
        self.levelNum = []
        for n in self.nodes:
            for u in range(len(self.uniqueLevels)):
                if n.level is self.uniqueLevels[u]:
                    self.levelMap.append(self.uniqueLevels[u])
                    self.levelNum.append(u)
        assert (len(self.levelMap) == len(self.nodes))

    def integrity(self):  # Checks that channel is well defined
        #Nodes
        for n in self.nodes:
            assert (isinstance(n, Node))
        assert (len(self.nodes) == len(self.getNodeNames()))  # makes sure node names are distinct
        assert (len(self.nodes) == len(set(self.nodes)))  # make sure nodes are distinct
        #Edges
        for n in range(len(self.nodes)):
            assert (self.QList[n][n] == 0)
        #Q0 = self.Q.copy()  # Q0 is for checking that off diagonal is positive
        #numpy.fill_diagonal(Q0,0.)  # diagonal is negative so set to zero
        #assert(numpy.amin(Q0)==0)  # now minimum element should be zero (on diagonal)
        #assert(self.Q.shape == (len(self.nodes),len(self.nodes)))
        self.reparameterize()

# This code sets up a canonical channel
# EK,ENa,EL are Hodgkin Huxley values take from http://icwww.epfl.ch/~gerstner/SPNM/node14.html
EK = parameter.Parameter("EK", -12-65, "mV", log=False)
ENa = parameter.Parameter("ENa", 115-65, "mV", log=False)
EL = parameter.Parameter("EL", 10.6-65, "mV", log=False)
# gNa,gK, gL are Hodgkin Huxley values take from http://icwww.epfl.ch/~gerstner/SPNM/node14.html
gNa = parameter.Parameter("gNa", 120, "mS/cm^2", log=True)
gK = parameter.Parameter("gK", 36, "mS/cm^2", log=True)
gL = parameter.Parameter("gL", 0.3, "mS/cm^2", log=True)
# I = gV
# gmax_khh is from www.neuron.yale.edu, but is a density parameter inappropriate for a single channel; use g_open instead
gmax_khh = parameter.Parameter("gmax_khh", 0.02979, "microsiemens", log=True)
# "The single-channel conductance of typical ion channels ranges from 0.1 to 100 pS (picosiemens)."  Bertil Hille (2008), Scholarpedia, 3(10):6051.
# For now, g_open is used only for plotting
g_open = parameter.Parameter("g_open", 1., "picosiemens", log=True)
# gNa_open, gK_open from  Adam Strassber and Louis DeFelice "Limitations of the Hodgkin-Huxley Formalism: Effects of
# single channel kinetics on Transmembrane Voltage Dynamics, Neural Computation 5, 843-855 (1993) PAGE 845
gK_open = parameter.Parameter("gK_open", 20., "picosiemens", log=True)
gNa_open = parameter.Parameter("gNa_open", 20., "picosiemens", log=True)
# The following two parameters were made up (but they are not used at the moment):
gstd_open = parameter.Parameter("gstd_open", 0.1, "picosiemens", log=True)
gstd_closed = parameter.Parameter("gstd_closed", 0.01, "picosiemens", log=True)

# The rest of these parameters come from www.neuron.yale.edu (khh channel) channel builder tutorial
ta1 = parameter.Parameter("ta1", 4.4, "ms", log=True)
tk1 = parameter.Parameter("tk1", -0.025, "1/mV", log=False)
d1 = parameter.Parameter("d1", 21., "mV", log=False)
k1 = parameter.Parameter("k1", 0.2, "1/mV", log=False)

ta2 = parameter.Parameter("ta2", 2.6, "ms", log=True)
tk2 = parameter.Parameter("tk2", -0.007, "1/mV", log=False)
d2 = parameter.Parameter("d2", 43, "mV", log=False)
k2 = parameter.Parameter("k2", 0.036, "1/mV", log=False)

V0 = parameter.Parameter("V0", -65., "mV", log=False)
V1 = parameter.Parameter("V1", 20., "mV", log=False)
V2 = parameter.Parameter("V2", -80., "mV", log=False)
# The parameter VOLTAGE is set by voltage-clamp in patch.py
VOLTAGE = parameter.Parameter("VOLTAGE", -65., "mV", log=False)
OFFSET = parameter.Parameter("OFFSET", 65., "mV", log=False)
VOLTAGE.remap(V0)

vr = parameter.Expression("vr", "VOLTAGE + OFFSET", [VOLTAGE, OFFSET])
tau1 = parameter.Expression("tau1", "ta1*exp(tk1*vr)", [ta1, tk1, vr])
K1 = parameter.Expression("K1", "exp((k2*(d2-vr))-(k1*(d1-vr)))", [k1, k2, d1, d2, vr])
tau2 = parameter.Expression("tau2", "ta2*exp(tk2*vr)", [ta2, tk2, vr])
K2 = parameter.Expression("K2", "exp(-(k2*(d2-vr)))", [k2, d2, vr])

a1 = parameter.Expression("a1", "K1/(tau1*(K1+1))", [K1, tau1])
b1 = parameter.Expression("b1", "1/(tau1*(K1+1))", [K1, tau1])
a2 = parameter.Expression("a2", "K2/(tau2*(K2+1))", [K2, tau2])
b2 = parameter.Expression("b2", "1/(tau2*(K2+1))", [K2, tau2])

Open = Level("Open", mean=g_open, std=gstd_open)
Closed = Level("Closed", mean=0. * u.picosiemens, std=gstd_closed)
C1 = Node("C1", Closed)
C2 = Node("C2", Closed)
O = Node("O", Open)
khh = Channel([C1, C2, O])
khh.biEdge("C1", "C2", a1, b1)
khh.edge("C2", "O", a2)
khh.edge("O", "C2", b2)
