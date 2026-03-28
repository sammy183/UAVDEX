import unittest
from unittest.mock import patch
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import mplcursors

from uavdex import _uavdex_root
from uavdex.common import PointDesign
from uavdex.propulsions import *
from uavdex.utils import open_csv, open_folder
from uavdex.VSPcontribution.atmosphere import stdatm1976 as atm 

class TestInterpolations(unittest.TestCase):
    def test_funcs(self):
        # test 5 propellers, CP, CT funcs for base and numba
        cases = [
            ("14x14", CPBase, 2),
            ("16x10E", CPBase, 2),
            ("18x12E", CPBase, 2),
            ("22x12E", CPBase, 2),
            ("15x10E", CPBase, 2),
            
            ("14x14", CPNumba, 2),
            ("16x10E", CPNumba, 2),
            ("18x12E", CPNumba, 2),
            ("22x12E", CPNumba, 2),
            ("15x10E", CPNumba, 2),
            
            ("14x14", CTBase, 1),
            ("16x10E", CTBase, 1),
            ("18x12E", CTBase, 1),
            ("22x12E", CTBase, 1),
            ("15x10E", CTBase, 1),
            
            ("14x14", CTNumba, 1),
            ("16x10E", CTNumba, 1),
            ("18x12E", CTNumba, 1),
            ("22x12E", CTNumba, 1),
            ("15x10E", CTNumba, 1),
        ]

        def relativeerror(x1, x2):
            '''where x1 is 'truth' '''
            return (np.abs(x1 - x2) / np.abs(x1)) * 100

        def CheckInterpolation(prop_name, func, idx):
            '''
            func = C#Base --> no numba compiling
            func = C#Numba --> numba compiled interp.
            
            idx = 1 --> CT function
            idx = 2 --> CP function
            '''
            COEF_PROP_DATA, numba_prop_data = parse_coef_propeller_data(prop_name)
            rpm_list = np.array(COEF_PROP_DATA['rpm_list'])
            
            # RAW DATA
            Js = numba_prop_data[:, 0, :]
            Cs = numba_prop_data[:, idx, :]
                
            # INTERPOLATED
            # check at each of the raw data points
            Cs_interp = np.zeros(Cs.shape)
            for i, RPM in enumerate(rpm_list):
                Jsspec = Js[i, :]
                for j, J in enumerate(Jsspec):
                    Cs_interp[i, j] = func(RPM, J, rpm_list, numba_prop_data)
            
            # Calculate max error using nonzero data
            mask = Cs != 0.0
            RE = relativeerror(Cs[mask], Cs_interp[mask])
            
            return RE.max()

        for name, func, idx in cases:
            with self.subTest(case=name, function=func.__name__):
                max_error = CheckInterpolation(name, func, idx)
                self.assertLess(max_error, 1e-13)



# class TestSimplifiedRPM(unittest.TestCase):
#     def setUp(self):
#         self.design = PointDesign()
#         # self.design.Motor('C-4130/20', nmot = 2)
#         # self.design.Battery('Gaoneng_8S_3300')
#         # self.design.Prop('16x10E')
#         self.design.Motor('V8110-170', nmot = 1)
#         self.design.Battery('Gaoneng_8S_3300')
#         self.design.Prop('22x12E')
#         # self.design.Prop('27x13E')
        
#     def test_SimplifiedRPMBase_t(self):
#         # from component init
#         args = (self.design.GR, self.design.rpm_list, self.design.COEF_NUMBA_PROP_DATA, self.design.propdiam, 
#                 self.design.ns_batt, self.design.np_batt, self.design.CB, self.design.Rb, self.design.BattType, 
#                 self.design.KV, self.design.Rm, self.design.I0, self.design.nmot, self.design.ds)
#         # input
#         Uinf = 60
#         for Uinf in [10, 30, 50, 70, 90]:
#             dT = 1.0
#             h = 50
#             t = 300
            
#             # from pointresult
#             rho = atm().rho(h)
            
#             # from SimplifiedRPMBase_t
#             eta_c = 0.93
#             GR, rpm_list, coef_numba_prop_data, d, ns, np_batt, CB, Rb, BattType, KV, Rm, I0, nmot, ds = args
#             # Gearing efficiency
#             if GR != 1.0:
#                 eta_g = 0.94 # 94% gear efficiency assumed
#             else:
#                 eta_g = 1.0
                
