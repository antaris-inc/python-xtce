import enum
import math
import os
import itertools
import typing

from bitarray import bitarray
import numpy as np
from pydantic import BaseModel, conlist
import xmlschema


_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_xtce_xsd():
    xsd_file = os.path.join(_DIR, 'xtce_1.2.xsd')
    return xmlschema.XMLSchema(xsd_file)


def _pad_bits(v: bitarray):
    n = len(v) % 8
    if n != 0:
        v = bitarray((8-n)*[0]) + v
    return v


class xmlnode:
    def __init__(self, node: list):
        # node should be the output of a doc parsed to_dict with converter=xmlschema.JsonMlConverter
        self.tag = node.pop(0)
        self.attrs = node.pop(0) if (node and isinstance(node[0], dict)) else dict()
        self.children = []

        for v in node:
            if isinstance(v, list):
                self.children.append(xmlnode(v))
            else:
                self.attrs['value'] = v

    def __repr__(self):
        return f'<xtce.schema.xmlnode tag={self.tag}>'



class BaseType(BaseModel):

    ordered_children: list[typing.Any] = None

    @classmethod
    def _from_xmlnode(cls, node: xmlnode):
        def init_child(child_cls, child_node):
            # recursively parse XML for known object types
            if issubclass(child_cls, BaseType):
                try:
                    return child_cls._from_xmlnode(child_node)
                except Exception as exc:
                    raise Exception(f'failed loading {child_cls} field: {exc}')

            # fall back to direct instantiation for basic types like str
            else:
                return child_cls(child_node.attrs.get('value'))

        fields = node.attrs

        for child in node.children:
            # xmlschema will produce None values in certain cases
            #if child_value is None:
            #    continue

            # e.g. map xtce:IntegerDataEncoding to integerDataEncoding
            child_field = child.tag[5].lower() + child.tag[6:]

            try:
                # find pydantic.BaseModel field type via annotation attribute
                child_field_cls = cls.model_fields[child_field].annotation
            except KeyError:
                raise Exception(f'{cls} does not support child field "{child_field}"')

            #TODO(bcwaldon): find a more elegant way to detect a list-type pydantic.BaseModel.field
            try:
                child_field_cls = child_field_cls.__args__[0]
            except: # Not a list type
                fields[child_field] = init_child(child_field_cls, child)

            else: # Is a list type
                child_field_value = init_child(child_field_cls, child)

                if not fields.get(child_field):
                    fields[child_field] = []
                fields[child_field].append(child_field_value)

                # Track list-type children in order
                if not fields.get('ordered_children'):
                    fields['ordered_children'] = []
                fields['ordered_children'].append(child_field_value)

        return cls(**fields)


class Unit(BaseType):
    power: float
    factor: int
    description: str
    form: str
    value: str


class UnitSet(BaseType):
    unit: list[Unit] = None


class Term(BaseType):
    coefficient: float
    exponent: int


class PolynomialCalibrator(BaseType):
    # NOTE(bcwaldon): assumed that terms are sorted by exponent
    # starting at zero and containing no gaps in the sequence
    term: conlist(Term, min_length=2)

    def calibrate(self, x_value) -> float:
        return sum([t.coefficient*math.pow(float(x_value), t.exponent) for t in self.term])

    def uncalibrate(self, y_value) -> int:
        # linear equation
        if len(self.term) == 2:
             x_value = (-1.0*self.term[0].coefficient + float(y_value)) / self.term[1].coefficient
        else:
            # at least 3 coefficients
            coefficients = [t.coefficient for t in self.term]
            coefficients[0] -= y_value

            roots = np.roots(coefficients[::-1])

            x_value = roots[-1].real

        #NOTE(bcwaldon): rounding off decoded value due
        # to imprecision in handling floats
        x_value = round(x_value, 12)

        return int(x_value)


class DefaultCalibrator(BaseType):
    polynomialCalibrator: PolynomialCalibrator

    #TODO(bcwaldon): other calibrators not yet implemented

    def calibrate(self, value):
        return self.polynomialCalibrator.calibrate(value)

    def uncalibrate(self, value):
        return self.polynomialCalibrator.uncalibrate(value)


class BitOrderEnum(str, enum.Enum):
    MSB = 'mostSignificantBitFirst'

    #TODO(bcwaldon): not yet implemented
    #LSB = 'leastSignificantBitFirst'


