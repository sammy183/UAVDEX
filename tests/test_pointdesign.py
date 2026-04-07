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
            [33.88275, 7.617145, 3455.078903, 121.874322, 1.235354, 0.91115, 6494.15946, 50.774096, 60.496057, 100.0, 90.447363, 93.0, 99.778339, 840.122918, 928.852859, 998.766515, 88.729941, 69.913656, 2.218793, 39.579776, 29.791229, 29.791229, 23.467865, 33.525522, 33.525522, 4.2, 99.975586],
            [26.967227, 6.062474, 2749.891817, 96.999579, 1.024865, 0.755902, 5916.027069, 53.623877, 63.709175, 100.0, 90.690212, 93.0, 99.795938, 634.92958, 700.108164, 752.804478, 65.178584, 52.696313, 1.539329, 32.967093, 24.813941, 24.813941, 21.236576, 30.337965, 30.337965, 3.8, 70.703125],
            [31.484066, 7.0779, 3210.481221, 113.246392, 1.163101, 0.857859, 6300.516844, 51.705049, 61.540347, 100.0, 90.537507, 93.0, 99.784142, 767.400583, 847.605159, 911.403397, 80.204577, 63.798238, 1.971597, 37.309887, 28.082711, 28.082711, 22.717977, 32.454253, 32.454253, 4.065557, 92.908406],
            [34.017432, 7.647423, 3468.812717, 122.358768, 1.240455, 0.914913, 6491.884708, 50.770345, 60.507943, 100.0, 90.423729, 93.0, 99.777442, 843.296696, 932.605526, 1002.801641, 89.30883, 70.196115, 2.236798, 39.74004, 29.911858, 29.911858, 23.467654, 33.52522, 33.52522, 4.2, 99.975586],
            [27.075512, 6.086817, 2760.933869, 97.389076, 1.029141, 0.759055, 5914.121151, 53.620741, 63.719796, 100.0, 90.670548, 93.0, 99.795107, 637.372852, 702.954668, 755.865234, 65.581816, 52.910566, 1.551898, 33.101407, 24.915037, 24.915037, 21.236399, 30.337712, 30.337712, 3.8, 70.703125],
            [31.601196, 7.104232, 3222.425205, 113.667704, 1.167654, 0.861218, 6297.709703, 51.705056, 61.555835, 100.0, 90.515514, 93.0, 99.783289, 770.061756, 850.751125, 914.786156, 80.689369, 64.035031, 1.986745, 37.452943, 28.190387, 28.190387, 22.715201, 32.450287, 32.450287, 4.065095, 92.881215]
            ] 
        
        # total_tested = 0
        for i, case in enumerate(cases):
            with self.subTest(case=case):
                data = self.design.PointResult(
                    Uinf_mps=15,
                    dT=70,
                    verbose=False,
                    **case
                )
                # print(repr([float(f"{a:.6f}") for a in data]))
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
        # self.design.LinePlot(propQ = 'eta_drive', 
        #              Uinf_mph = np.linspace(0, 100, 100), 
        #              dT = 100, 
        #              h_m = 10, 
        #              SOC = 30, 
        #              plot = True)
        
        # TODO: add rigorous varients, i.e. all unit combinations and validate that they're the same
        n = 100
        plot = False
        cases = [
            {"propQ":'eta_drive',   "Uinf_mps":np.linspace(0, 40, n), "dT":50, "h_m": 10, "SOC": 100, "plot":plot},
            {"propQ":'T_lbf',           "Uinf_mps":np.linspace(0, 40, n), "dT":50, "h_m": 10, "SOC": 100, "plot":plot},
            {"propQ":'eta_drive',   "Uinf_mps":25, "dT":np.linspace(30, 100, n), "h_m": 10, "SOC": 100, "plot":plot},
            {"propQ":'eta_drive',   "Uinf_mps":25, "dT":np.linspace(30, 100, n), "h_m": 10, "t_s": 0.0, "plot":plot}, # case for SimplifiedRPM_t
            # {"propQ":['eta_drive', 'Ib', 'T_lbf'], "Uinf_mps":np.linspace(0, 50, n), "dT":100, "h_m":100, "t_s":30, "plot":plot},
            # {"propQ":'eta_p', "Uinf_mps":25, "dT":np.linspace(30, 100, n), "h_ft": 50, "SOC": 80, "plot":plot},
            # {"propQ":'eta_m', "Uinf_mps":25, "dT":np.linspace(30, 100, n), "h_ft": 50, "SOC": 80, "plot":plot},
            # {"propQ":'eta_c', "Uinf_mps":25, "dT":np.linspace(30, 100, n), "h_ft": 50, "SOC": 80, "plot":plot},
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
