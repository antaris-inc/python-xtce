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

        # Test decode - verify both value and type
        dec_true = typ.data_encoding.decode(bitarray([1]))
        self.assertIsInstance(dec_true, bool)
        self.assertTrue(dec_true)
        dec_false = typ.data_encoding.decode(bitarray([0]))
        self.assertIsInstance(dec_false, bool)
        self.assertFalse(dec_false)

    def test_encode_with_int_values(self):
        """Test encoding with integer values (0/1)."""
        typ = xtceschema.BooleanParameterType(name='test_bool')

        enc_one = typ.data_encoding.encode(1)
        self.assertEqual(enc_one, bitarray([1]))
        enc_zero = typ.data_encoding.encode(0)
        self.assertEqual(enc_zero, bitarray([0]))

    def test_rejects_string_values(self):
        """Test that string values are rejected."""
        typ = xtceschema.BooleanParameterType(name='test_bool')

        with self.assertRaises(ValueError):
            typ.data_encoding.encode('True')
        with self.assertRaises(ValueError):
            typ.data_encoding.encode('ON')

    def test_default_1bit_encoding(self):
        """Test BooleanParameterType with default 1-bit encoding."""
        typ = xtceschema.BooleanParameterType(name='test_bool')

        # Verify default size is 1 bit
        self.assertEqual(typ.data_encoding.size({}), 1)

        # Encode True -> 1 bit set
        enc_true = typ.data_encoding.encode(True)
        self.assertEqual(enc_true, bitarray([1]))
        self.assertEqual(len(enc_true), 1)

        # Encode False -> 1 bit clear
        enc_false = typ.data_encoding.encode(False)
        self.assertEqual(enc_false, bitarray([0]))
        self.assertEqual(len(enc_false), 1)

        # Decode and verify type is bool
        dec_true = typ.data_encoding.decode(bitarray([1]))
        self.assertIsInstance(dec_true, bool)
        self.assertTrue(dec_true)

        dec_false = typ.data_encoding.decode(bitarray([0]))
        self.assertIsInstance(dec_false, bool)
        self.assertFalse(dec_false)

    def test_custom_encoding_size(self):
        """Test BooleanParameterType with custom encoding size (8-bit)."""
        typ = xtceschema.BooleanParameterType(
            name='test_bool',
            integerDataEncoding=xtceschema.IntegerDataEncoding(sizeInBits=8),
        )

        enc_true = typ.data_encoding.encode(True)
        self.assertEqual(enc_true, bitarray([0, 0, 0, 0, 0, 0, 0, 1]))
        enc_false = typ.data_encoding.encode(False)
        self.assertEqual(enc_false, bitarray([0, 0, 0, 0, 0, 0, 0, 0]))

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

    def test_variable_string_encode_decode_via_parameter_type(self):
        """Test encode/decode through StringParameterType with variable-length string."""
        typ = xtceschema.StringParameterType(
            name='test_variable_string',
            stringDataEncoding=xtceschema.StringDataEncoding(
                encoding=xtceschema.StringEncodingEnum.UTF8,
                variable=xtceschema.VariableStringType(
                    maxSizeInBits=256,
                ),
            ),
        )

        enc = typ.data_encoding
        self.assertIsInstance(enc, xtceschema.StringDataEncoding)
        self.assertEqual(enc.size({}), 256)

        encoded = enc.encode("Hello")
        self.assertEqual(len(encoded), 256)
        decoded = enc.decode(encoded)
        self.assertEqual(decoded, "Hello")

    def test_variable_string_with_dynamic_value_via_parameter_type(self):
        """Test StringParameterType with variable-length string using dynamic value."""
        typ = xtceschema.StringParameterType(
            name='test_dynamic_variable_string',
            stringDataEncoding=xtceschema.StringDataEncoding(
                encoding=xtceschema.StringEncodingEnum.UTF8,
                variable=xtceschema.VariableStringType(
                    maxSizeInBits=512,
                    dynamicValue=xtceschema.DynamicValue(
                        parameterInstanceRef=xtceschema.ParameterInstanceRef(parameterRef='StringLen'),
                    ),
                ),
            ),
        )

        enc = typ.data_encoding
        self.assertEqual(enc.size({'StringLen': 80}), 80)

    def test_variable_string_termination_via_parameter_type(self):
        """Test StringParameterType with variable-length string using termination character."""
        typ = xtceschema.StringParameterType(
            name='test_terminated_variable_string',
            stringDataEncoding=xtceschema.StringDataEncoding(
                encoding=xtceschema.StringEncodingEnum.UTF8,
                variable=xtceschema.VariableStringType(
                    maxSizeInBits=128,
                    terminationChar='00',
                ),
            ),
        )

        enc = typ.data_encoding
        encoded = enc.encode("Hi")
        self.assertEqual(len(encoded), 128)
        decoded = enc.decode(encoded)
        self.assertEqual(decoded, "Hi")


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


