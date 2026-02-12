import enum
import functools
import math
import os
import itertools
import typing

from bitarray import bitarray
import numpy as np
from pydantic import BaseModel, conlist, ConfigDict
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
                #NOTE(bcwaldon): should enforce this once all examples contained in
                # this repository are fully supported
                #raise Exception(f'{cls} does not support child field "{child_field}"')
                continue

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
    description: str = None
    power: float
    factor: int
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
    polynomialCalibrator: PolynomialCalibrator = None

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
    signMagnitude = 'signMagnitude'
    IEEE754_1985 = 'IEEE754_1985'
    MILSTD_1750A = 'MILSTD_1750A'
    onesComplement = 'onesComplement'
    BCD = 'BCD'
    packedBCD = 'packedBCD'


class Fixed(BaseType):
    fixedValue: int


class ParameterInstanceRef(BaseType):
    parameterRef: str


class ArgumentInstanceRef(BaseType):
    argumentRef: str


class DynamicValue(BaseType):
    parameterInstanceRef: ParameterInstanceRef = None
    argumentInstanceRef: ArgumentInstanceRef = None


class SizeInBits(BaseType):
    fixed: Fixed = None
    fixedValue: int = None
    dynamicValue: DynamicValue = None
    terminationChar: str = None  # hexBinary string like "00" or "0D0A"

    def get_fixed_value(self) -> int:
        if self.fixedValue:
            return self.fixedValue
        if self.fixed.fixedValue:
            return self.fixed.fixedValue
        raise ValueError('no fixed value specified')


class VariableStringType(BaseType):
    """Represents the Variable element for variable-length strings in XTCE."""
    maxSizeInBits: int
    dynamicValue: DynamicValue = None
    terminationChar: str = "00"  # hexBinary string like "00"



class FloatDataEncoding(BaseType):
    encoding: SignedEnum = SignedEnum.unsigned
    sizeInBits: int = 8
    changeThreshold: float = None

    #NOTE(bcwaldon): not implemented yet


class IntegerDataEncoding(BaseType):
    encoding: SignedEnum = SignedEnum.unsigned
    bitOrder: str = BitOrderEnum.MSB
    byteOrder: str = ByteOrderEnum.MSB

    # NOTE(bcwaldon): XTCE explicitly defines sizeInBits as a number, not a SizeInBits object used elsewhere
    sizeInBits: int = 8

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
        try:
            encoded_bytes = bytearray(value.to_bytes(size_in_bytes, signed=self._signed, byteorder='big'))
        except Exception as exc:
            raise Exception(f'failed encoding value {value} into {size_in_bytes}B: {exc}')
        encoded_bits = bitarray(encoded_bytes)
        field_bits = encoded_bits[-self.sizeInBits:]
        return field_bits

    def decode(self, value: bitarray) -> [int | float]:
        if len(value) != self.sizeInBits:
            raise ValueError(f'field size mismatch: got={len(value)} want={self.sizeInBits}')

        dec = int.from_bytes(_pad_bits(value).tobytes(), signed=self._signed, byteorder='big')

        if self.defaultCalibrator:
            dec = self.defaultCalibrator.calibrate(dec)
        elif isinstance(value, float):
            raise ValueError('unable to decode float from integer without calibrator')

        #NOTE(bcwaldon): rounding off decoded value due
        # to imprecision in handling floats in python
        if isinstance(dec, float):
            dec = round(dec, 12)

        return dec

    def size(self, parameters) -> int:
        return self.sizeInBits


class BooleanDataEncoding:
    """Wrapper around IntegerDataEncoding that handles boolean value conversion."""

    def __init__(self, integer_encoding: IntegerDataEncoding):
        self._integer_encoding = integer_encoding

    def _to_int(self, value: [bool | int]) -> int:
        if isinstance(value, bool):
            return 1 if value else 0
        if isinstance(value, int):
            return 1 if value else 0
        raise ValueError(f"unsupported boolean value type: {type(value)}")

    def _from_int(self, value: int) -> bool:
        return value != 0

    def encode(self, value: [bool | int]) -> bitarray:
        int_value = self._to_int(value)
        return self._integer_encoding.encode(int_value)

    def decode(self, value: bitarray) -> bool:
        int_value = self._integer_encoding.decode(value)
        return self._from_int(int_value)

    def size(self, parameters) -> int:
        return self._integer_encoding.size(parameters)


class ValidRange(BaseType):
    minInclusive: float
    maxInclusive: float


