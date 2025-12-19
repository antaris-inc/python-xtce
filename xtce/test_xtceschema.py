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
