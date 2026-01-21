import os
import unittest

from bitarray import bitarray

from xtce import xtceschema, xtcemsg


_DIR = os.path.dirname(os.path.abspath(__file__))


class TestLoad(unittest.TestCase):

    def test_from_bytes(self):
        loc = os.path.join(_DIR, './ccsds_660x1g2.xml')
        with open(loc, 'rb') as f:
            xtceschema.from_bytes(f.read())


class TestCCSDS_660x1g2(unittest.TestCase):
    loc = os.path.join(_DIR, './ccsds_660x1g2.xml')

    def test_Header_SecH0(self):
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        tm = xtcemsg.Message(
            message_type=ss.get_sequence_container('Header'),
            entries={
                'ID': 0x10,
                'SecH': 0,
                'Type': 1,
                'Length': 2,
            },
        )

        want = bitarray('00010000010000000000000010')
        got = enc.encode(tm)
        self.assertEqual(want, got)

        tm2 = enc.decode(tm.message_type, got)
        self.assertEqual(tm.entries, tm2.entries)

    def test_Header_SecH1(self):
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        tm = xtcemsg.Message(
            message_type=ss.get_sequence_container('Header'),
            entries={
                'ID': 0x10,
                'SecH': 1,
                'Type': 1,
                'Length': 2,
                'Seconds': 44,
                'MilliSeconds': 55,
            },
        )

        want = bitarray('000100001100000000000000100000000000000000000000000010110000000000000000000000000000110111')
        got = enc.encode(tm)
        self.assertEqual(want, got)

        tm2 = enc.decode(tm.message_type, got)
        self.assertEqual(tm.entries, tm2.entries)

    def test_PWHTMR_encode_and_decode(self):
        ss = xtceschema.from_file(self.loc)
        self.assertEqual(ss.name, 'SpaceVehicle')

        enc = xtcemsg.SpaceSystemEncoder(ss)

        cmd = xtcemsg.Message(
            message_type=ss.get_meta_command('PWHTMR'),
            entries={
                'ID': 16, # will be overridden to 255 due to restriction criteria
                'SecH': 0,
                'Type': 0,
                'Length': 0,
                'TimerStartStop': 1,
                'CheckSum': 12,
            },
        )

        want = bitarray('1111111100000000000000000000011110000011000000000000000001')
        got = enc.encode(cmd)
        self.assertEqual(want, got)

        cmd2 = enc.decode(cmd.message_type, got)
        self.assertEqual(cmd.entries, cmd2.entries)

    def test_PWHTMR_decode_abstract(self):
        ss = xtceschema.from_file(self.loc)
        self.assertEqual(ss.name, 'SpaceVehicle')

        enc = xtcemsg.SpaceSystemEncoder(ss)

        want = xtcemsg.Message(
            message_type=ss.get_meta_command('PWHTMR'),
            entries={
                'ID': 255, # main criteria to identify correct message type
                'SecH': 0,
                'Type': 0,
                'Length': 0,
                'TimerStartStop': 1,
                'CheckSum': 12,
            },
        )

        arg = bitarray('1111111100000000000000000000011110000011000000000000000001')

        # Rely on automated matching through abstract container based on restriction criteria
        got = enc.decode(ss.get_sequence_container('Header'), arg)

        self.assertEqual(want, got)


