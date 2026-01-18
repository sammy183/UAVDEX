# -*- coding: utf-8 -*-
"""
File dedicated to performance functions

@author: Sammy Nassau
"""

import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.integrate import trapezoid, cumulative_trapezoid, quad
import scipy.integrate as sp 
import matplotlib.pyplot as plt
from tqdm import tqdm
from numba import jit, njit

import uavdex.propulsions as propulsions

lbfN = 4.44822
ftm = 0.3048

#%% Takeoff simulation using initial value problem methods
def SimulateTakeoff(self, aoa_rotation = 10, texpect = 200, results = True, plot = False):
    '''
    ASSUME ROTATION AT 4/5 OF VLOF
    
    aoa rotation is really finicky, ideally figure out what it would be irl and implement
    Assume 10 deg otherwise
    
    h0 = distance of fuselage centerline from ground (meters)
    b = wingspan (m)
    t expect is the expected takeoff time in s
    
    Currently no accounting for takeoff rotation!!
    
    Using: https://digitalcommons.usu.edu/cgi/viewcontent.cgi?article=1080&context=mae_facpub
    For more accurate ground effect predictions for wings with LINEAR TAPER
    
    '''
    print('\nSimulating Ground Roll...')
    # to account for ground effect (phillips + hunsaker correction) at SMALL aoa
    delta_D = 1 - 0.157*(self.taper**0.775 - 0.373)*(self.AR**0.417 - 1.27)
    CDige_oge = 1 - delta_D*(np.e**(-4.74*(self.h0/self.b)**0.814)) - ((self.h0/self.b)**2)*(np.e**(-3.88*(self.h0/self.b)**0.758))
    
    # at SMALL aerodynamic angles of attack
    delta_L = 1 - 2.25*(self.taper**0.00273 - 0.997)*(self.AR**0.717 + 13.6)
    CLige_oge = 1 + delta_L*(288*((self.h0/self.b)**0.787)*(np.e**(-9.14*((self.h0/self.b)**0.327))))/(self.AR**0.882)
    
    # Pre-rotation!
    M = self.MGTOW/9.81 # mass in kg
    
    def T_Dtakeoff(t, V):
        T, _, _, _ = propulsions.ModelCalcs(self, V, t) 
        D = 0.5*self.rho*(V**2)*self.Sw*self.CDtoPreR*CDige_oge
        L = 0.5*self.rho*(V**2)*self.Sw*self.CLtoPreR*CLige_oge
        F = self.mufric*(self.MGTOW-L)
        return((T - D - F)/M)
    
    V0 = [0]
    tspan= [0, texpect]
    
    sol = solve_ivp(T_Dtakeoff, tspan, V0, method = 'RK45', dense_output = True, t_eval=np.linspace(0, texpect, 100000)) #might need to change this if time becomes an issue
    ts = sol.t
    Vs = sol.y[0]
    
    diffs = np.abs(Vs - (5/6)*self.Vlof) # assume rotation at 4/5 Vlof (BIG BIG APPROX)
    rotate = np.argsort(diffs)[:1][0]
    # trotate = ts[rotate]
    xrotate = trapezoid(Vs[:rotate], x=ts[:rotate])
    
    t1 = ts[:rotate]
    V1 = Vs[:rotate]
    d1 = cumulative_trapezoid(V1, x=t1)
    d1 = np.insert(d1, 0, 0.0)
    a1 = Vs[1:rotate]/ts[1:rotate]
    
    # ROTATION phase
    # CLnew = self.CLmax-0.2 #HUGEEEE assumption, this would be changing continuously
    CLnew = self.CLtoPostR # at some deg of rotation with high lift devices
    
    # updated using the high aoa formulations from Phillips and Hunsaker
    Beta_D = 1 + 0.0361*(CLnew**1.21)/((self.AR**1.19)*((self.h0/self.b)**1.51))
    CDige_oge = (1 - delta_D*(np.e**(-4.74*(self.h0/self.b)**0.814)) - ((self.h0/self.b)**2)*(np.e**(-3.88*(self.h0/self.b)**0.758)))*Beta_D
    Beta_L = 1 + 0.269*(CLnew**1.45)
    CLige_oge = (1 + (delta_L*(288*(self.h0/self.b)**0.787)*(np.e**(-9.14*((self.h0/self.b)**0.327))))/(self.AR**0.882))/Beta_L
    
    # assume that the takeoff occurs at 10 deg aoa, and adjust the thrust vector accordingly
    aoa = aoa_rotation #deg
    def T_Dtakeoff(t, V):
        T, _, _, _ = propulsions.ModelCalcs(self, V, t)
        T *= np.cos(aoa*(np.pi/180))
        D = 0.5*self.rho*(V**2)*self.Sw*self.CDtoPostR*CDige_oge
        L = 0.5*self.rho*(V**2)*self.Sw*self.CLtoPostR*CLige_oge + T*np.sin(aoa*(np.pi/180))
        F = self.mufric*(self.MGTOW-L)
        return((T - D - F)/M)
    
    V0 = [V1[-1]]
    tspan= [t1[-1], texpect]
    
    sol = solve_ivp(T_Dtakeoff, tspan, V0, method = 'RK45', dense_output = True, t_eval=np.linspace(t1[-1], texpect, 100000)) #might need to change this if time becomes an issue
    ts = sol.t
    Vs = sol.y[0]
    
    diffs = np.abs(Vs - self.Vlof) # assume rotation at 2/3 Vlof (BIG BIG APPROX)
    liftoff = np.argsort(diffs)[:1][0]
    tlof = ts[liftoff]
    
    t2 = ts[:liftoff]
    V2 = Vs[:liftoff]
    d2 = cumulative_trapezoid(V2, x=t2) + d1[-1]
    d2 = np.insert(d2, 0, d1[-1])
    a2 = Vs[:liftoff]/ts[:liftoff]
    xlof = trapezoid(Vs[:liftoff], x=ts[:liftoff])
    
    t_tot = np.append(t1, t2)
    V_tot = np.append(V1, V2)
    d_tot = np.append(d1, d2)
    a_tot = np.append(a1, a2)
    xlof_tot = xrotate + xlof
    tlof_tot = tlof
    if plot:
        fig, ax1 = plt.subplots(figsize = (6, 4), dpi = 1000)
        
        p1 = ax1.plot(t_tot, V_tot/ftm, color = 'black')
        ax1.set_ylabel('Velocity (ft/s)')
        
        ax2 = ax1.twinx()
        p2 = ax2.plot(t_tot, d_tot/ftm, color = 'red')
        ax2.set_ylabel('Distance (ft)')
        
        ax3 = ax1.twinx()
        p3 = ax3.plot(t_tot[1:], a_tot/ftm, color = 'blue')
        ax3.set_ylabel(r'Acceleration (ft/s$^2$)')
        ax3.spines['right'].set_position(('outward', 60))

        plt.xlabel('Time (s)')
        
        ax1.plot([t2[0], t2[0]], ax1.get_ylim(), '--', color = 'orange', label = 'Rotation')
        
        ax1.yaxis.label.set_color(p1[0].get_color())
        ax2.yaxis.label.set_color(p2[0].get_color())
        ax3.yaxis.label.set_color(p3[0].get_color())

        ax1.grid()
        ax1.minorticks_on()
        ax2.minorticks_on()
        ax3.minorticks_on()
        ax1.legend(loc = 'upper center')
        plt.annotate('Rotation', (1, 1))
        ax1.set_xlabel('Time (s)')
        plt.title(f'Ground Roll, MGTOW = {self.MGTOW/lbfN:.1f} lbf\nVlof = {self.Vlof/ftm:.1f} fps, Vrotate = {V1[-1]/ftm:.1f} ft/s\nDistance = {xlof_tot/ftm:.1f} ft, Time = {tlof_tot:.2f} s')
        plt.show()
    
    if results:
        print('\nGround Roll Calculations:\n'
              f'{"Distance":10} {xlof_tot/ftm:.4f} ft\n'
              f'{"Time":10} {tlof_tot:.4f} s')
    return(tlof_tot, xlof_tot)

