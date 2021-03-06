import numpy
import random
import time
import parameter
import matplotlib.pylab as plt
import scipy.optimize as opt

preferred = parameter.preferredUnits()
preferred.time = 'ms'
preferred.freq = 'kHz'

class toyProtocol(object):
    def __init__(self,q):
        self.q = q
        self.preferred = preferred
    def flatten(self,seed=None):
        parent = self  # for readability
        FT = flatToyProtocol(parent,seed)
        return FT
    def getExperiment(self):  # For subclassing replace this code
        if len(self.q) == 1:
            toy2 = True
            q = parameter.mu(self.q[0],self.preferred.freq)
            q0 = None
            q1 = None
        elif len(self.q) == 2:
            toy2 = False
            q = None
            q0 = parameter.mu(self.q[0],self.preferred.freq)
            q1 = parameter.mu(self.q[1],self.preferred.freq)
        else:
            assert(False) # Length of q should be 1 or 2
        return (toy2,q,q0,q1)

class RNG(random.Random):
    # Inherits all functions from random.Random and adds:
    def setSeed(self,seed=None):   # Added function to remember seed
        if seed == None:
            self.usedSeed = long(time.time()*256)
        else:
            self.usedSeed = seed
        self.resetSeed()
    def resetSeed(self):
        self.seed(self.usedSeed)
   
class Repeated(object):
    def __init__(self, single, rReps):
        self.single = single
        self.rReps = rReps
    def sim(self,nReps=1,clear=False):
        pass
    def simulateOnce(self,RNG=None):
        pass
    def likeOnce(self):
        pass
        
# Goes together: ToySimulator ToyLiker ToyExperiment ToyFlattened
class ToySimulator(object):
    def __init__(self, experiment, seed=None):
        self.initRNG(seed)
        if not experiment==None:
            self.unpack(experiment)
        self.restart()
        self.reveal(False)
    def initRNG(self,seed=None): # Maybe overloaded if using a different RNG, eg rpy2
        self.R = RNG() # RNG is a class
        self.R.setSeed(seed)  # remembers seed that was set
    #def reseed(self,seed=None):  # Clears data and resets RNG with possibly different seed
    #    self.R.setSeed(seed)
    #    self.restart()
    def restart(self):   # Clears data and resets RNG with same seed
        self.R.resetSeed() # Resets RNG with same seed as used before
        self.data = []   # Data used for fitting model. (Each datum may be a tuple)
        self.states = [] # These are the Markov states, including hidden ones.  This model is IID, though.
        self.changedSinceLastSim = False
    def unpack(self,experiment):  # For subclassing replace this code
        self.toy2, self.q, self.q0, self.q1 = experiment
        self.changedSinceLastSim = True
    def sim(self,nReps=1,clear=False): # Only does new reps; keeps old; if (nReps < # Trajs) then does nothing
        if clear:
            self.restart()  # Resets random number generator
        elif self.changedSinceLastSim:
            self.restart()
        numNewReps = nReps - len(self.data)  # Negative if decreasing nReps; if so, nReps updated data unchanged
        for n in range(numNewReps):  
            self.data.append(self.simulateOnce(self.R)) # Don't want to use self.R elsewhere
            if self.revealFlag:
                self.states.append(self.recentState)
        self.nReps = nReps  # Might be decreasing nReps, but code still saves the old results
        self.changedSinceLastSim = False
    def reveal(self, flag=None):
        if flag==True:
            self.revealFlag = True
            self.restart()  # Restart because you need to rerun to save hidden states
        elif flag==False:
            self.revealFlag = False
        return(self.revealFlag)
    def simulateOnce(self,RNG=None):  # Overload
        R = self.getRandom(RNG)  # Pass RNG=self.R to change state of self.R; pass None for a new RNG  
        if self.toy2:
            self.recentState = (R.expovariate(self.q))  # Though not Markovian, we can save the hidden transition times
        else:            
            self.recentState = (R.expovariate(self.q1), R.expovariate(self.q0))
        return sum(self.recentState)
    def getRandom(self,RNG=None):  # Overload if changing RNG eg with rpy2
        if RNG == None:   # RNG == None creates new Random Number Generator and sets seed by time
            R = random.Random()
            R.seed(long(time.time()*256))
            return R       
        else:
            return RNG