class TestCCSDS_660x2g2(unittest.TestCase):

    loc = os.path.join(_DIR, './ccsds_660x2g2.xml')

    def test_CCSDSPacket(self):
        ss = xtceschema.from_file(self.loc)
        self.assertEqual(ss.name, 'GovSat')

        enc = xtcemsg.SpaceSystemEncoder(ss)

        tm = xtcemsg.Message(
            message_type=ss.get_sequence_container('CCSDSPacket'),
            entries={
                'CCSDSVersion': 0,
                'CCSDSType': 1,
                'CCSDSSecH': 0,
                'CCSDSAPID': 130,
                'CCSDSGroupFlags': 0,
                'CCSDSSourceSequenceCount': 32,
                'CCSDSPacketLength': 45, # how do we set this dynamically?
            },
        )

        want = bitarray('000100001000001000000000001000000000000000101101')
        got = enc.encode(tm)
        self.assertEqual(want, got)

        tm2 = enc.decode(tm.message_type, got)
        self.assertEqual(tm.entries, tm2.entries)

    def test_PM1Enable_Logging_encode_and_decode(self):
        ss = xtceschema.from_file(self.loc)
        self.assertEqual(ss.name, 'GovSat')

        enc = xtcemsg.SpaceSystemEncoder(ss)

        cmd = xtcemsg.Message(
            message_type=ss.get_meta_command('PM1Enable_Logging'),
            entries={
                'CCSDSVersion': 0,
                'CCSDSType': 1,
                'CCSDSSecH': 0,
                'CCSDSAPID': 130,
                'CCSDSGroupFlags': 0,
                'CCSDSSourceSequenceCount': 32,
                'CCSDSPacketLength': 45, # how do we set this dynamically?
                'PM1Msg_Type': 12,
                'PM1Address': 241,
                'PM1Port': 10,
                'PM1Sensor_ID': 11114,
            },
        )

        want = bitarray('0001000010000010000000000010000000000000001011010000110000000000000000000000000011110001000000000000101000000000000000000010101101101010')
        got = enc.encode(cmd)
        self.assertEqual(want, got)

        cmd2 = enc.decode(cmd.message_type, got)
        self.assertEqual(cmd.entries, cmd2.entries)

    def test_PM1Enable_Logging_decode_abstract_two_levels(self):
        ss = xtceschema.from_file(self.loc)
        self.assertEqual(ss.name, 'GovSat')

        enc = xtcemsg.SpaceSystemEncoder(ss)

        want = xtcemsg.Message(
            message_type=ss.get_meta_command('PM1Enable_Logging'),
            entries={
                'CCSDSVersion': 0,
                'CCSDSType': 1,
                'CCSDSSecH': 0,
                'CCSDSAPID': 130,
                'CCSDSGroupFlags': 0,
                'CCSDSSourceSequenceCount': 32,
                'CCSDSPacketLength': 45, # how do we set this dynamically?
                'PM1Msg_Type': 12,
                'PM1Address': 241,
                'PM1Port': 10,
                'PM1Sensor_ID': 11114,
            },
        )

        arg = bitarray('0001000010000010000000000010000000000000001011010000110000000000000000000000000011110001000000000000101000000000000000000010101101101010')

        # tests decoding of a chain of inheritance with two levels of abstraction
        got = enc.decode(ss.get_sequence_container('CCSDSPacket'), arg)
        self.assertEqual(want, got)

    def test_PM1Enable_Logging_decode_abstract_intermediate(self):
        ss = xtceschema.from_file(self.loc)
        self.assertEqual(ss.name, 'GovSat')

        enc = xtcemsg.SpaceSystemEncoder(ss)

        want = xtcemsg.Message(
            message_type=ss.get_meta_command('PM1Enable_Logging'),
            entries={
                'CCSDSVersion': 0,
                'CCSDSType': 1,
                'CCSDSSecH': 0,
                'CCSDSAPID': 130,
                'CCSDSGroupFlags': 0,
                'CCSDSSourceSequenceCount': 32,
                'CCSDSPacketLength': 45, # how do we set this dynamically?
                'PM1Msg_Type': 12,
                'PM1Address': 241,
                'PM1Port': 10,
                'PM1Sensor_ID': 11114,
            },
        )

        arg = bitarray('0001000010000010000000000010000000000000001011010000110000000000000000000000000011110001000000000000101000000000000000000010101101101010')

        # tests decoding from an intermediate level in the inheritance chain
        got = enc.decode(ss.get_meta_command('CCSDSCommand'), arg)
        self.assertEqual(want, got)


class TestBogusSat(unittest.TestCase):
    parent = os.path.join(_DIR, './BogusSAT')
    loc = os.path.join(_DIR, './BogusSAT/BogusSAT_modified.xml')

    def test_sanity(self):
        ss = xtceschema.from_file(self.loc)
        self.assertEqual(ss.name, 'BogusSAT')