#             ##### THIS IS THE IMPORTANT PART I WAS MISSING
#             # add "critical check" for infeasible problem
#             # necessary to modify the residual equation such that it will be < 0 when CP = 0.0 (from J > available data)
#             # in theory, the ends of the residual must both be opposite signs? Is this true?
    
#             # IDEA: figure out CP limits (rpm > rpm_list.min(), rpm < rpm_list.max() <-- auto from bisection)
#             # CRITICAL LIMIT: @a specific RPM, J > J.max()
#             # precalculate that limit, then limit max input rpm
#             # if both ends of feasible RPM are same sign, 
#             # infeasible problem bc state exceeds available propeller data 
#             # (often bc propeller cannot create thrust at given RPM, J)
#             Jmax = coef_numba_prop_data[:, 0, :].max()
#             # J = Uinf/((RPM/60)*D)
#             # Uinf/J = (RPM/60)*D
#             # (Uinf*60)/(J*D) = RPM
#             RPMlowerlimit = (Uinf*60)/(Jmax*d) # this provides the LOWER RPM feasibility boundary!!! 
#             # print(RPMlowerlimit) 
            
#             # THE UPPER RPM feasibility limit occurs when SOC = 0!!!
#             # bc then the Voc equation changes dramatically (esp the ^3 and e^x terms)            
            
#             # (Ib*t)/(3.6*CB*np_batt) < 1 
#             # Ib*t < 3.6*CB*np_batt 
#             # Ib < 3.6*CB*np_batt 
#             # ((((rho*((RPM/60)**2)*(d**5)*CPBase(RPM, Uinf/((RPM/60)*d), rpm_list, coef_numba_prop_data))/(2*np.pi*GR*eta_g))*KV*(np.pi/30) + I0)*nmot)/eta_c < 3.6*CB*np_batt 
#             # very nonlinear cannot get a RPMmax limit immediately
#             # hm. Solve 1 residual for SOC = 0?
#             # is it possible that RPMmin from Jmax > RPMlim from SOC = 0?
            
#             # I don't think so, they can just get infinitely close together (no proof though)
#             # this means the SOC == 0 residual should always exist. Solve that first to get RPM bound, and then can determine problem feasibility
            
#             # def SOCresidual(RPM, *args):
#             #     return()
            
#             # let me ask another question. RPM only *drops* when SOC < 0? (FALSE)
#             # therefore can't we just not care about it? YES (WRONG, THE ANSWER IS NO)
            
#             # the point of all this was to immediately check if a propulsion system + flight condition (Uinf, dT, h/rho, Voc/SOC/t) was even feasible
            
#             # if SimpleRPMeqsBase_t(RPMlowerlimit, t, Uinf, dT, rho, eta_c, eta_g, *args)[0] < RPMlowerlimit:
#             #     print('this is infeasible')
            
#             # ok that check is good
#             # STILL a problem can emerge: when SOC = 0 is the trigger for the RPM residual to = 0 (see cobra, 10 m/s case)
#             # this problem is infeasible bc t >>, so battery would be depleted
            
#             # # guess you do need the SOC residual
#             # def SOCresidual(RPM, *args):
#             #     return(SimpleRPMeqsBase_t(RPM, *args)[-1])
#             # RPMupperlimit = bisectionBase(1000, self.design.rpm_list.max(), SOCresidual, t, Uinf, dT, rho, eta_c, eta_g, *args)
#             # print(RPMupperlimit)
#             # # this works great until RPMlowerlimit from the Jmax becomes large enough that SOC does not go to zero at all lol
            
#             # NOTE: when running, I observed that whenever SOCresidual won't coverge,
#             # the first < RPMmin criteria is also satisfied (although sometimes it converges even though the first criteria is satisfied)
            
#             # # New method
#             # if RPMlowerlimit > SimpleRPMeqs_t(RPMlowerlimit, t, Uinf, dT, rho, eta_c, eta_g, *args)[0]:
#             #     print('Advance ratio exceeds data; propeller cannot create thrust')
            
