"""A smoke test cannot silently expand to all open testing-area questions."""
from types import SimpleNamespace
import unittest

from bot.test_selection import select_test_question


class TestSelection(unittest.TestCase):
    def setUp(self):
        self.questions = [SimpleNamespace(id_of_post=i) for i in range(20)]

    def test_default_is_one_question(self):
        self.assertEqual(select_test_question(self.questions), self.questions[:1])

    def test_explicit_id_is_one_question(self):
        self.assertEqual(select_test_question(self.questions, 12), [self.questions[12]])

    def test_wrong_id_rejected_before_forecasting(self):
        with self.assertRaises(ValueError):
            select_test_question(self.questions, 999)

    def test_empty_testing_area_rejected(self):
        with self.assertRaises(ValueError):
            select_test_question([])