class TestStringArgumentType(unittest.TestCase):

    def test_data_encoding_property(self):
        """Test that data_encoding returns StringDataEncoding."""
        typ = xtceschema.StringArgumentType(
            name='test_string_arg',
            stringDataEncoding=xtceschema.StringDataEncoding(
                encoding=xtceschema.StringEncodingEnum.UTF8,
                sizeInBits=xtceschema.SizeInBits(fixed=xtceschema.Fixed(fixedValue=128)),
            ),
        )

        enc = typ.data_encoding
        self.assertIsInstance(enc, xtceschema.StringDataEncoding)
        self.assertEqual(enc.size({}), 128)

    def test_encode_decode_via_argument_type(self):
        """Test encode/decode through StringArgumentType."""
        typ = xtceschema.StringArgumentType(
            name='test_string_arg',
            stringDataEncoding=xtceschema.StringDataEncoding(
                encoding=xtceschema.StringEncodingEnum.UTF8,
                sizeInBits=xtceschema.SizeInBits(fixed=xtceschema.Fixed(fixedValue=128)),
            ),
        )

        encoded = typ.data_encoding.encode("CmdPayload")
        self.assertEqual(len(encoded), 128)
        decoded = typ.data_encoding.decode(encoded)
        self.assertEqual(decoded, "CmdPayload")

    def test_default_encoding(self):
        """Test that StringArgumentType falls back to default StringDataEncoding."""
        typ = xtceschema.StringArgumentType(name='test_string_arg')
        enc = typ.data_encoding
        self.assertIsInstance(enc, xtceschema.StringDataEncoding)


class TestVariableStringType(unittest.TestCase):

    def test_default_values(self):
        """Test VariableStringType default values."""
        v = xtceschema.VariableStringType(maxSizeInBits=2048)
        self.assertEqual(v.maxSizeInBits, 2048)
        self.assertIsNone(v.dynamicValue)
        self.assertEqual(v.terminationChar, '00')

    def test_custom_values(self):
        """Test VariableStringType with custom values."""
        v = xtceschema.VariableStringType(
            maxSizeInBits=512,
            terminationChar='00',
            dynamicValue=xtceschema.DynamicValue(
                argumentInstanceRef=xtceschema.ArgumentInstanceRef(argumentRef='MySize'),
            ),
        )
        self.assertEqual(v.maxSizeInBits, 512)
        self.assertEqual(v.terminationChar, '00')
        self.assertEqual(v.dynamicValue.argumentInstanceRef.argumentRef, 'MySize')


