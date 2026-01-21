import os
import typing
import unittest

from bitarray import bitarray
from pydantic import BaseModel

from xtce import xtceschema


calibrator_tenth = xtceschema.DefaultCalibrator(
        polynomialCalibrator=xtceschema.PolynomialCalibrator(term=[xtceschema.Term(coefficient=0.0, exponent=0), xtceschema.Term(coefficient=0.1, exponent=1)])
)

calibrator_100 = xtceschema.DefaultCalibrator(
        polynomialCalibrator=xtceschema.PolynomialCalibrator(term=[xtceschema.Term(coefficient=0.0, exponent=0), xtceschema.Term(coefficient=100, exponent=1)])
)


class calibrationTestCase(BaseModel):
    typ: typing.Any
    cal: float
    uncal: int


class TestPolynomialCalibrator(unittest.TestCase):

    def test_calibration(self):
        tests = (
            # no change
            calibrationTestCase(
                typ=xtceschema.PolynomialCalibrator(
                    term=[xtceschema.Term(coefficient=0.0, exponent=0), xtceschema.Term(coefficient=1.0, exponent=1)]),
                uncal=12, cal=12.0),
            # first coefficient
            calibrationTestCase(
                typ=xtceschema.PolynomialCalibrator(
                    term=[xtceschema.Term(coefficient=10.0, exponent=0), xtceschema.Term(coefficient=1.0, exponent=1)]),
                uncal=12, cal=22.0),
            # linear equation
            calibrationTestCase(
                typ=xtceschema.PolynomialCalibrator(
                    term=[xtceschema.Term(coefficient=10.0, exponent=0), xtceschema.Term(coefficient=0.1, exponent=1)]),
                uncal=12, cal=11.2),
            # three coefficients
            calibrationTestCase(
                typ=xtceschema.PolynomialCalibrator(
                    term=[xtceschema.Term(coefficient=-15.0, exponent=0), xtceschema.Term(coefficient=2.0, exponent=1), xtceschema.Term(coefficient=1.0, exponent=2)]),
                uncal=12, cal=153.0),
            # five coefficients, from CCSDS 660x1g2
            calibrationTestCase(
                typ=xtceschema.PolynomialCalibrator(
                    term = [
                        xtceschema.Term(coefficient=-7459.23273708, exponent=0),
                        xtceschema.Term(coefficient=8.23643519148, exponent=1),
                        xtceschema.Term(coefficient=-3.02185061876e3, exponent=2),
                        xtceschema.Term(coefficient=2.33422429056e-7, exponent=3),
                        xtceschema.Term(coefficient=5.67189556173e11, exponent=4),
                    ]
                ),
                uncal=8012, cal=2.3371790673058884e+27,
            )
        )

        for i, tt in enumerate(tests):
            with self.subTest(i=i):
                got_uncal = tt.typ.uncalibrate(tt.cal)
                self.assertEqual(got_uncal, tt.uncal, "incorrect uncalibrated value")

            with self.subTest(i=i):
                got_cal = tt.typ.calibrate(tt.uncal)
                self.assertEqual(got_cal, tt.cal, "incorrect calibrated value")


class encodingTestCase(BaseModel):
    typ: typing.Any
    dec: typing.Any
    enc: typing.Any


