import typing

from bitarray import bitarray
from pydantic import BaseModel
from xtce import xtceschema


class Message(BaseModel):
    message_type: xtceschema.SequenceContainer | xtceschema.MetaCommand
    entries: dict


class SpaceSystemEncoder:
    def __init__(self, space_system: xtceschema.SpaceSystem):
        self.space_system = space_system
        self._plan_cache = {}
        self._resolved_cache = {}

    @staticmethod
    def _conditions_met(conds, entries):
        for cond in conds:
            assert cond.comparisonOperator == '==', 'unsupported ComparisonOperator'
            assert cond.instance == 0, 'unsupported instance'
            assert cond.useCalibratedValue is True, 'unsupported useCalibratedValue'

            #TODO(bcwaldon): consider how to map from string value (comes from xmlxtceschema decode) to native type
            got = str(entries[cond.parameterRef])

            if got != cond.value:
                return False

        return True

    @staticmethod
    def _restrictions_match(restrictions, entries):
        """Pre-check restriction criteria against already-decoded entries.
        Skips parameters not yet decoded; does not assert on operator types."""
        for comp in restrictions:
            if comp.comparisonOperator != '==':
                continue
            if comp.parameterRef in entries:
                if str(entries[comp.parameterRef]) != comp.value:
                    return False
        return True

    def _build_entry_plan(self, message_type: xtceschema.MetaCommand | xtceschema.SequenceContainer) -> [list, list]:
        # Return a list of entries along with their required include conditions or restrictions
        key = id(message_type)
        if key in self._plan_cache:
            return self._plan_cache[key]

        plan = list() # list of tuples - first item is an entry and second a list of required conditions
        restrictions = list()

        # Start by following inheritance chain of CommandContainers
        if isinstance(message_type, xtceschema.MetaCommand):
            # Follow chain of CommandContainers
            con = message_type.commandContainer
            while True:
                if con.entryList and con.entryList.ordered_children:
                    plan = [[ent, None] for ent in con.entryList.ordered_children] + plan

                # Chain stops here
                if not con.baseContainer:
                    con = None
                    break

                if con.baseContainer.restrictionCriteria:
                    if con.baseContainer.restrictionCriteria.comparison:
                        restrictions.append(con.baseContainer.restrictionCriteria.comparison)
                    else:
                        restrictions.extend(list(con.baseContainer.restrictionCriteria.comparisonList.ordered_children or []))

                next_con_ref = con.baseContainer.containerRef
                con = self.space_system.get_container(next_con_ref)

                # Chain continues, but will be resolved below
                if not isinstance(con, xtceschema.CommandContainer):
                    break

        elif isinstance(message_type, xtceschema.SequenceContainer):
            con = message_type

        else:
            raise ValueError(f'unrecognized message_type {message_type}')

        # Only continue if following BaseContainer chain from a MetaCommand, or start a new chain for SequenceContainer (Telemetry)
        if con:
            while True:
                if con.entryList and con.entryList.ordered_children:
                    new_plan = []
                    new_restrictions = []
                    for ent in con.entryList.ordered_children:
                        if isinstance(ent, xtceschema.ContainerRefEntry):
                            embedded_con = self.space_system.get_sequence_container(ent.containerRef)
                            embedded_plan, embedded_restrictions = self._build_entry_plan(embedded_con)
                            new_conditions = list(ent.includeCondition.comparison) if ent.includeCondition else []
                            for embedded_entry, embedded_conditions in embedded_plan:
                                include_conditions = new_conditions + list(embedded_conditions or [])
                                new_plan.append((embedded_entry, include_conditions or None))
                                new_restrictions = new_restrictions + embedded_restrictions
                        else:
                            new_plan.append((ent, None))

                    plan = new_plan + plan
                    restrictions = new_restrictions + restrictions

                # Chain stops here
                if not con.baseContainer:
                    break

                if con.baseContainer.restrictionCriteria:
                    if con.baseContainer.restrictionCriteria.comparison:
                        restrictions.append(con.baseContainer.restrictionCriteria.comparison)
                    else:
                        restrictions.extend(list(con.baseContainer.restrictionCriteria.comparisonList.ordered_children or []))

                next_con_ref = con.baseContainer.containerRef
                con = self.space_system.get_container(next_con_ref)

        result = (plan, restrictions)
        self._plan_cache[key] = result
        return result

    def _get_resolved_plan(self, message_type):
        """Get plan with pre-resolved entry types and restriction index."""
        key = id(message_type)
        if key in self._resolved_cache:
            return self._resolved_cache[key]

        plan, restrictions = self._build_entry_plan(message_type)

        # Build arg type index for MetaCommands
        arg_type_idx = {}
        if isinstance(message_type, xtceschema.MetaCommand):
            cur = message_type
            while True:
                if cur.argumentList and cur.argumentList.argument:
                    arg_type_idx.update({arg.name: arg.argumentTypeRef for arg in cur.argumentList.argument})
                if not cur.baseMetaCommand or not cur.baseMetaCommand.metaCommandRef:
                    break
                cur = self.space_system.get_meta_command(cur.baseMetaCommand.metaCommandRef)

        # Pre-resolve entry types
        resolved_entries = []
        for (ent, conds) in plan:
            if isinstance(ent, xtceschema.ArgumentRefEntry):
                ent_name = ent.argumentRef
                ent_type = self.space_system.get_entry_type(arg_type_idx[ent_name])
                resolved_entries.append((ent, conds, ent_name, ent_type))
            elif isinstance(ent, xtceschema.ParameterRefEntry):
                ent_name = ent.parameterRef
                ent_type = self.space_system.get_entry_type(
                    self.space_system.get_parameter(ent_name).parameterTypeRef
                )
                resolved_entries.append((ent, conds, ent_name, ent_type))
            elif isinstance(ent, xtceschema.FixedValueEntry):
                resolved_entries.append((ent, conds, None, None))
            else:
                resolved_entries.append((ent, conds, None, None))

        # Pre-build restriction index
        restriction_idx = {}
        for comp in restrictions:
            restriction_idx.setdefault(comp.parameterRef, []).append(comp)

        result = (resolved_entries, restrictions, restriction_idx)
        self._resolved_cache[key] = result
        return result

    def encode(self, msg: Message) -> bitarray:
        resolved_entries, restrictions, _ = self._get_resolved_plan(msg.message_type)

        for comp in restrictions:
            assert comp.comparisonOperator == '==', 'unsupported ComparisonOperator'
            assert comp.instance == 0, 'unsupported instance'
            assert comp.useCalibratedValue is True, 'unsupported useCalibratedValue'

            #NOTE(bcwaldon): need to implement this check
            #if comp.parameterRef in msg.entries and msg.entries[comp.parameterRef] != comp.value:
            #   raise ValueError()

            #NOTE(bcwaldon): unclear exactly how to handle casting from XML type to native datatype
            msg.entries[comp.parameterRef] = int(comp.value)

        encoded = bitarray()

        for (ent, conds, ent_name, ent_type) in resolved_entries:
            if conds and not self._conditions_met(conds, msg.entries):
                continue

            if ent_name is not None:
                ent_value = msg.entries[ent_name]
                if isinstance(ent_type, (xtceschema.StringParameterType, xtceschema.StringArgumentType)):
                    encoded.extend(ent_type.data_encoding.encode(ent_value, msg.entries))
                else:
                    encoded.extend(ent_type.data_encoding.encode(ent_value))
            elif isinstance(ent, xtceschema.FixedValueEntry):
                encoded.extend(ent.value)
            else:
                raise ValueError(f'unable to encode {ent.__class__}')

        return encoded


    def decode(self, message_type: xtceschema.SequenceContainer | xtceschema.MetaCommand, b: bitarray, require_concrete=False) -> Message:
        # Decode a bitarray using a specific message type.
        #
        # If the provided message type is abstract, then its inheritors are evaluated based on their restriction criteria.
        # Assuming a match is found, the inheritor will be used to decode the message and will be returned to the caller.
        #
        # When require_concrete=False: if the indicated message type is abstract, consider decoding successful if the full message
        # can be decoded.
        #
        # When require_concrete=True: do not consider abstract message types for final decoding. Useful when concrete types have
        # the same message length as abstract types.
        #
        msg, consumed = self._decode_message(message_type, b)
        if consumed == len(b) and (not message_type.abstract or not require_concrete):
            return msg

        n_rem = len(b) - consumed

        if not message_type.abstract:
            raise ValueError(f'{n_rem}b remain to decode yet message type {message_type.name} not abstract')

        inheritors = self.space_system.find_inheritors(message_type)
        for inh in inheritors:
            # Pre-check restriction criteria against already-decoded entries
            # to avoid expensive decode attempts that will certainly fail
            _, inh_restrictions, _ = self._get_resolved_plan(inh)
            if not self._restrictions_match(inh_restrictions, msg.entries):
                continue

            try:
                return self.decode(inh, b, require_concrete=require_concrete)
            except Exception as exc:
                continue

        raise ValueError(f'no inheritor of {message_type.name} found to handle remaining {n_rem}b of message')

    def _decode_message(self, message_type: xtceschema.SequenceContainer | xtceschema.MetaCommand, b: bitarray) -> (Message, int):
        msg = Message(
            message_type=message_type,
            entries=dict(),
        )

        resolved_entries, _, restriction_idx = self._get_resolved_plan(message_type)

        offset = 0

        for (ent, conds, ent_name, ent_type) in resolved_entries:
            if conds and not self._conditions_met(conds, msg.entries):
                # simply ignore in this case
                continue

            if ent_name is not None:
                enc = ent_type.data_encoding

                # Variable-length terminated strings: scan buffer for the
                # termination character rather than blindly reading maxSizeInBits.
                if (isinstance(enc, xtceschema.StringDataEncoding)
                        and enc.variable is not None
                        and enc._get_termination_bytes() is not None):
                    max_bits = enc.variable.maxSizeInBits
                    remaining_bits = len(b) - offset
                    read_bits = min(max_bits, remaining_bits)
                    read_bits = (read_bits // 8) * 8  # byte-align
                    chunk = b[offset:offset + read_bits]

                    raw = chunk.tobytes()
                    term = enc._get_termination_bytes()
                    term_pos = raw.find(term)
                    if term_pos != -1:
                        consumed_bits = (term_pos + len(term)) * 8
                    else:
                        consumed_bits = read_bits

                    encoded_entry = b[offset:offset + consumed_bits]
                    offset += consumed_bits
                    msg.entries[ent_name] = enc.decode(encoded_entry)
                else:
                    encoded_bit_length = enc.size(msg.entries)
                    encoded_entry = b[offset:offset + encoded_bit_length]
                    offset += encoded_bit_length

                    # Pass parameters to decode for types that need them (e.g. ArrayParameterType/ArrayArgumentType with dynamic size)
                    if isinstance(ent_type, (xtceschema.ArrayParameterType, xtceschema.ArrayArgumentType)):
                        msg.entries[ent_name] = enc.decode(encoded_entry, msg.entries)
                    else:
                        msg.entries[ent_name] = enc.decode(encoded_entry)

                if isinstance(ent, xtceschema.ParameterRefEntry) and ent_name in restriction_idx:
                    if not self._conditions_met(restriction_idx[ent_name], msg.entries):
                        raise ValueError(f'restriction criteria violated for entry {ent_name}')

            elif isinstance(ent, xtceschema.FixedValueEntry):
                encoded_entry = b[offset:offset + ent.sizeInBits]
                if encoded_entry != ent.value:
                    raise ValueError('fixed value mismatch')
                offset += ent.sizeInBits
            else:
                raise ValueError(f'unable to decode {ent.__class__}')

        return msg, offset
