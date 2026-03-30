import unittest
from unittest.mock import patch
import numpy as np
import io
import contextlib

from uavdex import _uavdex_root
from uavdex.common import PointDesign
from uavdex.utils import open_csv, open_folder
from uavdex.VSPcontribution.units import ft2m, mph2ms, kmh2ms, kt2ms


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
        self.design.Battery('Gaoneng_8S_3300', discharge = 85)
        self.design.Prop('16x12E')
        
    def test_pointresult_errormessages(self):
        expected_errors = ['ERROR: Input t corresponds to SOC less than 15% from .Battery()',
                           'ERROR: Propeller data predicts zero thrust (high advance ratio). Reduce Uinf, t or increase dT', 
                           'ERROR: Propeller data predicts zero thrust (high advance ratio). Reduce Uinf, t or increase dT', 
                           'ERROR: Input Voc for LiPo corresponds to SOC < 15%',
                           'ERROR: Propeller data predicts zero thrust (high advance ratio). Reduce Uinf, t or increase dT',
                           'ERROR: Input Voc for LiPo corresponds to SOC > 100%'
                           ]
        cases = [
            {"Uinf_mps":40, "dT":100, "h_m":50, "t_s":300},
            {"Uinf_mps":70, "dT":100, "h_m":50, "t_m":5.0},
            {"Uinf_mps":70, "dT":100, "h_m":50, "SOC":50},
            {"Uinf_mps":20, "dT":100, "h_m":50, "Voc":2.8},
            {"Uinf_mps":70, "dT":100, "h_m":50, "Voc":3.6},
            {"Uinf_mps":20, "dT":100, "h_m":50, "Voc":4.2}
            ]
        for i, case in enumerate(cases):
            with self.subTest(case=case):
                f = io.StringIO()
                with contextlib.redirect_stdout(f):
                    data = self.design.PointResult(verbose=False, **case)
        
                output = f.getvalue().split("\n")[0]
                self.assertEqual(output, expected_errors[i])

    # todo: replace precomputed results with new arrays
    def test_pointresult_variants(self):
        cases = [
            {"h_m": 50,       "SOC": 100},
            {"h_m": 50,       "Voc": 3.8},
            {"h_m": 50,       "t_s": 30},
            {"rho_kgm3": 1.225,  "SOC": 100},
            {"rho_kgm3": 1.225,  "Voc": 3.8},
            {"rho_kgm3": 1.225,  "t_s": 30},
        ]
        precomputed_results = [
            np.array([33.811293, 7.601081, 3447.792339, 121.617296, 1.233228, 0.909582, 6488.415003, 
                      35.526857, 60.526075, 100.0, 90.449959, 65.1, 99.683876, 837.935371, 926.407689, 
                      1423.053285, 88.472318, 496.645597, 4.512882, 39.512992, 42.487088, 42.487088, 
                      23.445648, 33.493782, 33.493782, 4.2, 99.975586]),
            np.array([26.912846, 6.050248, 2744.346518, 96.803975, 1.023201, 0.754674, 5911.193848, 
                      37.520534, 63.736204, 100.0, 90.691735, 65.1, 99.708945, 633.380497, 698.388336, 
                      1072.793143, 65.007839, 374.404807, 3.13153, 32.914801, 35.392259, 35.392259, 
                      21.218064, 30.311519, 30.311519, 3.8, 70.703125]),
            np.array([30.618255, 6.883258, 3122.193122, 110.132121, 1.136759, 0.838431, 6229.141712, 
                      36.406753, 61.936449, 100.0, 90.569324, 65.1, 99.695035, 741.524307, 818.736713, 
                      1257.660081, 77.212405, 438.923368, 3.847155, 36.482351, 39.228334, 39.228334, 
                      22.441995, 32.059992, 32.059992, 4.019758, 90.093855]),
            np.array([33.94541, 7.631232, 3461.468487, 122.099708, 1.238312, 0.913332, 6486.120224, 
                      35.524172, 60.538069, 100.0, 90.426363, 65.1, 99.682598, 841.092485, 930.140784, 
                      1428.787686, 89.048299, 498.646902, 4.549442, 39.672724, 42.658843, 42.658843, 
                      23.445347, 33.493353, 33.493353, 4.2, 99.975586]),
            np.array([27.020699, 6.074495, 2755.344486, 97.191917, 1.027461, 0.757817, 5909.272909, 
                      37.518331, 63.746995, 100.0, 90.672135, 65.1, 99.707762, 635.81112, 701.219975, 
                      1077.142819, 65.408855, 375.922844, 3.15705, 33.048647, 35.53618, 35.53618, 
                      21.217812, 30.31116, 30.31116, 3.8, 70.703125]),
            np.array([30.729918, 6.90836, 3133.579593, 110.533767, 1.141142, 0.841663, 6226.187706, 
                      36.407397, 61.952947, 100.0, 90.547893, 65.1, 99.69384, 744.030427, 821.69822, 
                      1262.209247, 77.667793, 440.511027, 3.876251, 36.620048, 39.376396, 39.376396, 
                      22.43848, 32.054972, 32.054972, 4.019177, 90.056466]),
            ] 
        
        # todo: add tests for all error messages

        total_tested = 0
        for i, case in enumerate(cases):
            with self.subTest(case=case):
                data = self.design.PointResult(
                    Uinf_mps=15,
                    dT=70,
                    verbose=False,
                    **case
                )
                for j, value in enumerate(data):
                    self.assertEqual(precomputed_results[i][j], round(value, 6), f"PointResult case {i}, value {j} does not match precomputed")
                    # total_tested += 1
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
        #              Uinf_mps = np.linspace(0, 40, 100), 
        #              dT = 50, 
        #              h = 10, 
        #              SOC = 100, 
        #              plot = True)
        
        n = 100
        plot = False
        cases = [
            {"propQ":'eta_drive',   "Uinf_mps":np.linspace(0, 40, n), "dT":50, "h_m": 10, "SOC": 100, "plot":plot},
            {"propQ":'T',           "Uinf_mps":np.linspace(0, 40, n), "dT":50, "h_m": 10, "SOC": 100, "plot":plot},
            {"propQ":'eta_drive',   "Uinf_mps":25, "dT":np.linspace(30, 100, n), "h_m": 10, "SOC": 100, "plot":plot},
            {"propQ":'eta_drive',   "Uinf_mps":25, "dT":np.linspace(30, 100, n), "h_m": 10, "t_s": 0.0, "plot":plot}, # case for SimplifiedRPM_t
            {"propQ":['eta_drive', 'Ib', 'T'], "Uinf_mps":np.linspace(0, 50, n), "dT":100, "h_m":100, "t_s":30, "plot":plot}
            # {"propQ":'eta_p', "Uinf_mps":25, "dT":np.linspace(30, 100, n), "h": 10, "SOC": 100, "plot":True},
            # {"propQ":'eta_m', "Uinf_mps":25, "dT":np.linspace(30, 100, n), "h": 10, "SOC": 100, "plot":True},
            # {"propQ":'eta_c', "Uinf_mps":25, "dT":np.linspace(30, 100, n), "h": 10, "SOC": 100, "plot":True},
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
    
    def test_contourplot_Uinfs(self):
        n = 120
        plot = False
        cases = [
            # ensure all velocities produce the same plot for t + Uinf
            {"propQ":"eta_drive",
             "t_s":np.linspace(0, 30, n),
             "Uinf_mps":np.linspace(0, 30, n), 
             "dT":80,
             "h_ft":50,
             "plot":plot},
            {"propQ":"eta_drive",
             "t_s":np.linspace(0, 30, n),
             "Uinf_fps":np.linspace(0, 30, n)/ft2m,
             "dT":80,
             "h_ft":50,
             "plot":plot},
            {"propQ":"eta_drive",
             "t_s":np.linspace(0, 30, n),
             "Uinf_mph":np.linspace(0, 30, n)/mph2ms,
             "dT":80,
             "h_ft":50,
             "plot":plot},
            {"propQ":"eta_drive",
             "t_s":np.linspace(0, 30, n),
             "Uinf_kmh":np.linspace(0, 30, n)/kmh2ms,
             "dT":80,
             "h_ft":50,
             "plot":plot},
            {"propQ":"eta_drive",
             "t_s":np.linspace(0, 30, n),
             "Uinf_kt":np.linspace(0, 30, n)/kt2ms,
             "dT":80,
             "h_ft":50,
             "plot":plot},
            ]
        
        propQtotal = np.zeros((len(cases), n, n, 27))
        for i, case in enumerate(cases):
            # with self.subTest(case=case):
            _, _, propQtotal[i, :, :, :] = self.design.ContourPlot(
                verbose=True,
                **case
            )
            if i > 0:
                self.assertTrue(propQtotal[i].all() == propQtotal[i-1].all())
                
    def test_contourplot_t_variety(self):
        n = 120 # overview of all 6 types of contourplot
        plot = False
        t_arr = np.linspace(0, 500, n)
        t_const = 30
        Uinf_arr = np.linspace(0, 60, n)
        Uinf_const = 25
        dT_arr = np.linspace(20, 100, n)
        dT_const = 80
        h_arr = np.linspace(0, 80000, n)
        h_const = 100
        cases = [{"propQ":"eta_drive",
                 "t_s":t_arr,
                 "Uinf_mps":Uinf_arr, 
                 "dT":dT_const,
                 "h_ft":h_const,
                 "plot":plot},
                 
                 {"propQ":"eta_drive",
                "t_s":t_arr,
                "Uinf_mps":Uinf_const, 
                "dT":dT_arr,
                "h_ft":h_const,
                "plot":plot},
                 
                 {"propQ":"eta_drive",
                "t_s":t_arr,
                "Uinf_mps":Uinf_const, 
                "dT":dT_const,
                "h_ft":h_arr,
                "plot":plot},
                 
                 {"propQ":"eta_drive",
                "t_s":t_const,
                "Uinf_mps":Uinf_arr, 
                "dT":dT_arr,
                "h_ft":h_const,
                "plot":plot},
                 
                 {"propQ":"eta_drive",
                "t_s":t_const,
                "Uinf_mps":Uinf_arr, 
                "dT":dT_const,
                "h_ft":h_arr,
                "plot":plot},
                 
                 {"propQ":"eta_drive",
                "t_s":t_const,
                "Uinf_mps":Uinf_const, 
                "dT":dT_arr,
                "h_ft":h_arr,
                "plot":plot}
            ]
        for i, case in enumerate(cases):
            with self.subTest(case=case):
                _, _, _ = self.design.ContourPlot(
                    verbose=True,
                    **case
                )
                
    def test_contourplot_SOC_variety(self):
        n = 120 # overview of all 6 types of contourplot
        plot = False
        SOC_arr = np.linspace(0, 100, n)
        SOC_const = 70
        Uinf_arr = np.linspace(0, 60, n)
        Uinf_const = 25
        dT_arr = np.linspace(20, 100, n)
        dT_const = 80
        h_arr = np.linspace(0, 80000, n)
        h_const = 100
        cases = [{"propQ":"eta_drive",
                 "SOC":SOC_arr,
                 "Uinf_mps":Uinf_arr, 
                 "dT":dT_const,
                 "h_ft":h_const,
                 "plot":plot},
                 
                 {"propQ":"eta_drive",
                "SOC":SOC_arr,
                "Uinf_mps":Uinf_const, 
                "dT":dT_arr,
                "h_ft":h_const,
                "plot":plot},
                 
                 {"propQ":"eta_drive",
                "SOC":SOC_arr,
                "Uinf_mps":Uinf_const, 
                "dT":dT_const,
                "h_ft":h_arr,
                "plot":plot},
                 
                 {"propQ":"eta_drive",
                "SOC":SOC_const,
                "Uinf_mps":Uinf_arr, 
                "dT":dT_arr,
                "h_ft":h_const,
                "plot":plot},
                 
                 {"propQ":"eta_drive",
                "SOC":SOC_const,
                "Uinf_mps":Uinf_arr, 
                "dT":dT_const,
                "h_ft":h_arr,
                "plot":plot},
                 
                 {"propQ":"eta_drive",
                "SOC":SOC_const,
                "Uinf_mps":Uinf_const, 
                "dT":dT_arr,
                "h_ft":h_arr,
                "plot":plot}
            ]
        for i, case in enumerate(cases):
            with self.subTest(case=case):
                _, _, _ = self.design.ContourPlot(
                    verbose=True,
                    **case
                )
            
            # {"propQ":'eta_drive', 
            #  "Uinf_mps":np.linspace(0, 30, n), "t_s": np.linspace(0, 800, n), 
            #  "h_m":50, "dT":100, "plot":plot},
            # {"propQ":'eta_drive', 
            #  "Uinf_mps":np.linspace(0, 50, n), "t_s":30, 
            #  "h_m":50, "dT":np.linspace(40, 100, n), "plot":plot},
            # {"propQ":'eta_drive', 
            #  "Uinf_mps":np.linspace(0, 35, n), "t_s":30, 
            #  "h_m":np.linspace(0, 30000, n), "dT":80, "plot":plot},
            # {"propQ":'eta_drive', 
            #  "Uinf_mps":25, "t_s":np.linspace(0, 300, n), 
            #  "h_m":np.linspace(0, 30000, n), "dT":80, "plot":plot},
            # {"propQ":['T_lbf', 'eta_drive', 'Ib'],
            #  "Uinf_mps":np.linspace(0, 45, n), 
            #  "t_s": np.linspace(0, 300, n), 
            #  "h_m":50, 
            #  "dT":100,
            #  "plot":True},
            #  {"propQ":"eta_drive",
            #  "Uinf_mph":np.linspace(0, 45, n), 
            #  "Voc": np.linspace(3.5, 4.2, n), 
            #  "h_ft":50, 
            #  "dT":100, 
            #  "plot":plot},
            # {"propQ":"eta_drive",
            #  "Uinf_fps":50.0, 
            #  "Voc": np.linspace(3.5, 4.2, n), 
            #  "h_ft":50, 
            #  "dT":np.linspace(20, 100, n), 
            #  "plot":plot},

        # todo: implement unittests to check 

if __name__ == '__main__':
    unittest.main()