#%% The real functions start here!
@njit #DOESN'T WORK BC OF THE TRAPEZOID USAGE!!!, NOW IT DOES!!
def Takeoff(aoa, texpect, h0, taper, AR, b, MGTOW, rho, Sw, CDtoPreR, CLtoPreR, CDtoPostR, CLtoPostR, CLmax, 
            mass, mufric, Vlof, rpm_list, NUMBA_PROP_DATA, CB, ns, Rint, KV, Rm, nmot, I0, ds, takeoffdT, GR, m = 1000, plot = False, results = False):
    '''
    
    Several approximations in this code:
        - the phillips + hunsaker correction is valid for ground affect impact for very small UAVs
        - ***rotation occurs instantaneously at 4/5 of liftoff speed (itself 1.15*Vstall)
        - g = 9.81 m/s^2
        
    '''    
    h = h0
    # to account for ground effect (phillips + hunsaker correction) at SMALL aoa
    delta_D = 1 - 0.157*(taper**0.775 - 0.373)*(AR**0.417 - 1.27)
    CDige_oge = 1 - delta_D*(np.e**(-4.74*(h/b)**0.814)) - ((h/b)**2)*(np.e**(-3.88*(h/b)**0.758))
    
    # at SMALL aerodynamic angles of attack
    delta_L = 1 - 2.25*(taper**0.00273 - 0.997)*(AR**0.717 + 13.6)
    CLige_oge = 1 + delta_L*(288*((h/b)**0.787)*(np.e**(-9.14*((h/b)**0.327))))/(AR**0.882)
    
    
    # timestepping from mission start to rotate velocity assumption
    ts = np.linspace(0.0, texpect, m) # start the mission at 0.0 s
    dt = ts[2]-ts[1]
    
    x = np.zeros(m+1)
    V = np.zeros(m+1)
    SOC = np.zeros(m+1)
    V[0] = 0.0 #initial V (m/s)
    SOC[0] = 1.0 #initial state of charge

    a = np.zeros(m)
    T = np.zeros(m)
    P = np.zeros(m)
    Itot = np.zeros(m)
    Q = np.zeros(m)
    RPM = np.zeros(m)
    eta = np.zeros(m)
    D = np.zeros(m)
    L = np.zeros(m)
    
    endindex = -1
    for i, t in enumerate(ts):
        if SOC[i] < (1-ds):
            endindex = i
            break
        elif V[i] > (4/5)*Vlof: # assume rotation at 4/5 Vlof (BIG BIG APPROX)
            endindex = i
            break
        
        T[i], P[i], Itot[i], RPM[i], Q[i], eta[i] = propulsions.ModelCalcsExternalSOC(V[i], SOC[i], rpm_list, NUMBA_PROP_DATA, CB, ns, Rint, KV, Rm, nmot, I0, ds, takeoffdT, GR)         
        D[i] = 0.5*rho*(V[i]**2)*Sw*CDtoPreR*CDige_oge
        L[i] = 0.5*rho*(V[i]**2)*Sw*CLtoPreR*CLige_oge
        F = mufric*(MGTOW-L[i])
        
        a[i] = (T[i] - D[i] - F)/mass
        
        # PROBLEM: this is derivative based
        V[i+1] = V[i] + a[i]*dt
        x[i+1] = x[i] + V[i]*dt + 0.5*a[i]*(dt**2)
        
        # This is integral based though?
        # SOC[i+1] = (CB*3.6 - trapezoid(Itot[:i], x=ts[:i]))/(CB*3.6)
        SOC[i+1] = SOC[i] - (Itot[i]*dt)/(CB*3.6)
    
    if V[endindex] < (4/5)*Vlof:
        raise ValueError('Aircraft cannot get to rotation velocity!\n\t\t\tDrag, MGTOW, or surface friction must be reduced.')

    # trim arrays
    a = a[:endindex]
    V = V[:endindex]
    x = x[:endindex]
    ts = ts[:endindex]
    T = T[:endindex]
    D = D[:endindex]
    SOC = SOC[:endindex]
    Itot = Itot[:endindex]
    RPM = RPM[:endindex]
    P = P[:endindex]
    Q = Q[:endindex]   
    eta = eta[:endindex]
    
    
    # now simulate post rotation (please don't mention my awful naming conventions)
    
    # updated using the high aoa formulations from Phillips and Hunsaker
    Beta_D = 1 + 0.0361*(CLtoPostR**1.21)/((AR**1.19)*((h/b)**1.51))
    CDige_oge = (1 - delta_D*(np.e**(-4.74*(h/b)**0.814)) - ((h/b)**2)*(np.e**(-3.88*(h/b)**0.758)))*Beta_D
    Beta_L = 1 + 0.269*(CLtoPostR**1.45)
    CLige_oge = (1 + (delta_L*(288*(h/b)**0.787)*(np.e**(-9.14*((h/b)**0.327))))/(AR**0.882))/Beta_L

    ts2 = np.linspace(ts[-1], texpect, m) # start the mission at 0.0 s
    dt2 = ts[2]-ts[1]
    
    x2 = np.zeros(m+1)
    V2 = np.zeros(m+1)
    SOC2 = np.zeros(m+1)

    a2 = np.zeros(m)
    T2 = np.zeros(m)
    P2 = np.zeros(m)
    Itot2 = np.zeros(m)
    Q2 = np.zeros(m)
    RPM2 = np.zeros(m)
    D2 = np.zeros(m)
    L2 = np.zeros(m)
    eta2 = np.zeros(m)
    
    V2[0] = V[-1]      # initial V (m/s)
    SOC2[0] = SOC[-1]  # initial state of charge
    x2[0] = x[-1]
    Itot2[0] = Itot[-1] # also need to do this so SOC doesn't reset to 100!    
    
    endindex = -1
    for i, t in enumerate(ts2):
        if SOC2[i] < (1-ds):
            endindex = i
            
            break
        elif V2[i] > Vlof: # assume rotation at 4/5 Vlof (BIG BIG APPROX)
            endindex = i
            break
        
        T2[i], P2[i], Itot2[i], RPM2[i], Q2[i], eta2[i] = propulsions.ModelCalcsExternalSOC(V2[i], SOC2[i], rpm_list, NUMBA_PROP_DATA, 
                                                 CB, ns, Rint, KV, Rm, nmot, I0, ds, takeoffdT, GR)         
        D2[i] = 0.5*rho*(V2[i]**2)*Sw*CDtoPreR*CDige_oge
        L2[i] = 0.5*rho*(V2[i]**2)*Sw*CLtoPreR*CLige_oge
        F = mufric*(MGTOW-L2[i])
        
        a2[i] = (T2[i] - D2[i] - F)/mass
        
        V2[i+1] = V2[i] + a2[i]*dt2
        x2[i+1] = x2[i] + V2[i]*dt2 + 0.5*a2[i]*(dt2**2)
        SOC2[i+1] = SOC2[i] - (Itot2[i]*dt2)/(CB*3.6)

    if V2[endindex] < Vlof:
        raise ValueError('Aircraft cannot takeoff!\n\t\t\tDrag, MGTOW, or surface friction must be reduced.')

    # trim arrays
    a2 = a2[:endindex]
    V2 = V2[:endindex]
    x2 = x2[:endindex]
    ts2 = ts2[:endindex]
    T2 = T2[:endindex]
    D2 = D2[:endindex]
    SOC2 = SOC2[:endindex]
    Itot2 = Itot2[:endindex]
    RPM2 = RPM2[:endindex]
    P2 = P2[:endindex]
    Q2 = Q2[:endindex]
    eta2 = eta2[:endindex]
        
    # combine (this is so badly done, there MUST be a better way) (could use a list and iterate but whatever)
    a = np.append(a, a2)
    h = np.zeros(a.size) # no altitude gained during ground roll!
    n = np.zeros(a.size) # not calculating load factor for takeoff
    V = np.append(V, V2)
    x = np.append(x, x2)
    ts = np.append(ts, ts2)
    T = np.append(T, T2)
    D = np.append(D, D2)
    SOC = np.append(SOC, SOC2)
    Itot = np.append(Itot, Itot2)
    RPM = np.append(RPM, RPM2)
    P = np.append(P, P2)
    Q = np.append(Q, Q2)
    eta = np.append(eta, eta2)
    
    ############# NOW INITIAL CLIMB ###############
    
    
    
    
    
    
    
    
    
    
    return(a, V, x, h, ts, T, D, n, SOC, Itot, RPM, P, Q, eta)