class ToyLiker(object):
    def __init__(self, experiment=None):
        if not experiment==None:
            self.unpack(experiment)
        self.restart()
    def restart(self):
        self.likes = []
        self.changedSinceLastLike = False # Don't think I need this; also take out of sim()
    def unpack(self,experiment):  # Overload
        self.toy2, self.q, self.q0, self.q1 = experiment
        self.changedSinceLastLike = True  # Don't think I need this; put in restart() instead
    def likelihoods(self,passedData=None,passedLikes=None):
        if passedData == None:   # Data not passed, so ignore passed Likes (presumably not passed/None)
            data = self.data    # Use cached data
            likes = self.likes  # Append any new likes to cached self.likes
            nLast = self.nReps  # Used to restrict return value to length self.nReps in case nReps is greater than len(likes)
        elif passedLikes==None:  # Data passed, but not Likes
            data = passedData
            likes = []
            nLast = len(data) # Go to end of data, don't restrict
        else:  # both Data and Likes have been passed
            data = passedData
            likes = passedLikes
            nLast = len(data)  # Go to end of data, don't restrict
        nFirst = len(likes)
        for datum in data[nFirst:nLast]:
            likes.append(self.likeOnce(datum))
        return likes[0:nLast]  # Restrict what you return to stopping point
    def likeOnce(self,datum):  # Overload when subclassing
        if not self.datumIntegrity(datum):
            return -numpy.infty
        elif self.toy2:
            return (numpy.log(self.q) - self.q*datum)
        elif self.q0 == self.q1:
            return (numpy.log(self.q1) + numpy.log(self.q0) - self.q0*datum + numpy.log(datum))
        else:
            return (numpy.log(self.q1)+numpy.log(self.q0)+numpy.log((numpy.exp(-self.q0*datum)-numpy.exp(-self.q1*datum))/(self.q1-self.q0)))
    def datumIntegrity(self,datum):
        if not (isinstance(datum,float) or isinstance(datum,int)):
            return False
        elif datum < 0.:
            return False
        elif (not self.toy2) and datum == 0:
            return False
        else:
            return True
    def minuslike(self,data=None):
        L = self.likelihoods(data)
        return -sum(L)       
    def like(self,data=None):
        L = self.likelihoods(data)
        return sum(L)
    def pdf(self,datum):
        return numpy.exp(self.likelihoods([datum])[0])
    def mle(self):
        assert(self.toy2)  # Not yet implemented for toy 3
        return 1./numpy.mean(self.data[0:self.nReps])
    def logf(self,data=None):
        return numpy.matrix(self.likelihoods(data))
    def lr(self,alt):  # likelihood ratio; self is true model
        data = self.data[0:self.nReps]
        return (self.logf(data) - alt.logf(data))
    def lr_mn_sd(self,alt):  # self is true model
        lrs = self.lr(alt)
        mn = numpy.mean(lrs)
        sd = numpy.std(lrs)
        return (mn,sd)
    def lrN(self,alt,N,M):  # add N of them, return M
        self.sim(nReps=N*M)
        lrNM = self.lr(alt)
        L = numpy.reshape(lrNM,(M,N))
        return L.sum(axis=0)
    def aic(self,alt):  # self is true model
        data = self.data[0:self.nReps]
        return 2*(self.logf(data) - alt.logf(data))
    def a_mn_sd(self,alt):  # self is true model
        aics = self.aic(alt)
        mn = numpy.mean(aics)
        sd = numpy.std(aics)
        return (mn,sd)
    def aicN(self,alt,N,M):  # add N of them, return M
        self.sim(nReps=N*M)
        aicNM = self.aic(alt)
        A = numpy.reshape(aicNM,(M,N))
        return A.sum(axis=0)
    def Eflogf(self, data=None):  # NEED TO ADJUST FOR REPEATED EXPERIMENTS (M and N both different from 1)
        return(self.logf(data).mean())
    def Eflogg(self,data):  # Must pass data, don't use self.data
        return self.Eflogf(data)
    