#             # def SOCresidual(RPM, *args):
#             #     return(SimpleRPMeqsBase_t(RPM, *args)[-1])
#             # RPMupperlimit = bisectionBase(RPMlowerlimit, self.design.rpm_list.max(), SOCresidual, t, Uinf, dT, rho, eta_c, eta_g, *args)
            
#             # LHS = SimpleRPMeqs_t(RPMlowerlimit, t, Uinf, dT, rho, eta_c, eta_g, *args)[0] - RPMlowerlimit
#             # RHS = SimpleRPMeqs_t(RPMupperlimit, t, Uinf, dT, rho, eta_c, eta_g, *args)[0] - RPMupperlimit
#             # print(LHS, RHS)
            
#             # if LHS, RHS are different signs and the initial limit was not violated, then the system is feasible!
#             # still, running another residual is NOT worthwhile computationally
#             # what can I do instead?
#             # check left with the criteria
#             # check right after solving with an SOC check
            
#             def residualfunc(RPM, *args):
#                 RPMcalc = SimpleRPMeqsBase_t(RPM, *args)[0]
#                 res = RPMcalc - RPM
#                 return(res)
            
#             n = 1000
#             RPMs = np.linspace(self.design.rpm_list.min(), self.design.rpm_list.max(), n)
#             output = np.zeros(RPMs.size)
            
#             RPMcalcs = np.zeros(RPMs.size)
#             Js = np.zeros(RPMs.size)
#             CPs = np.zeros(RPMs.size)
#             Qms = np.zeros(RPMs.size)
#             Ims = np.zeros(RPMs.size)
#             Ibs = np.zeros(RPMs.size)
#             Vbs = np.zeros(RPMs.size)
#             Vms = np.zeros(RPMs.size)
            
#             for i, RPM in enumerate(RPMs):
#                 RPMcalc, J, CP, Qm, Im, Ib, Vb, Vm = SimpleRPMeqsBase_t(RPM, t, Uinf, dT, rho, eta_c, eta_g, *args)
#                 RPMcalcs[i] = RPMcalc
#                 Js[i] = J 
#                 CPs[i] = CP
#                 Qms[i] = Qm
#                 Ims[i] = Im
#                 Ibs[i] = Ib
#                 Vbs[i] = Vb
#                 Vms[i] = Vm
#                 output[i] = residualfunc(RPM, t, Uinf, dT, rho, eta_c, eta_g, *args)
                
#             plt.figure()
#             plt.plot(RPMs, output)
#             plt.xlabel('RPM')
#             plt.ylabel('Residual Equation Output')
#             plt.grid()
#             plt.show()
            
#             labels = ['RPMcalc', 'J', 'CP', 'Qm', 'Im', 'Ib', 'Vb', 'SOC']
#             plt.figure()
#             for i, var in enumerate([RPMcalcs, Js, CPs, Qms, Ims, Ibs, Vbs, Vms]):
#                 plt.plot(RPMs, var/np.abs(var).max(), label = labels[i])
#             plt.xlabel('RPM')
#             plt.ylabel('Normalized SimpleRPMeqs output')
#             plt.grid()
#             plt.legend()
#             plt.show()

            
#             # # Vbattinit = throttle*3.6*ns
#             # high = rpm_list[-1]
#             # low = rpm_list[0]
#             # RPM = bisectionBase(low, high, residualfunc, t, Uinf, dT, rho, eta_c, eta_g, *args)
        
        
# class TestPointResult(unittest.TestCase):
#     def setUp(self):
#         self.design = PointDesign()
#         # self.design.Motor('C-4130/20', 1)
#         # self.design.Battery('Gaoneng_8S_3300', 0.85)
#         # self.design.Prop('16x10E')
#         self.design.Motor('V8110-170', nmot = 1)
#         self.design.Battery('Gaoneng_8S_3300')
#         self.design.Prop('22x12E')

#     def test_pointresult_variants(self):
#         self.design.PointResult(Uinf = 20, dT = 1.0, h = 50, t = 300) # where propeller is valid but SOC < 1 - ds
#         self.design.PointResult(Uinf = 60, dT = 1.0, h = 50, t = 0) # where propeller cannot make thrust
