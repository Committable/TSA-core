import unittest
from inputDealer.solidityCompiler import AllowedVersion


class TestAllowedVersion(unittest.TestCase):
    def test_get_version(self):
        version1 = AllowedVersion()
        version1.set_unique("0.4.25")
        self.assertEqual(version1.get_version(), "0.4.25")

        version2 = AllowedVersion()
        version2.set_right("0.4.25", False)
        self.assertEqual(version2.get_version(), "0.4.24")

        version3 = AllowedVersion()
        version3.set_right("0.4.25", True)
        self.assertEqual(version3.get_version(), "0.4.25")

        version4 = AllowedVersion()
        version4.set_left("0.4.11", False)
        self.assertEqual(version4.get_version(), "0.4.12")

        version5 = AllowedVersion()
        version5.set_left("0.4.11", True)
        self.assertEqual(version5.get_version(), "0.4.11")

        version6 = AllowedVersion()
        version6.set_left("0.4.13", False)
        version6.set_right("0.8.0", False)
        self.assertEqual(version6.get_version(), "0.7.6")

        version7 = AllowedVersion()
        version7.set_left("0.4.13", True)
        version7.set_right("0.8.0", False)
        self.assertEqual(version7.get_version(), "0.7.6")

        version8 = AllowedVersion()
        version8.set_left("0.4.13", False)
        version8.set_right("0.8.0", True)
        self.assertEqual(version7.get_version(), "0.8.0")

        version8 = AllowedVersion()
        version8.set_left("0.4.13", True)
        version8.set_right("0.8.0", True)
        self.assertEqual(version7.get_version(), "0.8.0")

    def test_merge(self):
        version1 = AllowedVersion()
        version1.set_unique("0.4.25")

        version2 = AllowedVersion()
        version2.set_unique("0.7.0")

        version3 = AllowedVersion()
        version3.set_right("0.7.0", True)

        version4 = AllowedVersion()
        version4.set_left("0.4.25", True)

        version5 = AllowedVersion()
        version5.set_left("0.4.13", False)
        version5.set_right("0.7.0", True)

        version6 = AllowedVersion()
        version6.set_left("0.4.25", True)
        version6.set_right("0.8.0", False)

        version7 = AllowedVersion()
        version7.set_left("0.7.0", False)
        version7.set_right("0.8.0", False)

        version = version1.merge(version2)
        self.assertEqual(version.get_version(), "0.7.0")

        version = version1.merge(version3)
        self.assertEqual(version.get_version(), "0.4.25")

        version = version3.merge(version4)
        self.assertEqual(version.get_version(), "0.4.25")

        version = version5.merge(version6)
        self.assertEqual(version.get_version(), "0.7.0")

        version = version4.merge(version5)
        self.assertEqual(version.get_version(), "0.4.25")

        version = version2.merge(version7)
        self.assertEqual(version.get_version(), "0.4.11")