#%% Cruise
@njit
def Cruise(segment_distance, V_initial, t_initial, SOC_initial, x_initial, h_initial, eta_initial, CL0, CD0, 
           Sw, rho, MGTOW, mass, ds, rpm_list, NUMBA_PROP_DATA, CB, ns, Rint, KV, Rm, nmot, I0, dT, GR, tend = 500, m = 1000):
    '''
    Segment distance in m
    Initial velocity in m/s
    initial time in s
    initial SOC in %/100 
    CL0, CD0 aerodynamic coefs at cruise conditions (usually 0 aoa)
    rho = air density kg/m3
    mass = plane mass in kg
    
    max usable ds is 0.9999 (1.0 breaks the curve!)
    '''
    if segment_distance < 0:
        raise ValueError('Segment Distance < 0')
    
    ts = np.linspace(t_initial, tend, m)
    dt = ts[2]-ts[1]
    
    x = np.zeros(m+1)
    h = np.ones(m+1)*h_initial
    V = np.zeros(m+1)
    a = np.zeros(m)
    T = np.zeros(m)
    P = np.zeros(m)
    Itot = np.zeros(m)
    Q = np.zeros(m)
    eta = np.zeros(m)
    RPM = np.zeros(m)
    D = np.zeros(m)
    n = np.ones(m)
    
    SOC = np.zeros(m+1)
    SOC[0] = SOC_initial #initial state of charge
    V[0] = V_initial #initial V (m/s)
    x[0] = x_initial
    eta[0] = eta_initial
    
    # propulsions.ModelCalcs(self, V[i], t)
    # what if I want to account for changing Itot???
    # realistically I should aim to use RK45 or something 
    # need to handle an error where the input SOC is < 1-ds already!
    # print(SOC_initial)
    # print(SOC[0])
    for i, t in enumerate(ts):
        if SOC[i] < (1-ds):
            endindex = i
            break
        elif x[i]-x_initial > segment_distance:
            endindex = i
            break
        
        # essentially bc CL switches instantaneously between turn and cruise, 
        # for a brief moment the lift created at CL0 is less than MGTOW
        # elif 0.5*rho*(V[i]**2)*Sw*CL0 < MGTOW:
            # print(0.5*rho*(V[i]**2)*Sw*CL0)
            # print(MGTOW)
            # Vstall = np.sqrt((2*MGTOW)/(rho*Sw*CL0))
            # print(Vstall, V[i])
            # raise ValueError('Aircraft too heavy for level flight')
        
        T[i], P[i], Itot[i], RPM[i], Q[i], eta[i] = propulsions.ModelCalcsExternalSOC(V[i], SOC[i], rpm_list, NUMBA_PROP_DATA, 
                                                                              CB, ns, Rint, KV, Rm, nmot, I0, ds, dT, GR) 
        D[i] = 0.5*rho*(V[i]**2)*Sw*CD0
        a[i] = (T[i]-D[i])/mass
        V[i+1] = V[i] + a[i]*dt
        x[i+1] = x[i] + V[i]*dt + 0.5*a[i]*(dt**2)
        SOC[i+1] = SOC[i] - (Itot[i]*dt)/(CB*3.6)
        
    a = a[:endindex]
    V = V[:endindex]
    x = x[:endindex]
    h = h[:endindex]
    ts = ts[:endindex]
    T = T[:endindex]
    D = D[:endindex]
    n = n[:endindex]
    SOC = SOC[:endindex]
    Itot = Itot[:endindex]
    RPM = RPM[:endindex]
    P = P[:endindex]
    Q = Q[:endindex]
    eta = eta[:endindex]
    
    return(a, V, x, h, ts, T, D, n, SOC, Itot, RPM, P, Q, eta)