class integerBaseType(BaseType):
    name: str
    shortDescription: str = None
    longDescription: str = None

    signed: bool = True
    #TODO(bcwaldon): confirm input values respect this field size
    sizeInBits: int = 32
    unitSet: UnitSet = None

    integerDataEncoding: IntegerDataEncoding = None
    validRange: ValidRange = None

    @property
    def data_encoding(self):
        if self.integerDataEncoding:
            return self.integerDataEncoding

        return IntegerDataEncoding()


class IntegerParameterType(integerBaseType):
    pass


class IntegerArgumentType(integerBaseType):
    pass


class floatBaseType(BaseType):
    name: str
    shortDescription: str = None
    longDescription: str = None

    sizeInBits: int = 64
    unitSet: UnitSet = None

    integerDataEncoding: IntegerDataEncoding = None
    floatDataEncoding: FloatDataEncoding = None

    @property
    def data_encoding(self):
        if self.integerDataEncoding:
            return self.integerDataEncoding
        elif self.floatDataEncoding:
            return self.floatDataEncoding

        return FloatDataEncoding()


class FloatParameterType(floatBaseType):
    pass


class FloatArgumentType(floatBaseType):
    pass


class StringEncodingEnum(str, enum.Enum):
    UTF8 = 'UTF-8'
    UTF16 = 'UTF-16'
    UTF16LE = 'UTF-16LE'
    UTF16BE = 'UTF-16BE'
    US_ASCII = 'US-ASCII'
    ISO_8859_1 = 'ISO-8859-1'
    WINDOWS_1252 = 'Windows-1252'


class StringDataEncoding(BaseType):
    encoding: StringEncodingEnum = StringEncodingEnum.UTF8
    bitOrder: str = BitOrderEnum.MSB
    sizeInBits: SizeInBits = None
    variable: VariableStringType = None  # For variable-length strings

    def _get_python_encoding(self) -> str:
        """Map XTCE encoding names to Python codec names."""
        mapping = {
            StringEncodingEnum.UTF8: 'utf-8',
            StringEncodingEnum.UTF16: 'utf-16-be',  # XTCE UTF-16 uses big-endian (with BOM handling)
            StringEncodingEnum.UTF16LE: 'utf-16-le',
            StringEncodingEnum.UTF16BE: 'utf-16-be',
            StringEncodingEnum.US_ASCII: 'ascii',
            StringEncodingEnum.ISO_8859_1: 'iso-8859-1',
            StringEncodingEnum.WINDOWS_1252: 'cp1252',
        }
        return mapping.get(self.encoding, 'utf-8')

    def _get_termination_bytes(self) -> bytes:
        """Get termination character as bytes from hex string, or None if not specified."""
        term_char = None
        if self.sizeInBits is not None:
            term_char = self.sizeInBits.terminationChar
        elif self.variable is not None:
            term_char = self.variable.terminationChar
        if term_char is None:
            return None
        try:
            return bytes.fromhex(term_char)
        except ValueError:
            return None

    def encode(self, value: str, parameters=None) -> bitarray:
        if not isinstance(value, str):
            value = str(value)

        python_encoding = self._get_python_encoding()
        encoded_bytes = value.encode(python_encoding)

        # Get target size in bits
        target_bits = self.size(parameters or {})
        target_bytes = target_bits // 8

        termination = self._get_termination_bytes()

        # Truncate if too long
        if len(encoded_bytes) > target_bytes:
            encoded_bytes = encoded_bytes[:target_bytes]
        elif len(encoded_bytes) < target_bytes:
            # Add termination character if specified and there's room
            if termination is not None and len(encoded_bytes) + len(termination) <= target_bytes:
                encoded_bytes = encoded_bytes + termination
            # Pad remaining space with null bytes
            if len(encoded_bytes) < target_bytes:
                encoded_bytes = encoded_bytes + b'\x00' * (target_bytes - len(encoded_bytes))

        result = bitarray()
        result.frombytes(encoded_bytes)
        return result[:target_bits]

    def decode(self, value: bitarray) -> str:
        # Pad to byte boundary if needed
        padded = value.copy()
        remainder = len(padded) % 8
        if remainder != 0:
            padded = bitarray((8 - remainder) * [0]) + padded

        encoded_bytes = padded.tobytes()

        python_encoding = self._get_python_encoding()
        termination = self._get_termination_bytes()

        # Find and strip at termination character if specified
        if termination is not None:
            term_pos = encoded_bytes.find(termination)
            if term_pos != -1:
                encoded_bytes = encoded_bytes[:term_pos]
        else:
            # Default behavior: strip trailing null bytes
            encoded_bytes = encoded_bytes.rstrip(b'\x00')

        try:
            return encoded_bytes.decode(python_encoding)
        except UnicodeDecodeError:
            # Fall back to replacing invalid characters
            return encoded_bytes.decode(python_encoding, errors='replace')

    def size(self, parameters) -> int:
        # Handle Variable element (for variable-length strings)
        if self.variable is not None:
            if self.variable.dynamicValue:
                # Check for argumentInstanceRef first (commands), then parameterInstanceRef (telemetry)
                if self.variable.dynamicValue.argumentInstanceRef:
                    ref = self.variable.dynamicValue.argumentInstanceRef.argumentRef
                elif self.variable.dynamicValue.parameterInstanceRef:
                    ref = self.variable.dynamicValue.parameterInstanceRef.parameterRef
                else:
                    raise ValueError('Variable dynamicValue has no reference')
                ref_value = parameters.get(ref)
                if ref_value is None:
                    raise ValueError(f'dynamic value reference {ref} not found')
                return int(ref_value)
            # Fall back to maxSizeInBits if no dynamic value
            return self.variable.maxSizeInBits

        # Handle SizeInBits element (for fixed-length strings)
        if self.sizeInBits is None:
            raise ValueError('StringDataEncoding requires sizeInBits or variable')

        if self.sizeInBits.fixedValue:
            return self.sizeInBits.fixedValue
        if self.sizeInBits.fixed:
            return self.sizeInBits.fixed.fixedValue

        if self.sizeInBits.dynamicValue:
            # Check for argumentInstanceRef first (commands), then parameterInstanceRef (telemetry)
            if self.sizeInBits.dynamicValue.argumentInstanceRef:
                ref = self.sizeInBits.dynamicValue.argumentInstanceRef.argumentRef
            elif self.sizeInBits.dynamicValue.parameterInstanceRef:
                ref = self.sizeInBits.dynamicValue.parameterInstanceRef.parameterRef
            else:
                raise ValueError('dynamicValue has no reference')
            ref_value = parameters.get(ref)
            if ref_value is None:
                raise ValueError(f'dynamic value reference {ref} not found')
            return int(ref_value)

        raise ValueError('unable to determine string size')