class TestIntegerDataEncoding(unittest.TestCase):

    def test_encoding(self):
        tests = (
            encodingTestCase(typ=xtceschema.IntegerDataEncoding(), dec=12, enc=bitarray([0, 0, 0, 0, 1, 1, 0, 0])),
            encodingTestCase(typ=xtceschema.IntegerDataEncoding(sizeInBits=16), dec=30000, enc=bitarray(bytearray([0x75, 0x30]))),
            encodingTestCase(typ=xtceschema.IntegerDataEncoding(sizeInBits=1), dec=1, enc=bitarray([1])),
            encodingTestCase(typ=xtceschema.IntegerDataEncoding(sizeInBits=3), dec=2, enc=bitarray([0, 1, 0])),
            encodingTestCase(typ=xtceschema.IntegerDataEncoding(sizeInBits=16, defaultCalibrator=calibrator_tenth), dec=300, enc=bitarray(bytearray([0x0b, 0xb8]))),
            encodingTestCase(typ=xtceschema.IntegerDataEncoding(sizeInBits=24, defaultCalibrator=calibrator_100), dec=2002200, enc=bitarray(bytearray([0x00, 0x4e, 0x36]))),
            encodingTestCase(typ=xtceschema.IntegerDataEncoding(sizeInBits=32), dec=30000, enc=bitarray(bytearray([0x00, 0x00, 0x75, 0x30]))),
            encodingTestCase(typ=xtceschema.IntegerDataEncoding(sizeInBits=32), dec=100000, enc=bitarray(bytearray([0x00, 0x01, 0x86, 0xa0]))),
            encodingTestCase(typ=xtceschema.IntegerDataEncoding(sizeInBits=32, encoding=xtceschema.SignedEnum.twosComplement), dec=-30000, enc=bitarray(bytearray([0xff, 0xff, 0x8a, 0xd0]))),
        )

        for i, tt in enumerate(tests):
            with self.subTest(i=i):
                got_enc = tt.typ.encode(tt.dec)
                self.assertEqual(got_enc, tt.enc, "incorrect encoded value")

            with self.subTest(i=i):
                got_dec = tt.typ.decode(tt.enc)
                self.assertEqual(got_dec, tt.dec, "incorrect decoded value")


class TestIntegerBaseType(unittest.TestCase):

    def test_encoding(self):
        tests = (
            encodingTestCase(typ=xtceschema.integerBaseType(name='test'), dec=12, enc=bitarray(bytearray([0x0c]))),
            encodingTestCase(typ=xtceschema.integerBaseType(name='test', sizeInBits=32), dec=12, enc=bitarray(bytearray([0x0c]))),
            encodingTestCase(typ=xtceschema.integerBaseType(name='test', sizeInBits=32, integerDataEncoding=xtceschema.IntegerDataEncoding(sizeInBits=16)), dec=12, enc=bitarray(bytearray([0x00, 0x0c]))),
        )

        for i, tt in enumerate(tests):
            with self.subTest(i=i):
                got_enc = tt.typ.data_encoding.encode(tt.dec)
                self.assertEqual(got_enc, tt.enc, "incorrect encoded value")

            with self.subTest(i=i):
                got_dec = tt.typ.data_encoding.decode(tt.enc)
                self.assertEqual(got_dec, tt.dec, "incorrect decoded value")


class TestFloatBaseType(unittest.TestCase):

    def test_encoding(self):
        tests = (
            encodingTestCase(typ=xtceschema.floatBaseType(name='test', integerDataEncoding=xtceschema.IntegerDataEncoding(sizeInBits=24, defaultCalibrator=calibrator_tenth)), dec=122.1, enc=bitarray(bytearray([0x00, 0x04, 0xc5]))),
        )

        for i, tt in enumerate(tests):
            with self.subTest(i=i):
                got_enc = tt.typ.data_encoding.encode(tt.dec)
                self.assertEqual(got_enc, tt.enc, "incorrect encoded value")

            with self.subTest(i=i):
                got_dec = tt.typ.data_encoding.decode(tt.enc)
                self.assertEqual(got_dec, tt.dec, "incorrect decoded value")