#%% Climb (essentially cruise but with a theta modifier)
@njit
def Climb(climb_altitude, theta, max_segment_distance, V_initial, t_initial, SOC_initial, x_initial, h_initial, eta_initial, CL0, CD0, 
           Vstall, Sw, rho, MGTOW, mass, ds, rpm_list, NUMBA_PROP_DATA, CB, ns, Rint, KV, Rm, nmot, I0, dT, GR, tend = 500, m = 1000):
    '''
    climb alititude in m
    theta (climb angle) in deg
    h_initial is initial height in m
    
    Assumptions:
        - Start the climb half a meter off the ground (no initial climb modeled)
        - No ground effect corrections implmeented
    
    Should I add altitude to relevant variables? 
    Not really useful here but I think it'll add a lot of versatility, esp with later atmospheric modules
    
    '''
    
    ts = np.linspace(t_initial, tend, m)
    dt = ts[2]-ts[1]
    
    x = np.zeros(m+1)
    V = np.zeros(m+1)
    a = np.zeros(m)
    T = np.zeros(m)
    P = np.zeros(m)
    Itot = np.zeros(m)
    Q = np.zeros(m)
    eta = np.zeros(m)
    RPM = np.zeros(m)
    D = np.zeros(m)
    n = np.zeros(m)
    
    h = np.zeros(m+1) #altitude now
    
    SOC = np.zeros(m+1)
    SOC[0] = SOC_initial #initial state of charge
    V[0] = V_initial #initial V (m/s)
    x[0] = x_initial
    h[0] = h_initial #start half a meter above the ground
    eta[0] = eta_initial
    
    theta = theta*np.pi/180 #convert from deg to rad
    for i, t in enumerate(ts):
        if SOC[i] < (1-ds):
            endindex = i
            break
        elif np.abs(h[i]-h_initial) > climb_altitude:
            endindex = i
            break
        elif x[i]-x_initial > max_segment_distance:
            endindex = i
            break
        
        T[i], P[i], Itot[i], RPM[i], Q[i], eta[i] = propulsions.ModelCalcsExternalSOC(V[i], SOC[i], rpm_list, NUMBA_PROP_DATA, 
                                                                              CB, ns, Rint, KV, Rm, nmot, I0, ds, dT, GR) 
        D[i] = 0.5*rho*(V[i]**2)*Sw*CD0
        # L = 0.5*rho*(V[i]**2)*Sw*CL0
        
        Wuse = mass*9.81*np.sin(theta) # weight at a certain climb angle
        a[i] = (T[i] - D[i] - Wuse)/mass # acceleration along the path
        
        V[i+1] = V[i] + a[i]*dt
        n[i] = np.cos(theta) #n = L/W, in steady climb that's L*cos   #(T[i]/MGTOW)*(L/D[i])

        # if L < MGTOW*np.cos(theta):
        #     print(L)
        #     print(MGTOW)
        #     print(MGTOW*np.cos(theta))
        #     # print((T[i]*np.sin(theta) - D[i]*np.sin(theta) + L*np.cos(theta) - MGTOW)/mass) # ACTUAL acceleration in the y direction
        #     # print(a[i])
        #     raise ValueError('Aircraft cannot climb! Try reducing climb angle or MGTOW.')
        
        x[i+1] = x[i] + V[i]*dt*np.cos(theta) + 0.5*a[i]*(dt**2)*np.cos(theta)
        h[i+1] = h[i] + V[i]*dt*np.sin(theta) + 0.5*a[i]*(dt**2)*np.cos(theta) # does not account for the scenario where L < MGTOW*cos(theta)!
        
        
        # I'm not getting this to work right so we'll keep it simple for now. I think the problem in the descent is that L >> T and D for small aoa
        # IRL you have to reduce throttle to descend right???
        # ay = (T[i]*np.sin(theta) - D[i]*np.sin(theta) + L*np.cos(theta))/mass - 9.81 
        # # if theta < 0:
        # #     print(T[i]*np.sin(theta))
        # #     print(D[i]*np.sin(theta))
        # #     print(L*np.cos(theta))
        # #     print((T[i]*np.sin(theta) - D[i]*np.sin(theta) + L*np.cos(theta))/mass)
        # h[i+1] = h[i] + V[i]*dt*np.sin(theta) + 0.5*ay*(dt**2)
        
        # using specific excess power instead (assumes theta ~= sin(theta), small angle approx)
        # dh_dt = (V[i]/MGTOW)*(T[i]-D[i])
        # h[i + 1] = h[i] + dh_dt*dt
        
        if theta > 0 and h[i+1] <= h[i]:
            raise ValueError('Aircraft cannot climb! Try reducing climb angle or MGTOW.')
        
        # determining acceleration change
        SOC[i+1] = SOC[i] - (Itot[i]*dt)/(CB*3.6)
    
    a = a[:endindex]
    V = V[:endindex]
    x = x[:endindex]
    h = h[:endindex]
    ts = ts[:endindex]
    T = T[:endindex]
    D = D[:endindex]
    n = n[:endindex]
    SOC = SOC[:endindex]
    Itot = Itot[:endindex]
    RPM = RPM[:endindex]
    P = P[:endindex]
    Q = Q[:endindex]
    eta = eta[:endindex]

    return(a, V, x, h, ts, T, D, n, SOC, Itot, RPM, P, Q, eta)