class StringParameterType(BaseType):
    name: str
    shortDescription: str = None
    longDescription: str = None

    unitSet: UnitSet = None

    stringDataEncoding: StringDataEncoding = None

    @property
    def data_encoding(self):
        if self.stringDataEncoding:
            return self.stringDataEncoding

        return StringDataEncoding()


class StringArgumentType(BaseType):
    name: str
    shortDescription: str = None
    longDescription: str = None

    unitSet: UnitSet = None

    stringDataEncoding: StringDataEncoding = None

    @property
    def data_encoding(self):
        if self.stringDataEncoding:
            return self.stringDataEncoding

        return StringDataEncoding()


class BinaryDataEncoding(BaseType):
    sizeInBits: SizeInBits
    #NOTE(bcwaldon): much left to be implemented here
    #bitOrder: str = BitOrderEnum.MSB
    #byteOrder: str = ByteOrderEnum.MSB

    def encode(self, value: bitarray) -> bitarray:
        return value

    def decode(self, value: bitarray) -> bitarray:
        return value

    def size(self, parameters) -> int:
        if self.sizeInBits.fixedValue:
            return self.sizeInBits.fixedValue
        if self.sizeInBits.fixed:
            return self.sizeInBits.fixed.fixedValue

        try:
            ref = self.sizeInBits.dynamicValue.parameterInstanceRef.parameterRef
            ref_value = parameters[ref]
        except:
            raise Exception('failed to retrieve dynamic value parameter')

        assert isinstance(ref_value, int), 'dynamic value parameter must be integer'
        assert ref_value > 0,  'dynamic value parameter must be greater than zero'

        return ref_value


class BinaryParameterType(BaseType):
    name: str
    longDescription: str = None

    binaryDataEncoding: BinaryDataEncoding

    @property
    def data_encoding(self):
        if not self.binaryDataEncoding:
            raise ValueError('BinaryDataEncoding not defined')
        return self.binaryDataEncoding


class FixedValue(BaseType):
    value: int

