import os
import unittest

from bitarray import bitarray

from xtce import xtceschema, xtcemsg


_DIR = os.path.dirname(os.path.abspath(__file__))


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
                'ID': 0x10,
                'SecH': 0,
                'Type': 0,
                'Length': 0,
                'TimerStartStop': 1,
                'CheckSum': 12,
            },
        )

        want = bitarray('0001000000000000000000000000011110000011000000000000000001')
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



