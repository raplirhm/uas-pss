# tests.py
from django.test import TestCase
from lms_core.utils import validate_password

class PasswordValidationTest(TestCase):

    def test_valid_password(self):
        self.assertTrue(validate_password("PassValid1!"))
        self.assertTrue(validate_password("StrongPassword1@"))
        self.assertTrue(validate_password("Another$Valid2"))

    def test_invalid_password_length(self):
        self.assertFalse(validate_password("Short1!"))  # Terlalu pendek
        self.assertFalse(validate_password("NoSpecialChar1"))  # Tidak ada karakter khusus

    def test_invalid_password_no_uppercase(self):
        self.assertFalse(validate_password("invalidpassword1!"))  # Tidak ada huruf besar

    def test_invalid_password_no_lowercase(self):
        self.assertFalse(validate_password("INVALIDPASSWORD1!"))  # Tidak ada huruf kecil

    def test_invalid_password_no_digit(self):
        self.assertFalse(validate_password("NoDigit!"))  # Tidak ada angka

    def test_invalid_password_no_special_char(self):
        self.assertFalse(validate_password("NoSpecialChar1"))  # Tidak ada karakter khusus