class DimensionIndex(BaseType):
    fixedValue: FixedValue = None
    dynamicValue: DynamicValue = None

    def get_value(self, parameters: dict) -> int:
        if self.fixedValue is not None:
            return self.fixedValue.value
        if self.dynamicValue is not None:
            if self.dynamicValue.parameterInstanceRef is not None:
                ref = self.dynamicValue.parameterInstanceRef.parameterRef
                if ref not in parameters:
                    raise ValueError(f"Dynamic array size parameter '{ref}' not found in parameters")
                return parameters[ref]
            if self.dynamicValue.argumentInstanceRef is not None:
                ref = self.dynamicValue.argumentInstanceRef.argumentRef
                if ref not in parameters:
                    raise ValueError(f"Dynamic array size argument '{ref}' not found in parameters")
                return parameters[ref]
        raise ValueError("DimensionIndex has no fixed or dynamic value")

class Dimension(BaseType):
    startingIndex: DimensionIndex
    endingIndex: DimensionIndex

class DimensionList(BaseType):
    # Have not implemented support for more than single dimension yet
    dimension: conlist(Dimension, min_length=1, max_length=1)


class ArrayParameterType(BaseType):
    name: str
    shortDescription: str = None
    longDescription: str = None

    arrayTypeRef: str
    dimensionList: DimensionList = None

    # initialized when used by encoder
    itemParameterType: typing.Any = None

    def item_count(self, parameters: dict) -> int:
        dim = self.dimensionList.dimension[0]
        start = dim.startingIndex.get_value(parameters)
        end = dim.endingIndex.get_value(parameters)
        return 1 + end - start

    @property
    def data_encoding(self):
        return self

    def encode(self, value: list) -> bitarray:
        return bitarray(itertools.chain(*[self.itemParameterType.data_encoding.encode(v) for v in value]))

    def decode(self, value: bitarray, parameters: dict = None) -> list:
        parameters = parameters or {}
        count = self.item_count(parameters)
        item_size = self.itemParameterType.data_encoding.size(parameters)
        return [self.itemParameterType.data_encoding.decode(value[i*item_size:(i+1)*item_size]) for i in range(count)]

    def size(self, parameters: dict) -> int:
        count = self.item_count(parameters)
        return count * self.itemParameterType.data_encoding.size(parameters)


class ArrayArgumentType(BaseType):
    name: str
    shortDescription: str = None
    longDescription: str = None

    arrayTypeRef: str
    dimensionList: DimensionList = None

    # initialized when used by encoder
    itemArgumentType: typing.Any = None

    def item_count(self, parameters: dict) -> int:
        dim = self.dimensionList.dimension[0]
        start = dim.startingIndex.get_value(parameters)
        end = dim.endingIndex.get_value(parameters)
        return 1 + end - start

    @property
    def data_encoding(self):
        return self

    def encode(self, value: list) -> bitarray:
        return bitarray(itertools.chain(*[self.itemArgumentType.data_encoding.encode(v) for v in value]))

    def decode(self, value: bitarray, parameters: dict = None) -> list:
        parameters = parameters or {}
        count = self.item_count(parameters)
        item_size = self.itemArgumentType.data_encoding.size(parameters)
        return [self.itemArgumentType.data_encoding.decode(value[i*item_size:(i+1)*item_size]) for i in range(count)]

    def size(self, parameters: dict) -> int:
        count = self.item_count(parameters)
        return count * self.itemArgumentType.data_encoding.size(parameters)


class BooleanParameterType(BaseType):
    name: str
    shortDescription: str = None
    longDescription: str = None

    unitSet: UnitSet = None

    initialValue: str = None
    zeroStringValue: str = 'False'
    oneStringValue: str = 'True'

    integerDataEncoding: IntegerDataEncoding = None

    @property
    def data_encoding(self):
        int_encoding = self.integerDataEncoding or IntegerDataEncoding(sizeInBits=1)
        return BooleanDataEncoding(int_encoding)


class BooleanArgumentType(BaseType):
    name: str
    shortDescription: str = None
    longDescription: str = None

    unitSet: UnitSet = None

    initialValue: str = None
    zeroStringValue: str = 'False'
    oneStringValue: str = 'True'

    integerDataEncoding: IntegerDataEncoding = None

    @property
    def data_encoding(self):
        int_encoding = self.integerDataEncoding or IntegerDataEncoding(sizeInBits=1)
        return BooleanDataEncoding(int_encoding)


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
    def data_encoding(self):
        if self.integerDataEncoding:
            return self.integerDataEncoding

        return IntegerDataEncoding()


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

    #TODO(bcwaldon): need to encode this parameter type properly. Currently just
    # copied similar behavior to IntegerBaseType

    @property
    def data_encoding(self):
        return IntegerDataEncoding(
                encoding=SignedEnum.unsigned,
                sizeInBits=32,
        )


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