class TestStringDataEncodingVariable(unittest.TestCase):

    def test_size_with_variable_dynamic_argument_ref(self):
        """Test size() with Variable element using argumentInstanceRef."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            variable=xtceschema.VariableStringType(
                maxSizeInBits=256,
                dynamicValue=xtceschema.DynamicValue(
                    argumentInstanceRef=xtceschema.ArgumentInstanceRef(argumentRef='MyStringSize'),
                ),
            ),
        )
        self.assertEqual(enc.size({'MyStringSize': 80}), 80)

    def test_size_with_variable_dynamic_parameter_ref(self):
        """Test size() with Variable element using parameterInstanceRef."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            variable=xtceschema.VariableStringType(
                maxSizeInBits=256,
                dynamicValue=xtceschema.DynamicValue(
                    parameterInstanceRef=xtceschema.ParameterInstanceRef(parameterRef='StringLen'),
                ),
            ),
        )
        self.assertEqual(enc.size({'StringLen': 120}), 120)

    def test_size_with_variable_max_size_fallback(self):
        """Test size() falls back to maxSizeInBits when no dynamicValue."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            variable=xtceschema.VariableStringType(maxSizeInBits=512),
        )
        self.assertEqual(enc.size({}), 512)

    def test_size_variable_dynamic_ref_not_found(self):
        """Test size() raises ValueError when dynamic ref is not found."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            variable=xtceschema.VariableStringType(
                maxSizeInBits=256,
                dynamicValue=xtceschema.DynamicValue(
                    argumentInstanceRef=xtceschema.ArgumentInstanceRef(argumentRef='Missing'),
                ),
            ),
        )
        with self.assertRaises(ValueError):
            enc.size({})

    def test_size_variable_dynamic_no_ref(self):
        """Test size() raises ValueError when dynamicValue has no reference."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            variable=xtceschema.VariableStringType(
                maxSizeInBits=256,
                dynamicValue=xtceschema.DynamicValue(),
            ),
        )
        with self.assertRaises(ValueError):
            enc.size({})

    def test_termination_bytes_from_variable(self):
        """Test _get_termination_bytes() reads from variable.terminationChar."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            variable=xtceschema.VariableStringType(
                maxSizeInBits=256,
                terminationChar='00',
            ),
        )
        self.assertEqual(enc._get_termination_bytes(), b'\x00')

    def test_termination_bytes_variable_default(self):
        """Test _get_termination_bytes() returns null byte when variable uses default terminationChar."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            variable=xtceschema.VariableStringType(maxSizeInBits=256),
        )
        self.assertEqual(enc._get_termination_bytes(), b'\x00')

    def test_no_size_or_variable_raises(self):
        """Test size() raises ValueError when neither sizeInBits nor variable is set."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
        )
        with self.assertRaises(ValueError):
            enc.size({})