class ByteOrderEnum(str, enum.Enum):
    MSB = 'mostSignificantByteFirst'

    #TODO(bcwaldon): not yet implemented
    #LSB = 'leastSignificantByteFirst'


class SignedEnum(str, enum.Enum):
    unsigned = 'unsigned'
    twosComplement = 'twosComplement'

    #TODO(bcwaldon): not yet implemented
    #signMagnitude = 'signMagnitude'
    #onesComplement = 'onesComplement'
    #BCD = 'BCD'
    #packedBCD = 'packedBCD'


class SizeInBits(BaseType):
    fixedValue: int = 32


class BinaryEncoding(BaseType):
    bitOrder: str = BitOrderEnum.MSB
    byteOrder: str = ByteOrderEnum.MSB
    sizeInBits: SizeInBits


class IntegerDataEncoding(BaseType):
    encoding: SignedEnum = SignedEnum.unsigned
    sizeInBits: int = 8
    bitOrder: str = BitOrderEnum.MSB
    byteOrder: str = ByteOrderEnum.MSB

    defaultCalibrator: DefaultCalibrator = None

    @property
    def _signed(self) -> bool:
        return self.encoding == SignedEnum.twosComplement

    def encode(self, value: [int | float]) -> bitarray:
        if self.defaultCalibrator:
            value = int(self.defaultCalibrator.uncalibrate(value))
        elif isinstance(value, float):
            raise ValueError('unable to encode float as integer without calibrator')

        size_in_bytes = int(math.ceil(self.sizeInBits/8))
        encoded_bytes = bytearray(value.to_bytes(size_in_bytes, signed=self._signed, byteorder='big'))
        encoded_bits = bitarray(encoded_bytes)
        field_bits = encoded_bits[-self.sizeInBits:]
        return field_bits

    def decode(self, value: bitarray) -> [int | float]:
        if len(value) != self.sizeInBits:
            raise ValueError('field size mismatch')

        dec = int.from_bytes(_pad_bits(value).tobytes(), signed=self._signed, byteorder='big')

        if self.defaultCalibrator:
            dec = self.defaultCalibrator.calibrate(dec)
        elif isinstance(value, float):
            raise ValueError('unable to decode float from integer without calibrator')

        return dec


class integerBaseType(BaseType):
    name: str
    signed: bool = True
    #TODO(bcwaldon): confirm input values respect this field size
    sizeInBits: int = 32
    unitSet: UnitSet = None

    integerDataEncoding: IntegerDataEncoding = None

    @property
    def _encoding(self):
        if self.integerDataEncoding:
            return self.integerDataEncoding

        return IntegerDataEncoding()

    def encode(self, value: int) -> bytearray:
        return self._encoding.encode(value)

    @property
    def encoded_bit_length(self) -> int:
        return self._encoding.sizeInBits

    def decode(self, value: bytearray) -> int:
        return self._encoding.decode(value)


class IntegerParameterType(integerBaseType):
    pass


class IntegerArgumentType(integerBaseType):
    pass


class floatBaseType(BaseType):
    name: str
    sizeInBits: int = 64
    unitSet: UnitSet = None

    integerDataEncoding: IntegerDataEncoding = None


    @property
    def _encoding(self):
        if self.integerDataEncoding:
            return self.integerDataEncoding

        return IntegerDataEncoding()

    @property
    def encoded_bit_length(self) -> int:
        return self._encoding.sizeInBits

    def encode(self, value: float) -> bitarray:
        return self._encoding.encode(value)

    def decode(self, value: bitarray) -> float:
        #NOTE(bcwaldon): rounding off decoded value due
        # to imprecision in handling floats
        return round(self._encoding.decode(value), 12)


class FloatParameterType(floatBaseType):
    pass


class FloatArgumentType(floatBaseType):
    pass


class Comparison(BaseType):
    comparisonOperator: str
    value: str
    instance: int
    useCalibratedValue: bool
    parameterRef: str


class ComparisonList(BaseType):
    comparison: list[Comparison] = None


class RestrictionCriteria(BaseType):
    comparisonList: ComparisonList = None
    comparison: Comparison = None


class IncludeCondition(BaseType):
    comparison: ComparisonList = None


class Enumeration(BaseType):
    value: int
    label: str


class EnumerationList(BaseType):
    enumeration: list[Enumeration]