class LocationInContainerInBits(BaseType):
    referenceLocation: str
    fixedValue: int

class ParameterRefEntry(BaseType):
    parameterRef: str
    includeCondition: ComparisonList = None
    locationInContainerInBits: LocationInContainerInBits = None


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
    binaryEncoding: BinaryDataEncoding = None


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
    stringParameterType: list[StringParameterType] = None
    booleanParameterType: list[BooleanParameterType] = None
    binaryParameterType: list[BinaryParameterType] = None
    arrayParameterType: list[ArrayParameterType] = None


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
    booleanArgumentType: list[BooleanArgumentType] = None
    stringArgumentType: list[StringArgumentType] = None
    arrayArgumentType: list[ArrayArgumentType] = None


class MetaCommandSet(BaseType):
    metaCommand: list[MetaCommand]


class CommandMetaData(BaseType):
    parameterTypeSet: ParameterTypeSet = None
    parameterSet: ParameterSet = None
    argumentTypeSet: ArgumentTypeSet = None
    metaCommandSet: MetaCommandSet = None


class SpaceSystem(BaseType):
    name: str
    shortDescription: str = ''
    longDescription: str = ''
    header: str = ''
    telemetryMetaData: TelemetryMetaData = None
    commandMetaData: CommandMetaData = None
    spaceSystem: list['SpaceSystem'] = None

    @functools.cached_property
    def _type_idx(self):
        parameter_type_sets = (
            self.telemetryMetaData.parameterTypeSet,
            self.commandMetaData.parameterTypeSet,
        )
        objs = list(itertools.chain(
            *[
                itertools.chain(
                    ts.arrayParameterType or [],
                    ts.integerParameterType or [],
                    ts.floatParameterType or [],
                    ts.absoluteTimeParameterType or [],
                    ts.enumeratedParameterType or [],
                    ts.binaryParameterType or [],
                    ts.booleanParameterType or [],
                    ts.stringParameterType or [],
                ) for ts in parameter_type_sets if ts
            ],
            self.commandMetaData.argumentTypeSet.integerArgumentType or [],
            self.commandMetaData.argumentTypeSet.enumeratedArgumentType or [],
            self.commandMetaData.argumentTypeSet.booleanArgumentType or [],
            self.commandMetaData.argumentTypeSet.stringArgumentType or [],
            self.commandMetaData.argumentTypeSet.arrayArgumentType or [],
        ))
        return dict([(o.name, o) for o in objs])

    def get_entry_type(self, name):
        try:
            entry_type = self._type_idx[name]
        except KeyError:
            raise ValueError(f"unknown entry type: {name}")

        if isinstance(entry_type, ArrayParameterType):
            try:
                entry_type.itemParameterType = self.get_entry_type(entry_type.arrayTypeRef)
            except Exception as exc:
                raise ValueError(f"failed to initialize array item type: {exc}")

        if isinstance(entry_type, ArrayArgumentType):
            try:
                entry_type.itemArgumentType = self.get_entry_type(entry_type.arrayTypeRef)
            except Exception as exc:
                raise ValueError(f"failed to initialize array item type: {exc}")

        return entry_type

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

    # find the MetaCommands and SequenceContainers that identify a BaseContainer using the name provided
    def find_inheritors(self, message_type):
        if isinstance(message_type, MetaCommand):
            match_container_ref = message_type.commandContainer.name
        else:
            match_container_ref = message_type.name

        match = []
        match.extend([sc for sc in self.telemetryMetaData.containerSet.sequenceContainer if sc.baseContainer and sc.baseContainer.containerRef == match_container_ref])
        match.extend([mc for mc in self.commandMetaData.metaCommandSet.metaCommand if mc.commandContainer.baseContainer and mc.commandContainer.baseContainer.containerRef == match_container_ref])

        return match


def from_file(file_location: str):
    with open(file_location, 'rb') as f:
        xml_doc = f.read()

    return from_bytes(xml_doc)


def from_bytes(xml_doc: bytes):
    xs = _load_xtce_xsd()

    node = xmlnode(xs.to_dict(xml_doc, converter=xmlschema.JsonMLConverter, path='/xtce:SpaceSystem'))
    return SpaceSystem._from_xmlnode(node)