#%% Turn (with bank angle implementation)
def Turn(segment_degrees, nmaxlimit, V_initial, t_initial, SOC_initial, x_initial, h_initial, eta_initial, CLturn, CDturn, 
         Vstall, Sw, rho, MGTOW, mass, ds, rpm_list, NUMBA_PROP_DATA, CB, ns, Rint, KV, Rm, nmot, I0, dT, GR, tend = 15, m = 1000):
    '''
    Assumptions: 
        - Sustained level turns
        - CL/CD at 10 deg aoa
        - g = 9.81 m/s^2
    '''
    g = MGTOW/mass
    
    ts = np.linspace(t_initial, tend, m)
    dt = ts[2]-ts[1]
    
    x = np.zeros(m+1)
    V = np.zeros(m+1)
    a = np.zeros(m)
    T = np.zeros(m)
    P = np.zeros(m)
    Itot = np.zeros(m)
    Q = np.zeros(m)
    eta = np.zeros(m)
    RPM = np.zeros(m)
    D = np.zeros(m)
    h = np.ones(m+1)*h_initial #altitude
    
    # add in load factor to all or no? I say yes
    n = np.zeros(m+1)
    n[0] = 1.0 # from level flight
    deg = np.zeros(m+1)
        
    # specific quantities for turns
    L = np.zeros(m)
    turnrate = np.zeros(m)
    turnradius = np.zeros(m)
    
    SOC = np.zeros(m+1)
    SOC[0] = SOC_initial #initial state of charge
    V[0] = V_initial #initial V (m/s)
    x[0] = x_initial
    h[0] = h_initial #start half a meter above the ground
    n[0] = 1.0 #start from cruise
    eta[0] = eta_initial
    
    for i, t in enumerate(ts):
        if SOC[i] < (1-ds):
            endindex = i
            break
        elif deg[i] > segment_degrees:
            endindex = i
            break
            
        T[i], P[i], Itot[i], RPM[i], Q[i], eta[i] = propulsions.ModelCalcsExternalSOC(V[i], SOC[i], rpm_list, NUMBA_PROP_DATA, 
                                                                              CB, ns, Rint, KV, Rm, nmot, I0, ds, dT, GR) 
        D[i] = 0.5*rho*(V[i]**2)*Sw*CDturn
        L[i] = 0.5*rho*(V[i]**2)*Sw*CLturn
        
        # T/W*L/D assumes the aircraft is not allowed to slow down in turn or lose altitude!! (yet the aircraft DOES lose velocity in the sim)
        # n = L/W for instantaneous (but then how do we model the slowdown or loss in altitude?)
        # how about I just use instantaneous but I also model loss of altitude.
        n[i] = min((T[i]/MGTOW)*(L[i]/D[i]), nmaxlimit) # load factor for sustained turn, pin to nmax if there's a limit
        n[i] = max(n[i], 1.0)
        
        
        ############## NOT CONCLUSIVE WHAT TO DO HERE: REVIEW LATER ##############
        # n[i] = max(L[i]/MGTOW, 1.0) # this essentially forces the aircraft to accelerate if the turn would result in n < 1.0 (i.e. turning directly after a climb)
        # n[i] = min(n[i], nmaxlimit) # cap n at the structural limit!
        
        # Irl you roll to some bank angle which determines your load factor n = 1/cos(phi)
        # but I would like this to work without having to specify bank angle 
        # how do you find the altitude loss without that tho?
        
        # if n[i] < 1:
        #     print(T[i]/MGTOW)
        #     print(L[i]/MGTOW)
        #     print((T[i]/MGTOW)*(L[i]/D[i]))
        #     raise ValueError(f'Load factor of {n[i]:.3f} in sustained turn\n\t\t\tAircraft cannot maintain altitude while turning!')
        
        turnrate[i] = ((g*np.sqrt(n[i]**2 - 1))/V[i])*(180/np.pi) # for some scenario n < 1??
        turnradius[i] = (V[i]**2)/(g*np.sqrt(n[i]**2-1))
        deg[i+1] = deg[i] + turnrate[i]*dt
        
        
        a[i] = (T[i]-D[i])/mass
        V[i+1] = V[i] + a[i]*dt
        x[i+1] = x[i] + V[i]*dt + 0.5*a[i]*(dt**2)
                
        # assume level altitude (for now, accurately calculating climbing turns is my dream but I think it will have to wait for 6DOF)
        # h[i+1] = h[i] + V[i]*dt + 0.5*a[i]*(dt**2)
        
        # determining acceleration change
        SOC[i+1] = SOC[i] - (Itot[i]*dt)/(CB*3.6)
        
    a = a[:endindex]
    V = V[:endindex]
    x = x[:endindex]
    h = h[:endindex]
    ts = ts[:endindex]
    T = T[:endindex]
    D = D[:endindex]
    n = n[:endindex]
    SOC = SOC[:endindex]
    Itot = Itot[:endindex]
    RPM = RPM[:endindex]
    P = P[:endindex]
    Q = Q[:endindex]
    eta = eta[:endindex]
        
    return(a, V, x, h, ts, T, D, n, SOC, Itot, RPM, P, Q, eta) # one little thing up here can mess up everything loll (took 2 hrs at 2 am to debug)
    
    
    
    
    
    
    
    
    
    
    