class enumeratedBaseType(BaseType):
    name: str
    initialValue: str = None
    enumerationList: EnumerationList
    integerDataEncoding: IntegerDataEncoding = None
    unitSet: UnitSet = None

    @property
    def _encoding(self):
        if self.integerDataEncoding:
            return self.integerDataEncoding

        return IntegerDataEncoding()

    def encode(self, value: int) -> bitarray:
        return self._encoding.encode(value)

    @property
    def encoded_bit_length(self) -> int:
        return self._encoding.sizeInBits

    def decode(self, value: bitarray) -> int:
        return self._encoding.decode(value)


class EnumeratedParameterType(enumeratedBaseType):
    pass


class EnumeratedArgumentType(enumeratedBaseType):
    pass


class OffsetFrom(BaseType):
    parameterRef: str


class ReferenceTime(BaseType):
    epoch: str = None
    offsetFrom: OffsetFrom = None


class Encoding(BaseType):
    units: str
    scale: float
    offset: float
    integerDataEncoding: IntegerDataEncoding


class absoluteTimeBaseType(BaseType):
    name: str
    shortDescription: str = ''
    referenceTime: ReferenceTime
    encoding: Encoding = None

    #TODO(bcwaldon): need to encode this field properly. Currently just
    # copied similar behavior to IntegerBaseType

    @property
    def _encoding(self):
        return IntegerDataEncoding(
                encoding=SignedEnum.unsigned,
                sizeInBits=32,
        )

    def encode(self, value: int) -> bitarray:
        return self._encoding.encode(value)

    @property
    def encoded_bit_length(self) -> int:
        return self._encoding.sizeInBits

    def decode(self, value: bitarray) -> int:
        return self._encoding.decode(value)


class AbsoluteTimeParameterType(absoluteTimeBaseType):
    pass


class AbsoluteTimeArgumentType(absoluteTimeBaseType):
    pass


class ParameterProperties(BaseType):
    systemName: str = ''
    dataSource: str = ''
    persistence: bool = True
    readOnly: bool = False


class Parameter(BaseType):
    name: str
    parameterTypeRef: str
    parameterProperties: ParameterProperties = None


class ParameterRefEntry(BaseType):
    parameterRef: str


class ArgumentRefEntry(BaseType):
    argumentRef: str


class ContainerRefEntry(BaseType):
    containerRef: str
    includeCondition: ComparisonList = None


class FixedValueEntry(BaseType):
    binaryValue: str # hex-encoded byte string
    sizeInBits: int

    @property
    def value(self) -> bitarray:
        return bitarray(bytearray.fromhex(self.binaryValue))[-self.sizeInBits:]


class EntryList(BaseType):
    argumentRefEntry: list[ArgumentRefEntry] = None
    parameterRefEntry: list[ParameterRefEntry] = None
    containerRefEntry: list[ContainerRefEntry] = None
    fixedValueEntry: list[FixedValueEntry] = None


class BaseContainer(BaseType):
    containerRef: str
    restrictionCriteria: RestrictionCriteria = None


class AncillaryData(BaseType):
    name: str
    mimeType: str
    value: str


class AncillaryDataSet(BaseType):
    ancillaryData: list[AncillaryData]


class SequenceContainer(BaseType):
    name: str
    abstract: bool = False
    longDescription: str = ''
    entryList: EntryList = None
    baseContainer: BaseContainer = None
    ancillaryDataSet: AncillaryDataSet = None


class CommandContainer(BaseType):
    name: str
    longDescription: str = ''
    entryList: EntryList = None
    baseContainer: BaseContainer = None
    ancillaryDataSet: AncillaryDataSet = None
    binaryEncoding: BinaryEncoding = None


class BaseMetaCommand(BaseType):
    metaCommandRef: str


class Argument(BaseType):
    name: str
    argumentTypeRef: str


class ArgumentList(BaseType):
    argument: list[Argument]


class DefaultConsequence(BaseType):
    consequenceLevel: str


class CheckWindow(BaseType):
    timeToStopChecking: str
    timeWindowIsRelativeTo: str


class Verifier(BaseType):
    containerRef: str = None
    checkWindow: CheckWindow = None
    comparison: Comparison = None


#NOTE(bcwaldon): not sure that completeVerifier is being parsed correctly
class VerifierSet(BaseType):
    completeVerifier: list[Verifier]
    failedVerifier: Verifier


class ParameterToSet(BaseType):
    parameterRef: str
    setOnVerification: str
    newValue: str # hex-encoded bytes


class ParameterToSetList(BaseType):
    parameterToSet: list[ParameterToSet]


class DefaultSignificance(BaseType):
    consequenceLevel: str