class flatToyProtocol(object):
    def __init__(self, parent, seed=None):
        self.experiment = parent.getExperiment()
        self.simulator = ToySimulator(seed,self.experiment)
        self.liker = ToyLiker(self.experiment)
        self.restart()
        self.reveal(False)  # To save hidden states, call self.reveal(True)
    def reseed(self,seed=None):  # Clears data and resets RNG with possibly different seed
        self.simulator.reseed(seed)
    def restart(self):   # Clears data and resets RNG with same seed
        self.simulator.restart()
        self.liker.restart()
    def changeProtocol(self,experiment=None):
        pass  # For this class, protocol always remains same: measure time of single event
    def changeModel(self,parent):
        self.experiment = parent.getExperiment()
        self.simulator.unpack(self.experiment)
        self.liker.unpack(self.experiment)
    # redirect this function
    # after redirecting reload liker's data, also load nReps into liker
    def sim(self,nReps=1,clear=False): # Only does new reps; keeps old; if (nReps < # Trajs) then does nothing
        self.simulator.sim(nReps,clear)
        self.liker.appendNewData(self.sim.data,self.sim.nReps)
        #if clear:
        #    self.restart()  # Resets random number generator
        #elif self.changedSinceLastSim:
        #    self.restart()
        #numNewReps = nReps - len(self.data)  # Negative if decreasing nReps; if so, nReps updated data unchanged
        #for n in range(numNewReps):  
        #    self.data.append(self.simulateOnce(self.simRNG())) # Don't want to use self.R elsewhere
        #    if self.revealFlag:
        #        self.states.append(self.recentState)
        #self.nReps = nReps  # Might be decreasing nReps, but code still saves the old results
        #self.changedSinceLastSim = False
    # redirect
    def reveal(self, flag=None):
        return self.simulator.reveal(flag)
        #if flag==True:
        #    self.revealFlag = True
        #    self.restart()  # Restart because you need to rerun to save hidden states
        #elif flag==False:
        #    self.revealFlag = False
        #return(self.revealFlag)
    ## remove
    #def simulateOnce(self,RNG=None):  # Overload
    #    R = self.getRandom(RNG)  # Pass RNG=self.simRNG() to change state of self.R; pass None for a new RNG  
    #    if self.toy2:
    #        self.recentState = (R.expovariate(self.q))  # Though not Markovian, we can save the hidden transition times
    #    else:            
    #        self.recentState = (R.expovariate(self.q1), R.expovariate(self.q0))
    #    return sum(self.recentState)
    ## remove
    #def simRNG(self):   # Overload if changing RNG, eg with rpy2
    #    return self.R
    ## remove
    #def getRandom(self,RNG=None):  # Overload if changing RNG eg with rpy2
    #    if RNG == None:   # RNG == None creates new Random Number Generator and sets seed by time
    #        R = random.Random()
    #        R.seed(long(time.time()*256))
    #    else:
    #        R = RNG
    #    return R
    # Change next function so only does liker's data (& liker's nReps) or passed data; if not loaded too bad
    def likelihoods(self,passedData=None,passedLikes=None):
        if passedData == None:  # Data not passed, so ignore passed Likes (presumably not passed/None)
            data = self.data    # Use cached data
            likes = self.likes  # Append any new likes to cached self.likes
            nLast = self.nReps  # Used to restrict return value to length self.nReps in case nReps is greater than len(likes)
        elif passedLikes==None: # Data passed, but not Likes
            data = passedData
            likes = []
            nLast = len(data) # Go to end of data, don't restrict
        else:  # both Data and Likes have been passed
            data = passedData
            likes = passedLikes
            nLast = len(data)  # Go to end of data, don't restrict
        nFirst = len(likes)
        for datum in data[nFirst:nLast]:
            likes.append(self.likeOnce(datum))
        return likes[0:nLast]  # Restrict what you return to stopping point
    def likeOnce(self,datum):  # Overload when subclassing
        if not self.datumIntegrity(datum):
            return -numpy.infty
        elif self.toy2:
            return (numpy.log(self.q) - self.q*datum)
        elif self.q0 == self.q1:
            return (numpy.log(self.q1) + numpy.log(self.q0) - self.q0*datum + numpy.log(datum))
        else:
            return (numpy.log(self.q1)+numpy.log(self.q0)+numpy.log((numpy.exp(-self.q0*datum)-numpy.exp(-self.q1*datum))/(self.q1-self.q0)))
    def datumIntegrity(self,datum):
        if not (isinstance(datum,float) or isinstance(datum,int)):
            return False
        elif datum < 0.:
            return False
        elif (not self.toy2) and datum == 0:
            return False
        else:
            return True
    def minuslike(self,data=None):
        L = self.likelihoods(data)
        return -sum(L)       
    def like(self,data=None):
        L = self.likelihoods(data)
        return sum(L)
    def pdf(self,datum):
        return numpy.exp(self.likelihoods([datum])[0])
    def mle(self):
        assert(self.toy2)  # Not yet implemented for toy 3
        return 1./numpy.mean(self.data[0:self.nReps])
    def logf(self,data=None):
        return numpy.matrix(self.likelihoods(data))
    def lr(self,alt):  # likelihood ratio; self is true model
        data = self.data[0:self.nReps]
        return (self.logf(data) - alt.logf(data))
    def lr_mn_sd(self,alt):  # self is true model
        lrs = self.lr(alt)
        mn = numpy.mean(lrs)
        sd = numpy.std(lrs)
        return (mn,sd)
    def lrN(self,alt,N,M):  # add N of them, return M
        self.sim(nReps=N*M)
        lrNM = self.lr(alt)
        L = numpy.reshape(lrNM,(M,N))
        return L.sum(axis=0)
    def aic(self,alt):  # self is true model
        data = self.data[0:self.nReps]
        return 2*(self.logf(data) - alt.logf(data))
    def a_mn_sd(self,alt):  # self is true model
        aics = self.aic(alt)
        mn = numpy.mean(aics)
        sd = numpy.std(aics)
        return (mn,sd)
    def aicN(self,alt,N,M):  # add N of them, return M
        self.sim(nReps=N*M)
        aicNM = self.aic(alt)
        A = numpy.reshape(aicNM,(M,N))
        return A.sum(axis=0)
    def Eflogf(self, data=None):  # NEED TO ADJUST FOR REPEATED EXPERIMENTS (M and N both different from 1)
        return(self.logf(data).mean())
        #if self.toy2:
        #    return numpy.log(self.q) - self.q*numpy.mean(self.data[0:self.nReps])
        #else:  # toy 3
        #    Qs = []
        #    for n in range(self.nReps):
        #        if self.q1 == self.q0:
        #            Qs.append(-self.q0*self.data[n] + numpy.log(self.data[n]))    
        #        else:
        #            Qs.append(numpy.log((numpy.exp(-self.q0*self.data[n])-numpy.exp(-self.q1*self.data[n]))/(self.q1-self.q0)))
        #            if numpy.isinf(Qs[-1]):
        #                print "q1", self.q1, "q0", self.q0
        #                
        #    Qbar = numpy.mean(Qs)
        #    return numpy.log(self.q1) + numpy.log(self.q0) + Qbar
    def Eflogg(self,data):  # Must pass data, don't use self.data
        return self.Eflogf(data)
        # assert(self.toy2)
        # return numpy.log(self.q) - self.q*numpy.mean(data)  # data passed as parameter: not self.data!
    #def pdfplot(self):
    #    assert(len(self.data)>99)
    #    m = min(self.data)
    #    M = max(self.data)
    #    X = numpy.arange(m,M,(M-m)/100)
    #    Y = []
    #    for x in X:
    #        Y.append(self.pdf(x))
    #    plt.plot(X,Y)
    #    plt.hist(self.data,50,normed=1)
    #    plt.show()

