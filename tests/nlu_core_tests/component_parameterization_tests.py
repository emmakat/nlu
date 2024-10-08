import unittest

import nlu


class TestParameterization(unittest.TestCase):
    def test_set_parameters(self):

        pipe = nlu.load("sentiment")
        print(pipe.keys())
        pipe.generate_class_metadata_table()


if __name__ == "__main__":
    TestParameterization().test_entities_config()