class MetaCommand(BaseType):
    name: str = ''
    abstract: bool = False
    longDescription: str = ''
    systemName: str = ''
    commandContainer: CommandContainer = None
    baseMetaCommand: BaseMetaCommand = None
    argumentList: ArgumentList = None
    #argument: list[Argument] = None
    defaultConsequence: DefaultConsequence = None
    defaultSignificance: DefaultSignificance = None
    verifierSet: VerifierSet = None
    parameterToSetList: ParameterToSetList = None


class ParameterTypeSet(BaseType):
    integerParameterType: list[IntegerParameterType] = None
    floatParameterType: list[FloatParameterType] = None
    absoluteTimeParameterType: list[AbsoluteTimeParameterType] = None
    enumeratedParameterType: list[EnumeratedParameterType] = None


class ParameterSet(BaseType):
    parameter: list[Parameter]


class ContainerSet(BaseType):
    sequenceContainer: list[SequenceContainer]


class TelemetryMetaData(BaseType):
    parameterTypeSet: ParameterTypeSet = None
    parameterSet: ParameterSet = None
    containerSet: ContainerSet = None


class ArgumentTypeSet(BaseType):
    integerArgumentType: list[IntegerArgumentType] = None
    floatArgumentType: list[FloatArgumentType] = None
    absoluteTimeArgumentType: list[AbsoluteTimeArgumentType] = None
    enumeratedArgumentType: list[EnumeratedArgumentType] = None


class MetaCommandSet(BaseType):
    metaCommand: list[MetaCommand]


class CommandMetaData(BaseType):
    parameterTypeSet: ParameterTypeSet = None
    parameterSet: ParameterSet = None
    argumentTypeSet: ArgumentTypeSet = None
    metaCommandSet: MetaCommandSet = None


class SpaceSystem(BaseType):
    name: str
    longDescription: str = ''
    header: str = ''
    telemetryMetaData: TelemetryMetaData
    commandMetaData: CommandMetaData

    def get_entry_type(self, name):
        parameter_type_sets = (
            self.telemetryMetaData.parameterTypeSet,
            self.commandMetaData.parameterTypeSet,
        )
        objs = list(itertools.chain(
            *[
                itertools.chain(
                    ts.integerParameterType or [],
                    ts.floatParameterType or [],
                    ts.absoluteTimeParameterType or [],
                    ts.enumeratedParameterType or [],
                ) for ts in parameter_type_sets if ts
            ],
            self.commandMetaData.argumentTypeSet.integerArgumentType or [],
            self.commandMetaData.argumentTypeSet.enumeratedArgumentType or [],
        ))
        idx = dict([(o.name, o) for o in objs])
        try:
            return idx[name]
        except KeyError:
            raise ValueError(f"unknown entry type: {name}")

    def get_parameter(self, name):
        paramsets = (
                self.telemetryMetaData.parameterSet,
                self.commandMetaData.parameterSet,
        )
        objs = itertools.chain(*[ps.parameter for ps in paramsets if ps])
        idx = dict([(o.name, o) for o in objs])
        try:
            return idx[name]
        except KeyError:
            raise ValueError(f"unknown Parameter: {name}")

    def get_sequence_container(self, name):
        idx = dict([(o.name, o) for o in self.telemetryMetaData.containerSet.sequenceContainer])
        try:
            return idx[name]
        except KeyError:
            raise ValueError(f"unknown SequenceContainer: {name}")

    def get_meta_command(self, name):
        idx = dict([(o.name, o) for o in self.commandMetaData.metaCommandSet.metaCommand])
        try:
            return idx[name]
        except KeyError:
            raise ValueError(f"unknown MetaCommand: {name}")

    # retrieve a CommandContainer or SequenceContainer by name
    def get_container(self, name):
        objs = itertools.chain(
            [c.commandContainer for c in itertools.chain(self.commandMetaData.metaCommandSet.metaCommand)],
            self.telemetryMetaData.containerSet.sequenceContainer,
        )
        idx = dict([(o.name, o) for o in objs])
        try:
            return idx[name]
        except KeyError:
            raise ValueError(f"unknown container: {name}")


def from_file(file_location: str):
    xs = _load_xtce_xsd()

    with open(file_location, 'rb') as f:
        doc = f.read()

    node = xmlnode(xs.to_dict(doc, converter=xmlschema.JsonMLConverter, path='/xtce:SpaceSystem'))
    return SpaceSystem._from_xmlnode(node)