def toy3mlike4opt(q,data):
    for datum in data:
        self.mll -= ad.admath.log(q[1]) + ad.admath.log(q[0])
        self.mll -= ad.admath.log((ad.admath.exp(-q[0]*datum)-ad.admath.exp(-q[1]*datum))/(q[1]-q[0]))
    return self.mll

class likefun(object):
    def __init__(self,parent,paramTuple):
        self.parent = parent
        self.paramTuple = paramTuple
        self.F = self.parent.flatten()
    def set(self,valueTuple):
        for i,P in enumerate(self.paramTuple):
            P.assign(valueTuple[i])
        Ex = self.parent.getExperiment()
        self.F._changeModel(Ex)
        #self.F.changeModel(self.parent)
    def setLog(self,valueTuple):
        for i,P in enumerate(self.paramTuple):
            P.assignLog(valueTuple[i])  # AssignLog so that assigned values can vary from -infty to infty
        Ex = self.parent.getExperiment()
        self.F._changeModel(Ex)
        #self.F.changeModel(self.parent)
    def sim(self,XTrue,nReps=100,seed=None,log=True):
        self.XTrue = XTrue
        if log==True:
            self.setLog(XTrue)
        else:
            self.set(XTrue)
        self.F._reseed(seed)
        self.F.sim(nReps,clear=True)  # clear=True should now be redundant, but kept here for readability
    def minuslike(self,x):
        self.setLog(x)
            #if x[0] < 0. or x[1]<0:
            #    print "x is negative"
            #print "x[0], q[0]", x[0], q0.value
            #print "x[1], q[1]", x[1], q1.value
        return self.F.minuslike()
    def like(self,x,log=True):
        if log==True:
            self.setLog(x)
        else:
            self.set(x)
        return self.F.like()
    
