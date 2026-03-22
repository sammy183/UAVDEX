import unittest

from uavdex.common import PointDesign
from uavdex.propulsions import propQnames

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
        

#### BUILD OUT TO CHECK IF IT COULD OPEN DATABSE SHEETS WITHOUT ACTUALLY OPENING THE FILES
# class TestDatabaseAccess(unittest.TestCase):
#     def test_motor_sheet(self):
#         t = PointDesign()
#         t.OpenMotorData()
        
class TestPointResult(unittest.TestCase):
    def setUp(self):
        self.design = PointDesign()
        self.design.Motor('C-4130/20', 1)
        self.design.Battery('Gaoneng_8S_3300', 0.85)
        self.design.Prop('16x12E')

    def test_pointresult_variants(self):
        cases = [
            {"h": 10,       "SOC": 1.0},
            {"rho": 1.225,  "Voc": 3.8},
            {"rho": 1.225,  "t": 30},
            {"rho": 1.225,  "SOC": 1.0},
            {"rho": 1.225,  "Voc": 3.8},
            {"rho": 1.225,  "t": 30},
        ]

        for case in cases:
            with self.subTest(case=case):
                data = self.design.PointResult(
                    Uinf=15,
                    dT=0.7,
                    verbose=False,
                    **case
                )
                print([
                    [float(f"{a:.6f}"), propQnames[i]]
                    for i, a in enumerate(data)
                ])

if __name__ == '__main__':
    unittest.main()