class TestUnittest(unittest.TestCase):
    loc = os.path.join(_DIR, './unittest.xml')

    # Tests for a branching decode with multiple layers
    # of nested restriction criteria
    def test_decode_abstract_branching(self):
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        arg = bitarray(bytes([2, 10, 35, 99, 42]))

        got = enc.decode(ss.get_sequence_container('MessageBase'), arg)

        want = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_Ping'),
            entries={
                'MessageType': 2,
                'MessageSource': 35,
                'MessageDestination': 10,
                'MessageID': 99,
                'Nonce': 42,
            }
        )

        self.assertEqual(want, got)

    # Ensure restriction criteria cause entries to be set automatically on encode.
    def test_encode_restriction_criteria(self):
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        msg = xtcemsg.Message(
            message_type=ss.get_meta_command('Command_Ping'),
            entries={
                'MessageSource': 36,
                'MessageDestination': 11,
                'Intermediate': 12,
                'Nonce': 42,
                # MessageType (1) and MessageID (99) should be set automatically
            }
        )
        got = enc.encode(msg)

        want = bitarray(bytes([1, 11, 36, 99, 12, 42]))

        self.assertEqual(want, got)

    # Ensure concrete message will be decoded properly even if no arguments are
    # present and the message could be decoded "correctly" as abstract.
    def test_decode_noarg(self):
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        arg = bitarray(bytes([1, 11, 32, 98, 12]))

        got = enc.decode(ss.get_sequence_container('MessageBase'), arg, require_concrete=True)

        want = xtcemsg.Message(
            message_type=ss.get_meta_command('Command_NOARG'),
            entries={
                'MessageType': 1,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 98,
                'Intermediate': 12,
            }
        )

        self.assertEqual(want, got)

    def test_decode_fixed_array(self):
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        arg = bitarray(bytes([2, 11, 32, 97, 5, 6, 7, 8]))

        got = enc.decode(ss.get_sequence_container('Reply_BatteryVoltage'), arg)

        want = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_BatteryVoltage'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 97,
                'BatteryVoltage': [5, 6, 7, 8],
            }
        )

        self.assertEqual(want, got)

    def test_encode_fixed_array(self):
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        msg = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_BatteryVoltage'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 97,
                'BatteryVoltage': [1, 2, 3, 4],
            }
        )
        got = enc.encode(msg)

        want = bitarray(bytes([2, 11, 32, 97, 1, 2, 3, 4]))

        self.assertEqual(want, got)

    def test_decode_binary_data(self):
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        arg = bitarray(bytes([2, 11, 32, 95, 24, 11, 32, 97, 42]))

        got = enc.decode(ss.get_sequence_container('Reply_Blob'), arg)

        want = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_Blob'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 95,
                'BDataLen': 24,
                'BData': bitarray(bytes([11, 32, 97])),
                'Nonce': 42,
            }
        )

        self.assertEqual(want, got)

    def test_encode_binary_data(self):
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        msg = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_Blob'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 95,
                'BDataLen': 24,
                'BData': bitarray(bytes([11, 32, 97])),
                'Nonce': 42,
            }
        )

        got = enc.encode(msg)
        want = bitarray(bytes([2, 11, 32, 95, 24, 11, 32, 97, 42]))

        self.assertEqual(want, got)

    def test_decode_dynamic_array(self):
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        # Message: MessageType=2, Dest=11, Src=32, ID=94, ArrayCount=3 (3 elements), Data=[10,20,30]
        arg = bitarray(bytes([2, 11, 32, 94, 3, 10, 20, 30]))

        got = enc.decode(ss.get_sequence_container('Reply_DynamicArray'), arg)

        want = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_DynamicArray'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 94,
                'ArrayCount': 3,
                'DynamicData': [10, 20, 30],
            }
        )

        self.assertEqual(want, got)

    def test_encode_dynamic_array(self):
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        msg = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_DynamicArray'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 94,
                'ArrayCount': 5,
                'DynamicData': [1, 2, 3, 4, 5],
            }
        )

        got = enc.encode(msg)
        want = bitarray(bytes([2, 11, 32, 94, 5, 1, 2, 3, 4, 5]))

        self.assertEqual(want, got)

    def test_decode_fixed_float_array(self):
        """Test decoding a fixed-size array of floats using IntegerDataEncoding with polynomial calibration.

        The ScaledTemperature type uses 16-bit integers with calibration: calibrated = 0.1 * raw
        FixedFloatArray has 3 elements (indices 0-2).
        """
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        # Message: MessageType=2, Dest=11, Src=32, ID=92
        # Raw values: 100 (0x0064), 200 (0x00C8), 300 (0x012C) as 16-bit big-endian integers
        arg = bitarray(bytes([2, 11, 32, 92, 0x00, 0x64, 0x00, 0xC8, 0x01, 0x2C]))

        got = enc.decode(ss.get_sequence_container('Reply_FixedFloatArray'), arg)

        want = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_FixedFloatArray'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 92,
                'FixedTemperatures': [10.0, 20.0, 30.0],
            }
        )

        self.assertEqual(want, got)

    def test_encode_fixed_float_array(self):
        """Test encoding a fixed-size array of floats using IntegerDataEncoding with polynomial calibration.

        The ScaledTemperature type uses 16-bit integers with calibration: calibrated = 0.1 * raw
        So calibrated values [10.0, 20.0, 30.0] are encoded as raw values [100, 200, 300]
        """
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        msg = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_FixedFloatArray'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 92,
                'FixedTemperatures': [10.0, 20.0, 30.0],
            }
        )

        got = enc.encode(msg)
        # Raw values: 100 (0x0064), 200 (0x00C8), 300 (0x012C) as 16-bit big-endian integers
        want = bitarray(bytes([2, 11, 32, 92, 0x00, 0x64, 0x00, 0xC8, 0x01, 0x2C]))

        self.assertEqual(want, got)

    def test_decode_dynamic_float_array(self):
        """Test decoding a dynamic array of floats using IntegerDataEncoding with polynomial calibration.

        The ScaledTemperature type uses 16-bit integers with calibration: calibrated = 0.1 * raw
        So raw values [100, 200, 300] become calibrated values [10.0, 20.0, 30.0]
        """
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        # Message: MessageType=2, Dest=11, Src=32, ID=93, FloatArrayCount=3 (3 elements)
        # Raw values: 100 (0x0064), 200 (0x00C8), 300 (0x012C) as 16-bit big-endian integers
        arg = bitarray(bytes([2, 11, 32, 93, 3, 0x00, 0x64, 0x00, 0xC8, 0x01, 0x2C]))

        got = enc.decode(ss.get_sequence_container('Reply_DynamicFloatArray'), arg)

        want = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_DynamicFloatArray'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 93,
                'FloatArrayCount': 3,
                'FloatTemperatures': [10.0, 20.0, 30.0],
            }
        )

        self.assertEqual(want, got)

    def test_encode_dynamic_float_array(self):
        """Test encoding a dynamic array of floats using IntegerDataEncoding with polynomial calibration.

        The ScaledTemperature type uses 16-bit integers with calibration: calibrated = 0.1 * raw
        So calibrated values [10.0, 20.0] are encoded as raw values [100, 200]
        """
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        msg = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_DynamicFloatArray'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 93,
                'FloatArrayCount': 2,
                'FloatTemperatures': [10.0, 20.0],
            }
        )

        got = enc.encode(msg)
        # FloatArrayCount=2 means 2 elements
        # Raw values: 100 (0x0064), 200 (0x00C8) as 16-bit big-endian integers
        want = bitarray(bytes([2, 11, 32, 93, 2, 0x00, 0x64, 0x00, 0xC8]))

        self.assertEqual(want, got)

    def test_decode_dynamic_array_zero_size(self):
        """Test decoding a dynamic array when the array size is zero."""
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        # Message: MessageType=2, Dest=11, Src=32, ID=94, ArrayCount=0 (0 elements)
        arg = bitarray(bytes([2, 11, 32, 94, 0]))

        got = enc.decode(ss.get_sequence_container('Reply_DynamicArray'), arg)

        want = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_DynamicArray'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 94,
                'ArrayCount': 0,
                'DynamicData': [],
            }
        )

        self.assertEqual(want, got)

    def test_encode_dynamic_array_zero_size(self):
        """Test encoding a dynamic array when the array size is zero."""
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        msg = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_DynamicArray'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 94,
                'ArrayCount': 0,
                'DynamicData': [],
            }
        )

        got = enc.encode(msg)
        want = bitarray(bytes([2, 11, 32, 94, 0]))

        self.assertEqual(want, got)

    def test_decode_string_parameter(self):
        """Test decoding a message with a string parameter.

        The StatusMessage type is a UTF-8 encoded string with 64-bit (8 byte) fixed size.
        """
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        # Message: MessageType=2, Dest=11, Src=32, ID=91, StatusMessage="Hello" (8 bytes, null-padded)
        arg = bitarray(bytes([2, 11, 32, 91]) + b'Hello\x00\x00\x00')

        got = enc.decode(ss.get_sequence_container('Reply_Status'), arg)

        want = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_Status'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 91,
                'StatusMessage': 'Hello',
            }
        )

        self.assertEqual(want, got)

    def test_encode_string_parameter(self):
        """Test encoding a message with a string parameter.

        The StatusMessage type is a UTF-8 encoded string with 64-bit (8 byte) fixed size.
        """
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        msg = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_Status'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 91,
                'StatusMessage': 'Hello',
            }
        )

        got = enc.encode(msg)
        # MessageType=2, Dest=11, Src=32, ID=91, StatusMessage="Hello" (8 bytes, null-padded)
        want = bitarray(bytes([2, 11, 32, 91]) + b'Hello\x00\x00\x00')

        self.assertEqual(want, got)

    def test_encode_decode_string_roundtrip(self):
        """Test that encoding and decoding a string message produces the same result."""
        ss = xtceschema.from_file(self.loc)

        enc = xtcemsg.SpaceSystemEncoder(ss)

        msg = xtcemsg.Message(
            message_type=ss.get_sequence_container('Reply_Status'),
            entries={
                'MessageType': 2,
                'MessageSource': 32,
                'MessageDestination': 11,
                'MessageID': 91,
                'StatusMessage': 'OK',
            }
        )

        encoded = enc.encode(msg)
        decoded = enc.decode(msg.message_type, encoded)

        self.assertEqual(msg.entries, decoded.entries)