class TestStringDataEncodingSizeArgumentRef(unittest.TestCase):

    def test_size_with_argument_instance_ref(self):
        """Test size() with SizeInBits dynamicValue using argumentInstanceRef."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(
                dynamicValue=xtceschema.DynamicValue(
                    argumentInstanceRef=xtceschema.ArgumentInstanceRef(argumentRef='CmdStringSize'),
                ),
            ),
        )
        self.assertEqual(enc.size({'CmdStringSize': 64}), 64)

    def test_size_dynamic_no_ref_raises(self):
        """Test size() raises ValueError when SizeInBits dynamicValue has no reference."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(
                dynamicValue=xtceschema.DynamicValue(),
            ),
        )
        with self.assertRaises(ValueError):
            enc.size({})

    def test_size_dynamic_ref_not_found_raises(self):
        """Test size() raises ValueError when dynamic ref is not in parameters."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            sizeInBits=xtceschema.SizeInBits(
                dynamicValue=xtceschema.DynamicValue(
                    argumentInstanceRef=xtceschema.ArgumentInstanceRef(argumentRef='Missing'),
                ),
            ),
        )
        with self.assertRaises(ValueError):
            enc.size({})


class TestStringDataEncodingEncodeWithParameters(unittest.TestCase):
    """Tests for StringDataEncoding.encode() accepting a parameters dict to resolve dynamic sizes."""

    def test_encode_variable_with_dynamic_parameter_ref(self):
        """Test encode() uses parameters dict to resolve parameterInstanceRef size."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            variable=xtceschema.VariableStringType(
                maxSizeInBits=2048,
                dynamicValue=xtceschema.DynamicValue(
                    parameterInstanceRef=xtceschema.ParameterInstanceRef(parameterRef='element_type__size'),
                ),
            ),
        )

        # "satellite" is 9 bytes = 72 bits
        value = "satellite"
        size_bits = len(value.encode('utf-8')) * 8
        parameters = {'element_type__size': size_bits}

        encoded = enc.encode(value, parameters)
        self.assertEqual(len(encoded), size_bits)

        decoded = enc.decode(encoded)
        self.assertEqual(decoded, value)

    def test_encode_variable_with_dynamic_argument_ref(self):
        """Test encode() uses parameters dict to resolve argumentInstanceRef size."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            variable=xtceschema.VariableStringType(
                maxSizeInBits=2048,
                dynamicValue=xtceschema.DynamicValue(
                    argumentInstanceRef=xtceschema.ArgumentInstanceRef(argumentRef='cmd__name__size'),
                ),
            ),
        )

        value = "hello"
        size_bits = len(value.encode('utf-8')) * 8
        parameters = {'cmd__name__size': size_bits}

        encoded = enc.encode(value, parameters)
        self.assertEqual(len(encoded), size_bits)

        decoded = enc.decode(encoded)
        self.assertEqual(decoded, value)

    def test_encode_variable_dynamic_ref_without_parameters_raises(self):
        """Test encode() raises ValueError when dynamicValue is set but no parameters provided."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            variable=xtceschema.VariableStringType(
                maxSizeInBits=2048,
                dynamicValue=xtceschema.DynamicValue(
                    parameterInstanceRef=xtceschema.ParameterInstanceRef(parameterRef='missing_ref'),
                ),
            ),
        )

        with self.assertRaises(ValueError):
            enc.encode("test")

    def test_encode_variable_no_dynamic_value_uses_max_size(self):
        """Test encode() falls back to maxSizeInBits when no dynamicValue, with or without parameters."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            variable=xtceschema.VariableStringType(maxSizeInBits=128),
        )

        encoded_no_params = enc.encode("test")
        self.assertEqual(len(encoded_no_params), 128)

        encoded_with_params = enc.encode("test", {'some_key': 99})
        self.assertEqual(len(encoded_with_params), 128)

    def test_encode_roundtrip_variable_dynamic_size(self):
        """Test full encode/decode roundtrip with variable dynamic size for various strings."""
        enc = xtceschema.StringDataEncoding(
            encoding=xtceschema.StringEncodingEnum.UTF8,
            variable=xtceschema.VariableStringType(
                maxSizeInBits=2048,
                dynamicValue=xtceschema.DynamicValue(
                    parameterInstanceRef=xtceschema.ParameterInstanceRef(parameterRef='str__size'),
                ),
            ),
        )

        for value in ["groundstation", "satellite", "a", "missile"]:
            with self.subTest(value=value):
                size_bits = len(value.encode('utf-8')) * 8
                encoded = enc.encode(value, {'str__size': size_bits})
                self.assertEqual(len(encoded), size_bits)
                decoded = enc.decode(encoded)
                self.assertEqual(decoded, value)


class TestFloatDataEncoding(unittest.TestCase):

    def test_32bit_ieee754_1985_encode_decode(self):
        """Test 32-bit IEEE754_1985 encode/decode."""
        enc = xtceschema.FloatDataEncoding(
            encoding=xtceschema.FloatEncodingEnum.IEEE754_1985,
            sizeInBits=32,
        )
        encoded = enc.encode(3.14)
        self.assertEqual(len(encoded), 32)
        decoded = enc.decode(encoded)
        self.assertAlmostEqual(decoded, 3.14, places=5)

    def test_64bit_ieee754_1985_encode_decode(self):
        """Test 64-bit IEEE754_1985 encode/decode."""
        enc = xtceschema.FloatDataEncoding(
            encoding=xtceschema.FloatEncodingEnum.IEEE754_1985,
            sizeInBits=64,
        )
        encoded = enc.encode(3.141592653589793)
        self.assertEqual(len(encoded), 64)
        decoded = enc.decode(encoded)
        self.assertAlmostEqual(decoded, 3.141592653589793, places=12)

    def test_16bit_ieee754_encode_decode(self):
        """Test 16-bit IEEE754 encode/decode."""
        enc = xtceschema.FloatDataEncoding(
            encoding=xtceschema.FloatEncodingEnum.IEEE754,
            sizeInBits=16,
        )
        encoded = enc.encode(1.5)
        self.assertEqual(len(encoded), 16)
        decoded = enc.decode(encoded)
        self.assertAlmostEqual(decoded, 1.5, places=2)

    def test_default_encoding(self):
        """Test default FloatDataEncoding (IEEE754_1985, 32-bit)."""
        enc = xtceschema.FloatDataEncoding()
        self.assertEqual(enc.encoding, xtceschema.FloatEncodingEnum.IEEE754_1985)
        self.assertEqual(enc.sizeInBits, 32)
        self.assertEqual(enc.size({}), 32)

        encoded = enc.encode(1.0)
        self.assertEqual(len(encoded), 32)
        decoded = enc.decode(encoded)
        self.assertAlmostEqual(decoded, 1.0, places=5)

    def test_unsupported_size_raises(self):
        """Test that unsupported sizeInBits raises ValueError."""
        enc = xtceschema.FloatDataEncoding(sizeInBits=48)
        with self.assertRaises(ValueError):
            enc.encode(1.0)
        with self.assertRaises(ValueError):
            enc.decode(bitarray(48))

    def test_size_method(self):
        """Test size() returns sizeInBits."""
        for bits in (16, 32, 64):
            enc = xtceschema.FloatDataEncoding(sizeInBits=bits)
            self.assertEqual(enc.size({}), bits)

    def test_roundtrip_via_float_base_type(self):
        """Test roundtrip through floatBaseType.data_encoding with explicit FloatDataEncoding."""
        typ = xtceschema.floatBaseType(
            name='test_float',
            floatDataEncoding=xtceschema.FloatDataEncoding(sizeInBits=64),
        )
        encoded = typ.data_encoding.encode(2.718281828)
        decoded = typ.data_encoding.decode(encoded)
        self.assertAlmostEqual(decoded, 2.718281828, places=8)

    def test_float_base_type_default_encoding(self):
        """Test floatBaseType falls back to FloatDataEncoding with working defaults."""
        typ = xtceschema.floatBaseType(name='test_default')
        enc = typ.data_encoding
        self.assertIsInstance(enc, xtceschema.FloatDataEncoding)
        self.assertEqual(enc.size({}), 32)

        encoded = enc.encode(42.0)
        decoded = enc.decode(encoded)
        self.assertAlmostEqual(decoded, 42.0, places=5)


class TestFloatRange(unittest.TestCase):

    def test_all_bounds(self):
        r = xtceschema.FloatRange(minInclusive=-5.0, maxInclusive=5.0)
        self.assertEqual(r.minInclusive, -5.0)
        self.assertEqual(r.maxInclusive, 5.0)
        self.assertIsNone(r.minExclusive)
        self.assertIsNone(r.maxExclusive)

    def test_one_sided(self):
        r = xtceschema.FloatRange(minInclusive=30.5)
        self.assertEqual(r.minInclusive, 30.5)
        self.assertIsNone(r.maxInclusive)

    def test_exclusive_bounds(self):
        r = xtceschema.FloatRange(minExclusive=1.0, maxExclusive=10.0)
        self.assertEqual(r.minExclusive, 1.0)
        self.assertEqual(r.maxExclusive, 10.0)
        self.assertIsNone(r.minInclusive)
        self.assertIsNone(r.maxInclusive)


class TestStaticAlarmRanges(unittest.TestCase):

    def test_all_levels(self):
        sar = xtceschema.StaticAlarmRanges(
            watchRange=xtceschema.FloatRange(minInclusive=-5.0, maxInclusive=5.0),
            warningRange=xtceschema.FloatRange(minInclusive=-6.0, maxInclusive=6.0),
            criticalRange=xtceschema.FloatRange(minInclusive=-10.0, maxInclusive=10.0),
            severeRange=xtceschema.FloatRange(minInclusive=-7.0, maxInclusive=7.0),
        )
        self.assertEqual(sar.watchRange.minInclusive, -5.0)
        self.assertEqual(sar.warningRange.maxInclusive, 6.0)
        self.assertEqual(sar.criticalRange.minInclusive, -10.0)
        self.assertEqual(sar.severeRange.maxInclusive, 7.0)
        self.assertIsNone(sar.distressRange)

    def test_partial_levels(self):
        sar = xtceschema.StaticAlarmRanges(
            warningRange=xtceschema.FloatRange(minInclusive=30.0),
        )
        self.assertIsNone(sar.watchRange)
        self.assertEqual(sar.warningRange.minInclusive, 30.0)


class TestAlarmConditions(unittest.TestCase):

    def test_with_boolean_expression(self):
        cond1 = xtceschema.Condition(
            parameterInstanceRef=xtceschema.ParameterInstanceRef(parameterRef='param_x'),
            comparisonOperator='<',
            value='-5.0',
        )
        cond2 = xtceschema.Condition(
            parameterInstanceRef=xtceschema.ParameterInstanceRef(parameterRef='param_x'),
            comparisonOperator='>',
            value='5.0',
        )
        ored = xtceschema.ORedConditions(condition=[cond1, cond2])
        anded = xtceschema.ANDedConditions(oRedConditions=[ored])
        bexpr = xtceschema.BooleanExpression(aNDedConditions=anded)
        mc = xtceschema.MatchCriteria(booleanExpression=bexpr)
        ac = xtceschema.AlarmConditions(watchAlarm=mc)

        self.assertIsNotNone(ac.watchAlarm)
        self.assertIsNone(ac.warningAlarm)
        be = ac.watchAlarm.booleanExpression
        self.assertEqual(len(be.aNDedConditions.oRedConditions), 1)
        self.assertEqual(len(be.aNDedConditions.oRedConditions[0].condition), 2)
        self.assertEqual(be.aNDedConditions.oRedConditions[0].condition[0].value, '-5.0')


class TestNumericAlarm(unittest.TestCase):

    def test_with_static_ranges(self):
        alarm = xtceschema.NumericAlarm(
            staticAlarmRanges=xtceschema.StaticAlarmRanges(
                watchRange=xtceschema.FloatRange(minInclusive=-5.0, maxInclusive=5.0),
            ),
        )
        self.assertIsNotNone(alarm.staticAlarmRanges)
        self.assertIsNone(alarm.alarmConditions)

    def test_with_alarm_conditions(self):
        alarm = xtceschema.NumericAlarm(
            alarmConditions=xtceschema.AlarmConditions(
                watchAlarm=xtceschema.MatchCriteria(
                    booleanExpression=xtceschema.BooleanExpression(
                        condition=xtceschema.Condition(
                            parameterInstanceRef=xtceschema.ParameterInstanceRef(parameterRef='p'),
                            comparisonOperator='>',
                            value='10',
                        ),
                    ),
                ),
            ),
        )
        self.assertIsNone(alarm.staticAlarmRanges)
        self.assertIsNotNone(alarm.alarmConditions)

    def test_on_float_parameter_type(self):
        fpt = xtceschema.FloatParameterType(
            name='test',
            defaultAlarm=xtceschema.NumericAlarm(
                staticAlarmRanges=xtceschema.StaticAlarmRanges(
                    warningRange=xtceschema.FloatRange(minInclusive=0.0, maxInclusive=100.0),
                ),
            ),
        )
        self.assertIsNotNone(fpt.defaultAlarm)
        self.assertEqual(fpt.defaultAlarm.staticAlarmRanges.warningRange.maxInclusive, 100.0)

    def test_on_integer_parameter_type(self):
        ipt = xtceschema.IntegerParameterType(
            name='test',
            defaultAlarm=xtceschema.NumericAlarm(
                staticAlarmRanges=xtceschema.StaticAlarmRanges(
                    criticalRange=xtceschema.FloatRange(minInclusive=-50.0, maxInclusive=50.0),
                ),
            ),
        )
        self.assertIsNotNone(ipt.defaultAlarm)
        self.assertEqual(ipt.defaultAlarm.staticAlarmRanges.criticalRange.minInclusive, -50.0)


class TestAlarmXMLParsing(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        xml_path = os.path.join(os.path.dirname(__file__),
            '..', 'xtce_c1db6124-8f44-4f79-9deb-79e40540dbff.xml')
        cls.ss = xtceschema.from_file(xml_path)

    def test_static_alarm_ranges_both_bounds(self):
        et = self.ss.get_entry_type('float64_alarmed__RepGetSatelliteState__est_rate_x')
        self.assertIsInstance(et, xtceschema.FloatParameterType)
        alarm = et.defaultAlarm
        self.assertIsNotNone(alarm)
        self.assertIsNotNone(alarm.staticAlarmRanges)
        self.assertIsNone(alarm.alarmConditions)

        sar = alarm.staticAlarmRanges
        self.assertEqual(sar.watchRange.minInclusive, -5.0)
        self.assertEqual(sar.watchRange.maxInclusive, 5.0)
        self.assertEqual(sar.warningRange.minInclusive, -6.0)
        self.assertEqual(sar.warningRange.maxInclusive, 6.0)
        self.assertEqual(sar.criticalRange.minInclusive, -10.0)
        self.assertEqual(sar.criticalRange.maxInclusive, 10.0)
        self.assertEqual(sar.severeRange.minInclusive, -7.0)
        self.assertEqual(sar.severeRange.maxInclusive, 7.0)

    def test_static_alarm_ranges_one_sided(self):
        et = self.ss.get_entry_type('float64_alarmed__RepGetSatelliteState__eps_battery_voltage')
        alarm = et.defaultAlarm
        sar = alarm.staticAlarmRanges
        self.assertEqual(sar.watchRange.minInclusive, 30.5)
        self.assertIsNone(sar.watchRange.maxInclusive)
        self.assertEqual(sar.warningRange.minInclusive, 30.0)
        self.assertEqual(sar.criticalRange.minInclusive, 28.0)
        self.assertEqual(sar.severeRange.minInclusive, 26.0)

    def test_alarm_conditions_structure(self):
        et = self.ss.get_entry_type('float64_alarmed__RepGetSatelliteState__est_rate_combined')
        alarm = et.defaultAlarm
        self.assertIsNone(alarm.staticAlarmRanges)
        self.assertIsNotNone(alarm.alarmConditions)

        ac = alarm.alarmConditions
        for level in ('watchAlarm', 'warningAlarm', 'criticalAlarm', 'severeAlarm'):
            mc = getattr(ac, level)
            self.assertIsNotNone(mc, f'{level} should be present')
            self.assertIsNotNone(mc.booleanExpression, f'{level} should have booleanExpression')
            be = mc.booleanExpression
            self.assertIsNotNone(be.aNDedConditions)
            self.assertEqual(len(be.aNDedConditions.oRedConditions), 3)

    def test_alarm_condition_values(self):
        et = self.ss.get_entry_type('float64_alarmed__RepGetSatelliteState__est_rate_combined')
        ac = et.defaultAlarm.alarmConditions
        be = ac.watchAlarm.booleanExpression
        first_or = be.aNDedConditions.oRedConditions[0]
        self.assertEqual(len(first_or.condition), 2)
        self.assertEqual(first_or.condition[0].parameterInstanceRef.parameterRef,
                         'RepGetSatelliteState__est_rate_x')
        self.assertEqual(first_or.condition[0].comparisonOperator, '<')
        self.assertEqual(first_or.condition[0].value, '-5.0')
        self.assertEqual(first_or.condition[1].comparisonOperator, '>')
        self.assertEqual(first_or.condition[1].value, '5.0')

    def test_no_alarm_on_regular_type(self):
        et = self.ss.get_entry_type('uint8')
        self.assertIsInstance(et, xtceschema.integerBaseType)
        self.assertIsNone(et.defaultAlarm)
