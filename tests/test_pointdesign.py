import unittest
from unittest.mock import patch
import numpy as np

from uavdex import _uavdex_root
from uavdex.common import PointDesign
from uavdex.utils import open_csv, open_folder

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
        
class TestDatabaseAccess(unittest.TestCase):
    def test_csv_opening(self):        
        @patch('platform.system', return_value='Windows')
        @patch('os.startfile')
        def test_open_csv_windows(self, mock_startfile, mock_platform):
            test_path = 'C:\\test\\file.csv'
            open_csv(test_path)
            mock_startfile.assert_called_once_with(test_path)
     
        @patch('platform.system', return_value='Darwin')
        @patch('subprocess.call')
        def test_open_csv_macos(self, mock_subprocess_call, mock_platform):
            test_path = '/tmp/file.csv'
            open_csv(test_path)
            mock_subprocess_call.assert_called_once_with(['open', test_path])
     
        @patch('platform.system', return_value='Linux')
        @patch('subprocess.call')
        def test_open_csv_linux(self, mock_subprocess_call, mock_platform):
            test_path = '/tmp/file.txt'
            open_csv(test_path)
            mock_subprocess_call.assert_called_once_with(['xdg-open', test_path])
    def test_folder_opening(self):
        @patch('platform.system', return_value='Windows')
        @patch('os.startfile')
        def test_open_folder_windows(self, mock_startfile, mock_platform):
            test_path = 'C:\\test\\'
            open_folder(test_path)
            mock_startfile.assert_called_once_with(test_path)
     
        @patch('platform.system', return_value='Darwin')
        @patch('subprocess.call')
        def test_open_folder_macos(self, mock_subprocess_call, mock_platform):
            test_path = '/tmp/'
            open_folder(test_path)
            mock_subprocess_call.assert_called_once_with(['open', test_path])
     
        @patch('platform.system', return_value='Linux')
        @patch('subprocess.call')
        def test_open_folder_linux(self, mock_subprocess_call, mock_platform):
            test_path = '/tmp/'
            open_folder(test_path)
            mock_subprocess_call.assert_called_once_with(['xdg-open', test_path])
            
    def test_data_location(self):
        self.path_to_data = _uavdex_root / 'Databases/'
        
        def test_motor_data(self):
            file_path = self.path_to_data / 'Motors.csv'
            self.assertTrue(file_path.is_file())
            
        def test_battery_data(self, path_to_data):
            file_path = self.path_to_data / 'Batteries.csv'
            self.assertTrue(file_path.is_file())
        
        def test_prop_data(self, path_to_data):
            '''apologies to people who delete the 16x10E propeller'''
            file_path = self.path_to_data /'APCPropDatabase' / 'PER3_16x10E.dat'
            self.assertTrue(file_path.is_file())
            
    # def test_data_open(self):
    #     self.design = PointDesign()
    #     self.design.OpenMotorData()
    #     self.design.OpenBatteryData()
    #     self.design.OpenPropData()
        
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
            np.array([33.811293, 1.233228, 6488.415003, 0.355269, 0.605261, 1.0, 0.9045, 0.651, 0.996839, 837.935371, 926.407689, 1423.053285, 88.472318, 496.645597, 4.512882, 39.512992, 42.487088, 42.487088, 23.445648, 33.493782, 33.493782, 4.2, 0.999756]),
            np.array([26.912846, 1.023201, 5911.193848, 0.375205, 0.637362, 1.0, 0.906917, 0.651, 0.997089, 633.380497, 698.388336, 1072.793143, 65.007839, 374.404807, 3.13153, 32.914801, 35.392259, 35.392259, 21.218064, 30.311519, 30.311519, 3.8, 0.707031]),
            np.array([30.618255, 1.136759, 6229.141712, 0.364068, 0.619364, 1.0, 0.905693, 0.651, 0.99695, 741.524307, 818.736713, 1257.660081, 77.212405, 438.923368, 3.847155, 36.482351, 39.228334, 39.228334, 22.441995, 32.059992, 32.059992, 4.019758, 0.900939]),
            np.array([33.94541, 1.238312, 6486.120224, 0.355242, 0.605381, 1.0, 0.904264, 0.651, 0.996826, 841.092485, 930.140784, 1428.787686, 89.048299, 498.646902, 4.549442, 39.672724, 42.658843, 42.658843, 23.445347, 33.493353, 33.493353, 4.2, 0.999756]),
            np.array([27.020699, 1.027461, 5909.272909, 0.375183, 0.63747, 1.0, 0.906721, 0.651, 0.997078, 635.81112, 701.219975, 1077.142819, 65.408855, 375.922844, 3.15705, 33.048647, 35.53618, 35.53618, 21.217812, 30.31116, 30.31116, 3.8, 0.707031]),
            np.array([30.729918, 1.141142, 6226.187706, 0.364074, 0.619529, 1.0, 0.905479, 0.651, 0.996938, 744.030427, 821.69822, 1262.209247, 77.667793, 440.511027, 3.876251, 36.620048, 39.376396, 39.376396, 22.43848, 32.054972, 32.054972, 4.019177, 0.900565]),
            ] 
        
        self.design.PointResult(Uinf = 40, dT = 1.0, h = 50, t = 300) # where propeller is valid but SOC < 1 - ds
        self.design.PointResult(Uinf = 60, dT = 1.0, h = 50, t = 300) # where propeller cannot make thrust

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
        
        n = 100
        plot = False
        cases = [
            {"propQ":'eta_drive',   "Uinf":np.linspace(0, 40, n), "dT":0.5, "h": 10, "SOC": 1.0, "plot":plot},
            {"propQ":'T',           "Uinf":np.linspace(0, 40, n), "dT":0.5, "h": 10, "SOC": 1.0, "plot":plot},
            {"propQ":'eta_drive',   "Uinf":25, "dT":np.linspace(0.3, 1.0, n), "h": 10, "SOC": 1.0, "plot":plot},
            {"propQ":'eta_drive',   "Uinf":25, "dT":np.linspace(0.3, 1.0, n), "h": 10, "t": 0.0, "plot":plot}, # case for SimplifiedRPM_t
            {"propQ":['eta_drive', 'Ib', 'T'], "Uinf":np.linspace(0, 50, n), "dT":1.0, "h":100, "t":30, "plot":plot}
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
        self.design.Motor('C-4130/20', nmot = 2)
        self.design.Battery('Gaoneng_8S_3300')
        self.design.Prop('16x10E')
        # self.design.Motor('V8110-170', nmot = 1)
        # self.design.Battery('Gaoneng_8S_3300')
        # self.design.Prop('22x12E')
    
    def test_contourplot_varients(self):
        n = 100
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
            {"propQ":['T', 'eta_drive', 'Ib'],
             # "xaxis":"t", "yaxis":"Uinf", 
             "Uinf":np.linspace(0, 45, n), 
             "t": 20, 
             "h":50, 
             "dT":np.linspace(0.2, 1.0, n), 
             "plot":plot},
            
            # {"propQ":"eta_drive",
            #  # "xaxis":"t", "yaxis":"Uinf", 
            #  "Uinf":np.linspace(0, 45, n), 
            #  "Voc": np.linspace(3.5, 4.2, n), 
            #  "h":50, 
            #  "dT":1.0, 
            #  "plot":False},
            # {"propQ":"eta_drive",
            #  # "xaxis":"t", "yaxis":"Uinf", 
            #  "Uinf":30.0, 
            #  "Voc": np.linspace(3.5, 4.2, n), 
            #  "h":50, 
            #  "dT":np.linspace(0.2, 1.0, n), 
            #  "plot":False},

            ]
        
        for i, case in enumerate(cases):
            with self.subTest(case=case):
                self.design.ContourPlot(
                    verbose=True,
                    **case
                )
        

if __name__ == '__main__':
    unittest.main()
