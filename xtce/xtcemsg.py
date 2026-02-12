import typing

from bitarray import bitarray
from pydantic import BaseModel
import itertools

from xtce import xtceschema


class Message(BaseModel):
    message_type: xtceschema.SequenceContainer | xtceschema.MetaCommand
    entries: dict


class SpaceSystemEncoder:
    def __init__(self, space_system: xtceschema.SpaceSystem):
        self.space_system = space_system

    def _build_entry_plan(self, message_type: xtceschema.MetaCommand | xtceschema.SequenceContainer) -> [list, list]:
        # Return a list of entries along with their required include condtions or restrictions
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
                            new_conditions = list(ent.includeCondition.comparison)
                            for embedded_entry, embedded_conditions in embedded_plan:
                                include_conditions = new_conditions + list(embedded_conditions or [])
                                new_plan.append((embedded_entry, include_conditions))
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

        return plan, restrictions

    def encode(self, msg: Message) -> bitarray:
        plan, restrictions = self._build_entry_plan(msg.message_type)

        for comp in restrictions:
            assert comp.comparisonOperator == '==', 'unsupported ComparisonOperator'
            assert comp.instance == 0, 'unsupported instance'
            assert comp.useCalibratedValue is True, 'unsupported useCalibratedValue'

            #NOTE(bcwaldon): need to implement this check
            #if comp.parameterRef in msg.entries and msg.entries[comp.parameterRef] != comp.value:
            #   raise ValueError()

            #NOTE(bcwaldon): unclear exactly how to handle casting from XML type to native datatype
            msg.entries[comp.parameterRef] = int(comp.value)

        arg_type_idx = dict()
        if isinstance(msg.message_type, xtceschema.MetaCommand):
            cur = msg.message_type
            while True:
                if cur.argumentList and cur.argumentList.argument:
                    arg_type_idx.update(dict([(arg.name, arg.argumentTypeRef) for arg in cur.argumentList.argument]))
                if not cur.baseMetaCommand or not cur.baseMetaCommand.metaCommandRef:
                    break
                cur = self.space_system.get_meta_command(cur.baseMetaCommand.metaCommandRef)

        encoded_entries = list[bitarray]()

        def encode_and_append_entry(ent_name, ent_type_name):
            ent_type = self.space_system.get_entry_type(ent_type_name)
            ent_value = msg.entries[ent_name]
            if isinstance(ent_type, (xtceschema.StringParameterType, xtceschema.StringArgumentType)):
                encoded_entry = ent_type.data_encoding.encode(ent_value, msg.entries)
            else:
                encoded_entry = ent_type.data_encoding.encode(ent_value)
            encoded_entries.append(encoded_entry)

        def conditions_met(conds):
            for cond in conds:
                assert cond.comparisonOperator == '==', 'unsupported ComparisonOperator'
                assert cond.instance == 0, 'unsupported instance'
                assert cond.useCalibratedValue is True, 'unsupported useCalibratedValue'

                #TODO(bcwaldon): consider how to map from string value (comes from xmlxtceschema decode) to native type
                got = str(msg.entries[cond.parameterRef])

                if got != cond.value:
                    return False

            return True

        for (ent, conds) in plan:
            if conds and not conditions_met(conds):
                continue

            if isinstance(ent, xtceschema.ArgumentRefEntry):
                ent_name = ent.argumentRef
                ent_type_name = arg_type_idx[ent_name]
                encode_and_append_entry(ent_name, ent_type_name)
            elif isinstance(ent, xtceschema.ParameterRefEntry):
                ent_name = ent.parameterRef
                ent_type_name = self.space_system.get_parameter(ent_name).parameterTypeRef
                encode_and_append_entry(ent_name, ent_type_name)
            elif isinstance(ent, xtceschema.FixedValueEntry):
                encoded_entries.append(ent.value)
            else:
                raise ValueError(f'unable to encode {ent.__class__}')

        encoded = bitarray(list(itertools.chain(*encoded_entries)))
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
        bak = b.copy()

        msg, rem = self._decode_message(message_type, b)
        if not rem and (not message_type.abstract or not require_concrete):
            return msg

        n_rem = len(rem)

        if not message_type.abstract:
            raise ValueError(f'{n_rem}b remain to decode yet message type {message_type.name} not abstract')

        inheritors = self.space_system.find_inheritors(message_type)
        for inh in inheritors:
            #NOTE(bcwaldon): this is a hack and somewhat wasteful
            try:
                return self.decode(inh, bak.copy(), require_concrete=require_concrete)
            except Exception as exc:
                continue

        raise ValueError(f'no inheritor of {message_type.name} found to handle remaining {n_rem}b of message')

    def _decode_message(self, message_type: xtceschema.SequenceContainer | xtceschema.MetaCommand, b: bitarray) -> (Message, bitarray):
        msg = Message(
            message_type=message_type,
            entries=dict(),
        )

        plan, restrictions = self._build_entry_plan(message_type)

        restriction_idx = {}
        for comp in restrictions:
            if comp.parameterRef not in restriction_idx:
                restriction_idx[comp.parameterRef] = []
            restriction_idx[comp.parameterRef].append(comp)

        arg_type_idx = dict()
        if isinstance(message_type, xtceschema.MetaCommand):
            cur = msg.message_type
            while True:
                if cur.argumentList and cur.argumentList.argument:
                    arg_type_idx.update(dict([(arg.name, arg.argumentTypeRef) for arg in cur.argumentList.argument]))
                if not cur.baseMetaCommand or not cur.baseMetaCommand.metaCommandRef:
                    break
                cur = self.space_system.get_meta_command(cur.baseMetaCommand.metaCommandRef)

        def pop_entry(b: bytearray, ent_name: str, ent_type_name: str):
            ent_type = self.space_system.get_entry_type(ent_type_name)
            encoded_bit_length = ent_type.data_encoding.size(msg.entries)

            encoded_entry = b[:encoded_bit_length]
            del b[:encoded_bit_length]

            # Pass parameters to decode for types that need them (e.g. ArrayParameterType/ArrayArgumentType with dynamic size)
            if isinstance(ent_type, (xtceschema.ArrayParameterType, xtceschema.ArrayArgumentType)):
                msg.entries[ent_name] = ent_type.data_encoding.decode(encoded_entry, msg.entries)
            else:
                msg.entries[ent_name] = ent_type.data_encoding.decode(encoded_entry)

        def conditions_met(conds):
            for cond in conds:
                assert cond.comparisonOperator == '==', 'unsupported ComparisonOperator'
                assert cond.instance == 0, 'unsupported instance'
                assert cond.useCalibratedValue is True, 'unsupported useCalibratedValue'

                #TODO(bcwaldon): consider how to map from string value (comes from xmlxtceschema decode) to native type
                got = str(msg.entries[cond.parameterRef])

                if got != cond.value:
                    return False
            return True

        for (ent, conds) in plan:
            if conds and not conditions_met(conds):
                # simply ignore in this case
                continue

            if isinstance(ent, xtceschema.ArgumentRefEntry):
                ent_name = ent.argumentRef
                ent_type_name = arg_type_idx[ent_name]
                pop_entry(b, ent_name, ent_type_name)
            elif isinstance(ent, xtceschema.ParameterRefEntry):
                ent_name = ent.parameterRef
                ent_type_name = self.space_system.get_parameter(ent_name).parameterTypeRef
                pop_entry(b, ent_name, ent_type_name)
                if ent_name in restriction_idx and not conditions_met(restriction_idx[ent_name]):
                    raise ValueError(f'restriction criteria violated for entry {ent_name}')

            elif isinstance(ent, xtceschema.FixedValueEntry):
                encoded_entry, b = b[:ent.sizeInBits], b[ent.sizeInBits:]
                if encoded_entry != ent.value:
                    raise ValueError('fixed value mismatch')
            else:
                raise ValueError(f'unable to decode {ent.__class__}')

        return msg, b
