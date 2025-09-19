
* BogusSAT/BogusSAT_modified.xml is a modified copy of BogusSAT-1.xml from gitlab.com/dovreem/xtcetools
    * Link to upstream: https://gitlab.com/dovereem/xtcetools/-/blob/2ed141930fd4bde109191343183d10a0388db121/src/test/resources/org/xtce/toolkit/test/BogusSAT-1.xml
    * Changes applied in order to meet final XTCE v1.2 schema:
        * Updated XML namespace to use official XTCE v1.2 reference
        * Renamed rangeAppliesToCalibrated attribute to validRangeAppliesToCalibrated
        * Removed empty PolynomialCalibrator, SplineCalibrator, MathOperationCalibrator elements
        * Removed negative test cases Float_MathOpCal_6_Type and Float_MathOpCal_10_Type
        * Wrap ValidRange in ValidRangeSet for argument types
        * Reordered BaseContainer and EntryList to meet requirement (EntryList first)
        * Added required Fixed and FixedValue child elements to StringDataEncoding where required. FixedValue content is a guess
* ccsds_660x1g2.xml is copied from CCSDS Green Book 660x1g2 (https://ccsds.org/Pubs/660x1g2.pdf) section ANNEX A
* ccsds_660x2g2.xml is copied from CCSDS Green Book 660x2g2 (https://ccsds.org/Pubs/660x2g2.pdf)

