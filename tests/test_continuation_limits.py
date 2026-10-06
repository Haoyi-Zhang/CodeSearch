import os
import unittest
from unittest.mock import patch
from continuation_limits import allowance


class AllowanceTests(unittest.TestCase):
    def test_original_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(allowance('TEST_ALLOWANCE', 135), 135)

    def test_explicit_host_allowance(self):
        with patch.dict(os.environ, {'TEST_ALLOWANCE': '300'}):
            self.assertEqual(allowance('TEST_ALLOWANCE', 135), 300)

    def test_invalid_or_unbounded_allowance(self):
        for value in ('-1', '0', '134', '601', 'nan', '300.0'):
            with self.subTest(value=value), patch.dict(os.environ, {'TEST_ALLOWANCE': value}):
                with self.assertRaises(ValueError):
                    allowance('TEST_ALLOWANCE', 135)
