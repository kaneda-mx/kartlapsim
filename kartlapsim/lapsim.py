# -*- coding: utf-8 -*-
"""
Created on Wed Apr  3 11:57:22 2019

@author: Sven van Koutrik
"""
import numpy as np
import matplotlib.pyplot as plt
from itertools import chain
from scipy.optimize import brentq 
import kartlapsim.utils.constants as constants


class Lapsim:
    def __init__(self, kartobj=None,trackobj=None):
        
        self.kart=kartobj
        self.track=trackobj
        self.idxApex = None
        self.vApex = None
        self.x = State() #state obj
        self.xvec = np.zeros([len(vars(self.x)),1])
        self.xvecchans = vars(self.x).keys()
        self.laptime = None
    
    
    def simulate(self):
        self.kart.ini()
        self.calcapexes()
        self.calcfwdbwd()
            
        
    def calcapexes(self):
        #todo:exception if no kart or track defined
        vApexSol  = np.sqrt(self.kart.aymax/ np.abs(self.track.curv) )
        dvApexSol = np.gradient(vApexSol,axis=0)*vApexSol
        
        axApexSol = np.zeros_like(vApexSol)
        for i in range(len(vApexSol)):
            self.x.ay=self.kart.aymax
            self.x.v=vApexSol[i]
            axApexSol[i] = self.calcDrag()/self.kart.m #replace by calcAx and the actual ay in the more general case(max ay at nonzero fxtyre)

        idxApex = np.flatnonzero(np.diff(np.sign(dvApexSol-axApexSol),axis=0))+1 #apex def: intersection of ax at max ay with gradient of v for max ay
        self.vApexSol = vApexSol
        self.idxApex  = idxApex
        self.vApex    = vApexSol[idxApex]
        

    def calcfwdbwd(self):
        idxApexSlowest=np.argmin(self.vApex) #start at slowest point
        idxSlowestPoint=self.idxApex[idxApexSlowest]

        vfwd = np.zeros_like(self.track.s) #allocate fw and bw calculated speeds
        vbwd = np.zeros_like(vfwd) 
        xvecfwd = np.zeros( (len(vars(self.x)),len(self.track.s)) )
        xvecbwd = np.zeros_like(xvecfwd)
        vfwd[idxSlowestPoint] = self.vApex[idxApexSlowest]
        vbwd[idxSlowestPoint] = self.vApex[idxApexSlowest]
        
        for i in chain( range(idxSlowestPoint+1,len(self.track.s)) , range(idxSlowestPoint)): 
            j= (2*idxSlowestPoint-i) % len(self.track.s) #reverse order bwd
            jn = (j+1) % len(self.track.s) #to make it circular
            
            vfwd[i]=self.QSSstep(vfwd[i-1],i,i-1,1)
            xvecfwd[:,i]= np.transpose(self.xvec)  #log state vector
            vbwd[j]=self.QSSstep(vbwd[jn],j,jn,-1)
            xvecbwd[:,j]= np.transpose(self.xvec)  #log state vector
                     
        self.vfwd=vfwd
        self.vbwd=vbwd
        
        self.vqss = np.minimum(vfwd,vbwd)  #pick correct speed
        self.xsol = np.where(vfwd<vbwd, np.transpose(xvecfwd) , np.transpose(xvecbwd) ) #pick correct statevector
        self.laptime = np.sum(self.track.ds / self.vqss)
                
    def QSSstep(self,vprev,idx,idxprev,direction):
        axprev = (self.calcAx(direction,vprev,idxprev) + self.track.axIncl[idx])*direction #include inclination
        vnew = vprev + (axprev/vprev)*(self.track.ds[idxprev])
        vnew = min(vnew,self.vApexSol[idx],self.kart.vmax)
        return vnew          

    def calcAx(self,direction,v,idx): #does not handle arrays because of brentq
        #direction==1: accel. direction==-1: braking
        
        #calc 'state' from v and curv
        self.x.direction = direction
        self.x.v   = v
        self.x.ay  = v**2*abs(self.track.curv[idx])
        self.x.rw  = self.rwdyn()
        self.x.fac = (direction==1)*self.kart.fxmax  +  (direction==-1)*self.kart.fxmin
        self.x.fxtyres = self.frictionEllipse()  #call friction circle(dep on direction
        self.x.fxdrag  = self.calcDrag()
        self.x.vow = v*(1+0.5*self.kart.T*abs(self.track.curv[idx])) #outside wheel 
               
        #solve PT force (unknown is RPM because of slip)
        nmin = self.x.v/self.x.rw
        nmax = self.x.vow*(1+self.kart.sxmax)/self.x.rw
        self.x.nAxle = brentq( self.errornAxle ,nmin,nmax) 
        #self.x.nAxle =  v/self.x.rw #assume no slip
        
        self.x.fxPT = self.calcFxPT(self.x.nAxle)
        ax = (np.minimum(self.x.fxtyres,self.x.fxPT) - self.x.fxdrag)/self.kart.m #add various drag components
        
        statevars = vars(self.x)
        #numpy >=1.24 no longer builds an object array from a ragged sequence:
        #the state mixes scalars with size-1 arrays, so flatten explicitly what
        #numpy <=1.23 coerced implicitly. Logging only, no effect on dynamics.
        np.put(self.xvec, range(len(statevars)) , [np.ravel(v)[0] for v in statevars.values()] )
        
        return ax
    

    def frictionEllipse(self): 
        return np.sqrt(1- np.minimum((self.x.ay/self.kart.aymax)**2,1) )*self.x.fac #fx
    
    def rwdyn(self): return  self.kart.rw*(1 - self.kart.rwAyCoeff*abs(self.x.ay/self.kart.aymax))

    def calcDrag(self): #handles & returns arrays
        #slip angle drag
        beta=np.radians(self.kart.betamax*np.arcsin( np.minimum( np.abs(self.x.ay/self.kart.aymax) ,1) )/(np.pi/2)) #slip angle
        fxdragslip = self.kart.m*np.abs(self.x.ay)*np.sin(beta)
        
        #aero & rolling resistance
        fxdragroll = self.kart.m*constants.g*self.kart.croll 
        fxdragaero = 0.5*self.kart.rho_air*self.kart.cxa*self.x.v**2
        
        return fxdragslip + fxdragroll + fxdragaero
    
    
    def errornAxle(self,nAxle):
        fx      = self.calcFxPT(nAxle) #first solve what would fx be at this rpm?
        sx      = self.calcSxTyres(fx)  #then solve what would slip be at this fx        
        nAxlesol = self.x.vow*(1+sx)/self.x.rw #corresponding nAxle
        return (nAxle - nAxlesol)
    
    def calcFxPT(self,nAxle):    
        T = np.interp(nAxle,self.kart.nAxlePT,self.kart.TAxlePT)
        return T/self.x.rw #return fxPT
    
    def calcSxTyres(self,fx): 
        #basic inverse tyre model (TmEasy combined, sin(quad slip arg))
        fxn = np.minimum(fx / self.kart.fxmax,1)
        fyn = np.minimum(self.x.ay / self.kart.aymax,1)
        fn = np.minimum(np.sqrt(fxn**2 + fyn**2),1)
        sxn = fxn * np.arcsin(fn)/(np.pi/2)/fn        
        return sxn*self.kart.sxmax
        

class State:
    def __init__(self): 
        self.direction = None
        self.v = None
        self.ay = None
        self.rw = None   
        self.fac = None
        self.fxtyres = None
        self.fxPT = None
        self.fxdrag = None
        self.vow = None
        self.nAxle = None
        
