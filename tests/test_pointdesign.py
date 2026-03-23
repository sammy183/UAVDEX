import unittest

from uavdex.common import PointDesign
from uavdex.propulsions import propQnames
import numpy as np

class TestComponentInits(unittest.TestCase):
    '''Test component initialization!'''
    def setUp(self):
        self.design = PointDesign()

    def test_component_imports(self):
        cases = [
            ("motor", lambda d: d.Motor('C-4130/20', 1)),
            ("battery", lambda d: d.Battery('Gaoneng_8S_3300', 0.85)),
            ("propeller", lambda d: d.Prop('16x12E')),
        ]

        for name, func in cases:
            with self.subTest(component=name):
                func(self.design)

    def test_fullsetup_import(self):
        self.design.Motor('C-4130/20', 1)
        self.design.Battery('Gaoneng_8S_3300', 0.85)
        self.design.Prop('16x12E')
        self.design.ViewSetup()
        

# #### BUILD OUT TO CHECK IF IT COULD OPEN DATABSE SHEETS WITHOUT ACTUALLY OPENING THE FILES
# class TestDatabaseAccess(unittest.TestCase):
#     def test_motor_sheet(self):
#         t = PointDesign()
#         # t.OpenMotorData()
#         # t.OpenBatteryData()
        
class TestPointResult(unittest.TestCase):
    def setUp(self):
        self.design = PointDesign()
        self.design.Motor('C-4130/20', 1)
        self.design.Battery('Gaoneng_8S_3300', 0.85)
        self.design.Prop('16x12E')

    def test_pointresult_variants(self):
        cases = [
            {"h": 50,       "SOC": 1.0},
            {"h": 50,       "Voc": 3.8},
            {"h": 50,       "t": 30},
            {"rho": 1.225,  "SOC": 1.0},
            {"rho": 1.225,  "Voc": 3.8},
            {"rho": 1.225,  "t": 30},
        ]
        precomputed_results = [
            np.array([32.076872, 1.181077, 6348.820686, 0.359946, 0.61275, 1.0, 0.905153, 0.651, 0.996898, 785.235288, 867.517082, 1332.591524, 82.281794, 465.074442, 4.146395, 37.874621, 40.725399, 40.725399, 22.904971, 32.721387, 32.721387, 4.1029, 0.999023]),
            np.array([26.912846, 1.023201, 5911.193848, 0.375205, 0.637362, 1.0, 0.906917, 0.651, 0.997089, 633.380497, 698.388336, 1072.793143, 65.007839, 374.404807, 3.13153, 32.914801, 35.392259, 35.392259, 21.218064, 30.311519, 30.311519, 3.8, 0.492188]),
            np.array([30.583908, 1.135712, 6226.289511, 0.364167, 0.619524, 1.0, 0.905706, 0.651, 0.996952, 740.50203, 817.596751, 1255.908988, 77.094721, 438.312237, 3.84022, 36.449454, 39.192961, 39.192961, 22.430974, 32.044249, 32.044249, 4.017779, 0.901028]),
            np.array([32.204118, 1.18594, 6346.626043, 0.359922, 0.61287, 1.0, 0.904926, 0.651, 0.996886, 788.195786, 871.005367, 1337.949873, 82.809581, 466.944506, 4.179913, 38.027392, 40.889669, 40.889669, 22.904683, 32.720976, 32.720976, 4.1029, 0.999023]),
            np.array([27.020699, 1.027461, 5909.272909, 0.375183, 0.63747, 1.0, 0.906721, 0.651, 0.997078, 635.81112, 701.219975, 1077.142819, 65.408855, 375.922844, 3.15705, 33.048647, 35.53618, 35.53618, 21.217812, 30.31116, 30.31116, 3.8, 0.492188]),
            np.array([30.700309, 1.14024, 6223.739386, 0.364159, 0.619666, 1.0, 0.90549, 0.651, 0.996939, 743.149432, 820.715397, 1260.699534, 77.565965, 439.984137, 3.870249, 36.591685, 39.345897, 39.345897, 22.429014, 32.041448, 32.041448, 4.017477, 0.900642])
            ] 

        total_tested = 0
        for i, case in enumerate(cases):
            with self.subTest(case=case):
                data = self.design.PointResult(
                    Uinf=15,
                    dT=0.7,
                    verbose=False,
                    **case
                )
                # print(repr([float(f"{a:.6f}") for a in data]))
                for j, value in enumerate(data):
                    self.assertEqual(precomputed_results[i][j], round(value, 6), f"PointResult case {i}, value {j} does not match precomputed")
                    total_tested += 1
        # print(f"Tested {total_tested} PointResult values")
        