class likefun1(object):   # One dimensional likelihood grid
    def __init__(self,parent,XParam,seed=None):
        self.parent = parent
        self.XParam = XParam
        self.F = self.parent.flatten(seed=seed)
    def setRange(self,XRange):
        self.XRange = XRange
    def set(self,X):
        self.XParam.assign(X)
        Ex = self.parent.getExperiment()
        self.F._changeModel(Ex)
    def sim(self,XTrue=15,nReps=100,seed=None):
        self.XTrue = XTrue
        self.set(XTrue)
        self.F._reseed(seed)
        self.F.sim(nReps,clear=True)   # clear=True should now be redundant, but kept here for readability
    def compute(self):
        self.llikes = []
        for x in self.XRange:
            self.set(x)
            self.llikes.append(self.F.like())
    def plot(self):
        plt.plot(self.XRange,self.llikes)
        plt.show()
    def addVLines(self):
        pass
    def replot(self,XTrue=15,nReps=100,seed=None):
        self.sim(XTrue=XTrue,nReps=nReps,seed=seed)
        self.compute()
        self.plot()

class likefun2(object):   # Two dimensional likelihood grid
    def __init__(self,parent,XParam,YParam):
        self.parent = parent
        self.XParam = XParam
        self.YParam = YParam

q0 = parameter.Parameter("q0",0.5,"kHz",log=True)
q1 = parameter.Parameter("q1",0.25,"kHz",log=True)
q = parameter.Parameter("q",1./6.,"kHz",log=True)
T3 = toyProtocol([q0,q1])
T2 = toyProtocol([q])
FT3 = T3.flatten(seed=3)
FT2 = T2.flatten(seed=3)
XRange = numpy.arange(0.1,30.1,1)
YRange = numpy.arange(0.11,30.11,1)  # Different values so rate constants remain unequal

#One dimensional likelihood plot with toy2 model
#plt.figure()
#LF2 = likefun1(T2,q)
#LF2.setRange(XRange)
#LF2.replot(XTrue=15.,seed=10,nReps=100)

#One-dimensional likelihood plot with toy3 modle
#plt.figure()
#LF3 = likefun1(T3,q0)
#LF3.setRange(XRange)
#LF3.replot(XTrue=15,seed=11,nReps=1000)
LF = likefun(T3,[q0,q1])
LF.sim((1.,2.),nReps=1000,seed=0,log=True)

#Histogram and PDFs
#plt.figure()
#FT3.sim(nReps=1000,clear=True)
#FT3.pdfplot()
#plt.figure()
#FT2.sim(nReps=1000,clear=True)
#FT2.pdfplot()
#plt.figure()
#q0.assign(2.)
#q1.assign(2.)
#FTE = T3.flatten(seed=4)
#FTE.sim(nReps=1000,clear=True)
#FTE.pdfplot()