class TestBooleanParameterType(unittest.TestCase):

    def test_encode_and_decode_with_default_encoding(self):
        """Test BooleanParameterType with default 1-bit encoding and True/False values."""
        typ = xtceschema.BooleanParameterType(name='test_bool')

        # Test with bool values
        enc_true = typ.data_encoding.encode(True)
        self.assertEqual(enc_true, bitarray([1]))
        enc_false = typ.data_encoding.encode(False)
        self.assertEqual(enc_false, bitarray([0]))

        # Test decode
        dec_true = typ.data_encoding.decode(bitarray([1]))
        self.assertTrue(dec_true)
        dec_false = typ.data_encoding.decode(bitarray([0]))
        self.assertFalse(dec_false)

    def test_encode_with_string_values(self):
        """Test encoding with string values (True/False)."""
        typ = xtceschema.BooleanParameterType(name='test_bool')

        enc_true = typ.data_encoding.encode('True')
        self.assertEqual(enc_true, bitarray([1]))
        enc_false = typ.data_encoding.encode('False')
        self.assertEqual(enc_false, bitarray([0]))

    def test_encode_with_int_values(self):
        """Test encoding with integer values (0/1)."""
        typ = xtceschema.BooleanParameterType(name='test_bool')

        enc_one = typ.data_encoding.encode(1)
        self.assertEqual(enc_one, bitarray([1]))
        enc_zero = typ.data_encoding.encode(0)
        self.assertEqual(enc_zero, bitarray([0]))

    def test_custom_string_values(self):
        """Test BooleanParameterType with custom string values (ON/OFF)."""
        typ = xtceschema.BooleanParameterType(
            name='test_bool',
            zeroStringValue='OFF',
            oneStringValue='ON',
        )

        # Encode using custom string values
        enc_on = typ.data_encoding.encode('ON')
        self.assertEqual(enc_on, bitarray([1]))
        enc_off = typ.data_encoding.encode('OFF')
        self.assertEqual(enc_off, bitarray([0]))

        # Bool values still work
        enc_true = typ.data_encoding.encode(True)
        self.assertEqual(enc_true, bitarray([1]))

    def test_custom_encoding_size(self):
        """Test BooleanParameterType with custom encoding size (8-bit)."""
        typ = xtceschema.BooleanParameterType(
            name='test_bool',
            zeroStringValue='DISCHARGE',
            oneStringValue='CHARGE',
            integerDataEncoding=xtceschema.IntegerDataEncoding(sizeInBits=8),
        )

        enc_charge = typ.data_encoding.encode('CHARGE')
        self.assertEqual(enc_charge, bitarray([0, 0, 0, 0, 0, 0, 0, 1]))
        enc_discharge = typ.data_encoding.encode('DISCHARGE')
        self.assertEqual(enc_discharge, bitarray([0, 0, 0, 0, 0, 0, 0, 0]))

        # Verify size method
        self.assertEqual(typ.data_encoding.size({}), 8)

    def test_size_method(self):
        """Test that size method returns correct value."""
        typ_default = xtceschema.BooleanParameterType(name='test_bool')
        self.assertEqual(typ_default.data_encoding.size({}), 1)

        typ_custom = xtceschema.BooleanParameterType(
            name='test_bool',
            integerDataEncoding=xtceschema.IntegerDataEncoding(sizeInBits=4),
        )
        self.assertEqual(typ_custom.data_encoding.size({}), 4)