class TestLinePlot(unittest.TestCase):
    def setUp(self):
        self.design = PointDesign()
        self.design.Motor('C-4130/20', nmot = 2)
        self.design.Battery('Gaoneng_8S_3300')
        self.design.Prop('16x10E')
        # self.design.Motor('V8110-170', nmot = 1)
        # self.design.Battery('Gaoneng_8S_3300')
        # self.design.Prop('22x12E')
    
    def test_lineplot_varients(self):
        # # TODO: figure out how to get the range automatically so ppl don't have to input
        # self.design.LinePlot(propQ = 'Pw_c', 
        #              Uinf = np.linspace(0, 40, 100), 
        #              dT = 0.5, 
        #              h = 10, 
        #              SOC = 1.0, 
        #              plot = True)
        
        n = 50
        plot = False
        cases = [
            {"propQ":'eta_drive',   "Uinf":np.linspace(0, 40, n), "dT":0.5, "h": 10, "SOC": 1.0, "plot":plot},
            {"propQ":'T',           "Uinf":np.linspace(0, 40, n), "dT":0.5, "h": 10, "SOC": 1.0, "plot":plot},
            {"propQ":'eta_drive',   "Uinf":25, "dT":np.linspace(0.3, 1.0, n), "h": 10, "SOC": 1.0, "plot":plot},
            {"propQ":'eta_drive',   "Uinf":25, "dT":np.linspace(0.3, 1.0, n), "h": 10, "t": 0.0, "plot":plot}, # case for SimplifiedRPM_t
            # {"propQ":'eta_p', "Uinf":25, "dT":np.linspace(0.3, 1.0, n), "h": 10, "SOC": 1.0, "plot":True},
            # {"propQ":'eta_m', "Uinf":25, "dT":np.linspace(0.3, 1.0, n), "h": 10, "SOC": 1.0, "plot":True},
            # {"propQ":'eta_c', "Uinf":25, "dT":np.linspace(0.3, 1.0, n), "h": 10, "SOC": 1.0, "plot":True},
        ]
        
        for i, case in enumerate(cases):
            with self.subTest(case=case):
                self.design.LinePlot(
                    verbose=False,
                    **case
                )
                
class TestContourPlot(unittest.TestCase):
    def setUp(self):
        self.design = PointDesign()
        # self.design.Motor('C-4130/20', nmot = 2)
        # self.design.Battery('Gaoneng_8S_3300')
        # self.design.Prop('16x10E')
        self.design.Motor('V8110-170', nmot = 1)
        self.design.Battery('Gaoneng_8S_3300')
        self.design.Prop('22x12E')
    
    def test_contourplot_varients(self):
        n = 50
        plot = False
        cases = [
            {"propQ":'eta_drive', 
             "xaxis":"t", "yaxis":"Uinf", 
             "Uinf":np.linspace(0, 30, n), "t": np.linspace(0, 800, n), 
             "h":50, "dT":1.0, "plot":plot},
            {"propQ":'eta_drive', 
             "xaxis":"dT", "yaxis":"Uinf", 
             "Uinf":np.linspace(0, 50, n), "t":30, 
             "h":50, "dT":np.linspace(0.4, 1, n), "plot":plot},
            {"propQ":'eta_drive', 
             # "xaxis":"Uinf", "yaxis":"h", 
             "Uinf":np.linspace(0, 35, n), "t":30, 
             "h":np.linspace(0, 30000, n), "dT":0.8, "plot":plot},
            {"propQ":'eta_drive', 
             # "xaxis":"t", "yaxis":"h", 
             "Uinf":25, "t":np.linspace(0, 300, n), 
             "h":np.linspace(0, 30000, n), "dT":0.8, "plot":plot},
            {"propQ":'eta_drive', 
             # "xaxis":"t", "yaxis":"Uinf", 
             "Uinf":np.linspace(0, 50, n), "t": np.linspace(0, 300, n), 
             "h":50, "dT":0.8, "plot":plot},
            ]
        
        for i, case in enumerate(cases):
            with self.subTest(case=case):
                self.design.ContourPlot(
                    verbose=False,
                    **case
                )
        

if __name__ == '__main__':
    unittest.main()
