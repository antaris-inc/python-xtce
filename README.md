# python-xtce

This library supports dynamic encoding and decoding of messages using XTCE in python. 

The current target XTCE version is 1.3. The documentation available is not entirely comparable to older versions of XTCE yet, so consider this repo a "best effort" implementation for the time being. ALso keep in mind, this library is not yet targeting the entire scope of XTCE. Consider the support matrix below to understand where gaps may exist.

## XTCE v1.3 Support Matrix

This document describes the python-xtce library's current support for XTCE v1.3 types.

## Parameter Types

Types available in `ParameterTypeSet`:

| Type | Supported | Notes |
|------|-----------|-------|
| IntegerParameterType | Yes | Signed/unsigned, configurable bit width, polynomial calibration |
| FloatParameterType | Yes | Integer and float data encodings |
| EnumeratedParameterType | Yes | Integer-encoded enumerations with label mapping |
| BooleanParameterType | Yes | Integer-encoded with configurable zero/one string values |
| StringParameterType | Yes | Fixed and dynamic size, multiple character encodings, termination characters |
| BinaryParameterType | Yes | Fixed and dynamic size |
| AbsoluteTimeParameterType | Yes | Partial: hardcoded to unsigned 32-bit integer encoding |
| ArrayParameterType | Yes | Single-dimension, fixed and dynamic sizing |
| RelativeTimeParameterType | No | |
| AggregateParameterType | No | |

## Argument Types

Types available in `ArgumentTypeSet`:

| Type | Supported | Notes |
|------|-----------|-------|
| IntegerArgumentType | Yes | Same capabilities as IntegerParameterType |
| FloatArgumentType | Yes | Same capabilities as FloatParameterType |
| EnumeratedArgumentType | Yes | Same capabilities as EnumeratedParameterType |
| BooleanArgumentType | Yes | Same capabilities as BooleanParameterType |
| AbsoluteTimeArgumentType | Yes | Partial: same limitations as AbsoluteTimeParameterType |
| ArrayArgumentType | Yes | Single-dimension, fixed and dynamic sizing |
| StringArgumentType | No | |
| BinaryArgumentType | No | |
| RelativeTimeArgumentType | No | |
| AggregateArgumentType | No | |

## Data Encodings

| Encoding | Supported | Notes |
|----------|-----------|-------|
| IntegerDataEncoding | Yes | Unsigned and twos complement; MSB bit/byte order only |
| FloatDataEncoding | Partial | Parsed but encode/decode not implemented |
| StringDataEncoding | Yes | UTF-8, UTF-16, US-ASCII, ISO-8859-1, Windows-1252; fixed, dynamic, and terminated sizing |
| BinaryDataEncoding | Yes | Fixed and dynamic size; passthrough encode/decode |

## Integer Encoding Details

| Feature | Supported | Notes |
|---------|-----------|-------|
| unsigned | Yes | |
| twosComplement | Yes | |
| signMagnitude | No | |
| onesComplement | No | |
| BCD | No | |
| packedBCD | No | |
| IEEE754_1985 | No | |
| MILSTD_1750A | No | |
| mostSignificantBitFirst | Yes | Default and only supported bit order |
| leastSignificantBitFirst | No | |
| mostSignificantByteFirst | Yes | Default and only supported byte order |
| leastSignificantByteFirst | No | |

## Calibrators

| Calibrator | Supported | Notes |
|------------|-----------|-------|
| PolynomialCalibrator | Yes | Encode and decode with numpy root-finding |
| SplineCalibrator | No | |
| MathOperationCalibrator | No | |
| ContextCalibratorList | No | |

## Telemetry Containers

| Feature | Supported | Notes |
|---------|-----------|-------|
| SequenceContainer | Yes | |
| BaseContainer (inheritance) | Yes | |
| RestrictionCriteria | Yes | ComparisonList and single Comparison |
| ParameterRefEntry | Yes | With optional locationInContainerInBits |
| ContainerRefEntry | Yes | With optional includeCondition |
| FixedValueEntry | Yes | Hex-encoded binary values |
| EntryList ordering | Yes | Tracks ordered_children for encode/decode |
| AncillaryDataSet | Yes | Parsed but not used in encode/decode |
| IncludeCondition | Yes | ComparisonList-based |
| BooleanExpression | No | Only ComparisonList supported in restrictions |

## Command Types

| Feature | Supported | Notes |
|---------|-----------|-------|
| MetaCommand | Yes | |
| CommandContainer | Yes | With entryList and baseContainer |
| BaseMetaCommand (inheritance) | Yes | |
| ArgumentList | Yes | |
| ArgumentRefEntry | Yes | |
| VerifierSet | Partial | completeVerifier and failedVerifier only |
| DefaultSignificance | Yes | Parsed |
| DefaultConsequence | Yes | Parsed |
| ParameterToSetList | Yes | Parsed |
| BlockMetaCommand | No | |
| TransmissionConstraints | No | |
| CommandVerifier (full set) | No | Only completeVerifier and failedVerifier |
| ArgumentAssignmentList | No | |

## Comparison and Restriction

| Feature | Supported | Notes |
|---------|-----------|-------|
| Comparison | Yes | Single parameter comparison |
| ComparisonList | Yes | AND-combined comparisons |
| RestrictionCriteria | Yes | Via Comparison or ComparisonList |
| BooleanExpression | No | |
| ANDedConditions | No | |
| ORedConditions | No | |

## Alarms

| Feature | Supported |
|---------|-----------|
| NumericAlarm | No |
| EnumerationAlarm | No |
| BooleanAlarm | No |
| StringAlarm | No |
| BinaryAlarm | No |
| TimeAlarm | No |
| ContextAlarm (all types) | No |

## Algorithms

| Feature | Supported |
|---------|-----------|
| MathAlgorithm | No |
| InputOutputAlgorithm | No |
| ExternalAlgorithm | No |
| TriggerSet | No |

## Streams

| Feature | Supported |
|---------|-----------|
| FixedFrameStream | No |
| VariableFrameStream | No |
| CustomStream | No |
| SyncStrategy | No |

## Other

| Feature | Supported | Notes |
|---------|-----------|-------|
| SpaceSystem (root) | Yes | Including nested SpaceSystem |
| Header | Partial | Parsed as string |
| UnitSet | Yes | Parsed on types that support it |
| ValidRange | Yes | Parsed on IntegerParameterType/ArgumentType |
| AliasSet | No | |
| MessageSet | No | |
| ServiceSet | No | |
| AlgorithmSet | No | |
| StreamSet | No | |
