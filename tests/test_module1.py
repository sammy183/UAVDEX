import unittest

from uavdex.module1 import Number


class TestSimple(unittest.TestCase):

    def test_add(self):
        self.assertEqual((Number(5) + Number(6)).value, 11)



##### NEED TO BUILD THIS OUT
class TestComponentAddons(unittest.TestCase):
    def test_motor_import(self):
        thing = 5

if __name__ == '__main__':
    unittest.main()