class TestStringDataEncoding(unittest.TestCase):

    def test_encode_utf8_fixed_size(self):
        """Test UTF-8 encoding with fixed size."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(fixed=xtceschema.Fixed(fixedValue=64)),
        )

        # 8 bytes = 64 bits
        result = enc.encode("Hello")
        self.assertEqual(len(result), 64)
        # "Hello" is 5 bytes, padded with 3 null bytes
        expected = bitarray()
        expected.frombytes(b'Hello\x00\x00\x00')
        self.assertEqual(result, expected)

    def test_decode_utf8_fixed_size(self):
        """Test UTF-8 decoding with fixed size."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(fixed=xtceschema.Fixed(fixedValue=64)),
        )

        # Encode then decode
        bits = bitarray()
        bits.frombytes(b'Hello\x00\x00\x00')
        result = enc.decode(bits)
        self.assertEqual(result, "Hello")

    def test_encode_decode_roundtrip_utf8(self):
        """Test encode/decode roundtrip for UTF-8."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(fixed=xtceschema.Fixed(fixedValue=128)),
        )

        test_strings = ["Hello", "Test123", "Short", ""]
        for s in test_strings:
            with self.subTest(s=s):
                encoded = enc.encode(s)
                decoded = enc.decode(encoded)
                self.assertEqual(decoded, s)

    def test_encode_truncates_long_string(self):
        """Test that long strings are truncated to fit."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(fixed=xtceschema.Fixed(fixedValue=32)),
        )

        # Only 4 bytes available
        result = enc.encode("HelloWorld")
        self.assertEqual(len(result), 32)
        decoded = enc.decode(result)
        self.assertEqual(decoded, "Hell")

    def test_encode_decode_utf16(self):
        """Test UTF-16 encoding/decoding."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF16,
            sizeInBits=xtceschema.SizeInBits(fixed=xtceschema.Fixed(fixedValue=64)),
        )

        # UTF-16 uses 2 bytes per character for basic ASCII
        result = enc.encode("Hi")
        self.assertEqual(len(result), 64)
        decoded = enc.decode(result)
        self.assertEqual(decoded, "Hi")

    def test_encode_decode_ascii(self):
        """Test US-ASCII encoding/decoding."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.US_ASCII,
            sizeInBits=xtceschema.SizeInBits(fixed=xtceschema.Fixed(fixedValue=64)),
        )

        result = enc.encode("Test")
        self.assertEqual(len(result), 64)
        decoded = enc.decode(result)
        self.assertEqual(decoded, "Test")

    def test_size_with_fixed_value(self):
        """Test size method with FixedValue."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(fixedValue=128),
        )
        self.assertEqual(enc.size({}), 128)

    def test_size_with_fixed_object(self):
        """Test size method with Fixed object."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(fixed=xtceschema.Fixed(fixedValue=256)),
        )
        self.assertEqual(enc.size({}), 256)

    def test_size_with_dynamic_value(self):
        """Test size method with dynamic value."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(
                dynamicValue=xtceschema.DynamicValue(
                    parameterInstanceRef=xtceschema.ParameterInstanceRef(parameterRef='StringLength')
                )
            ),
        )
        self.assertEqual(enc.size({'StringLength': 64}), 64)


class TestStringParameterType(unittest.TestCase):

    def test_data_encoding_property(self):
        """Test that data_encoding returns StringDataEncoding."""
        typ = xtceschema.StringParameterType(
            name='test_string',
            stringDataEncoding=xtceschema.StringDataEncoding(
                encoding=xtceschema.StringEncodingEnum.UTF8,
                sizeInBits=xtceschema.SizeInBits(fixed=xtceschema.Fixed(fixedValue=128)),
            ),
        )

        enc = typ.data_encoding
        self.assertIsInstance(enc, xtceschema.StringDataEncoding)
        self.assertEqual(enc.size({}), 128)

    def test_encode_decode_via_parameter_type(self):
        """Test encode/decode through StringParameterType."""
        typ = xtceschema.StringParameterType(
            name='test_string',
            stringDataEncoding=xtceschema.StringDataEncoding(
                encoding=xtceschema.StringEncodingEnum.UTF8,
                sizeInBits=xtceschema.SizeInBits(fixed=xtceschema.Fixed(fixedValue=128)),
            ),
        )

        encoded = typ.data_encoding.encode("TestMessage")
        self.assertEqual(len(encoded), 128)
        decoded = typ.data_encoding.decode(encoded)
        self.assertEqual(decoded, "TestMessage")


class TestStringTerminationChar(unittest.TestCase):

    def test_encode_with_null_terminator(self):
        """Test encoding with explicit null termination character."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(
                fixed=xtceschema.Fixed(fixedValue=64),
                terminationChar='00',
            ),
        )

        result = enc.encode("Hello")
        self.assertEqual(len(result), 64)
        # "Hello" (5 bytes) + null terminator (1 byte) + padding (2 bytes)
        expected = bitarray()
        expected.frombytes(b'Hello\x00\x00\x00')
        self.assertEqual(result, expected)

    def test_decode_with_null_terminator(self):
        """Test decoding stops at termination character."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(
                fixed=xtceschema.Fixed(fixedValue=64),
                terminationChar='00',
            ),
        )

        # String with null terminator followed by garbage
        bits = bitarray()
        bits.frombytes(b'Hello\x00XY')
        result = enc.decode(bits)
        self.assertEqual(result, "Hello")

    def test_encode_with_crlf_terminator(self):
        """Test encoding with CRLF (0D0A) termination."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(
                fixed=xtceschema.Fixed(fixedValue=80),  # 10 bytes
                terminationChar='0D0A',  # CRLF
            ),
        )

        result = enc.encode("Test")
        self.assertEqual(len(result), 80)
        # "Test" (4 bytes) + CRLF (2 bytes) + padding (4 bytes)
        expected = bitarray()
        expected.frombytes(b'Test\r\n\x00\x00\x00\x00')
        self.assertEqual(result, expected)

    def test_decode_with_crlf_terminator(self):
        """Test decoding stops at CRLF terminator."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(
                fixed=xtceschema.Fixed(fixedValue=80),
                terminationChar='0D0A',
            ),
        )

        bits = bitarray()
        bits.frombytes(b'Test\r\nXXXX')
        result = enc.decode(bits)
        self.assertEqual(result, "Test")

    def test_encode_without_terminator_strips_nulls(self):
        """Test that without terminator, decode strips trailing nulls."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(
                fixed=xtceschema.Fixed(fixedValue=64),
                # No terminationChar specified
            ),
        )

        bits = bitarray()
        bits.frombytes(b'Hello\x00\x00\x00')
        result = enc.decode(bits)
        self.assertEqual(result, "Hello")

    def test_roundtrip_with_terminator(self):
        """Test encode/decode roundtrip with termination character."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(
                fixed=xtceschema.Fixed(fixedValue=128),
                terminationChar='00',
            ),
        )

        test_strings = ["Hello", "Test123", "Short", "A"]
        for s in test_strings:
            with self.subTest(s=s):
                encoded = enc.encode(s)
                decoded = enc.decode(encoded)
                self.assertEqual(decoded, s)

    def test_string_fills_entire_buffer_no_terminator_added(self):
        """Test that when string exactly fills buffer, no terminator is added."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(
                fixed=xtceschema.Fixed(fixedValue=40),  # 5 bytes
                terminationChar='00',
            ),
        )

        # "Hello" is exactly 5 bytes - no room for terminator
        result = enc.encode("Hello")
        expected = bitarray()
        expected.frombytes(b'Hello')
        self.assertEqual(result, expected)

    def test_get_termination_bytes_helper(self):
        """Test the _get_termination_bytes helper method."""
        # With termination char
        enc = xtceschema.StringDataEncoding(
            sizeInBits=xtceschema.SizeInBits(
                fixed=xtceschema.Fixed(fixedValue=64),
                terminationChar='00',
            ),
        )
        self.assertEqual(enc._get_termination_bytes(), b'\x00')

        # With multi-byte termination
        enc2 = xtceschema.StringDataEncoding(
            sizeInBits=xtceschema.SizeInBits(
                fixed=xtceschema.Fixed(fixedValue=64),
                terminationChar='0D0A',
            ),
        )
        self.assertEqual(enc2._get_termination_bytes(), b'\r\n')

        # Without termination char
        enc3 = xtceschema.StringDataEncoding(
            sizeInBits=xtceschema.SizeInBits(
                fixed=xtceschema.Fixed(fixedValue=64),
            ),
        )
        self.assertIsNone(enc3._get_termination_bytes())
