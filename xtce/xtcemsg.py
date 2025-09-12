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

    def _build_entry_plan(self, message_type: xtceschema.MetaCommand | xtceschema.SequenceContainer) -> list:
        plan = list()

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
                    for ent in con.entryList.ordered_children:
                        if isinstance(ent, xtceschema.ContainerRefEntry):
                            embedded_con = self.space_system.get_sequence_container(ent.containerRef)
                            embedded_plan = self._build_entry_plan(embedded_con)
                            new_conditions = list(ent.includeCondition.comparison)
                            for embedded_entry, embedded_conditions in embedded_plan:
                                conditions = new_conditions + list(embedded_conditions or [])
                                new_plan.append((embedded_entry, conditions))
                        else:
                            new_plan.append((ent, None))

                    plan = new_plan + plan

                # Chain stops here
                if not con.baseContainer:
                    break

                next_con_ref = con.baseContainer.containerRef
                con = self.space_system.get_container(next_con_ref)

        return plan

    def encode(self, msg: Message) -> bitarray:
        plan = self._build_entry_plan(msg.message_type)

        arg_type_idx = dict()
        if isinstance(msg.message_type, xtceschema.MetaCommand):
            arg_type_idx.update(dict([(arg.name, arg.argumentTypeRef) for arg in msg.message_type.argumentList.argument]))

        encoded_entries = list[bitarray]()

        def encode_and_append_entry(ent_name, ent_type_name):
            ent_type = self.space_system.get_entry_type(ent_type_name)
            ent_value = msg.entries[ent_name]
            encoded_entry = ent_type.encode(ent_value)
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

    def decode(self, message_type: xtceschema.SequenceContainer | xtceschema.MetaCommand, b: bitarray) -> Message:
        msg = Message(
            message_type=message_type,
            entries=dict(),
        )

        plan = self._build_entry_plan(message_type)

        arg_type_idx = dict()
        if isinstance(message_type, xtceschema.MetaCommand):
            arg_type_idx.update(dict([(arg.name, arg.argumentTypeRef) for arg in message_type.argumentList.argument]))

        def pop_entry(b: bytearray, ent_name: str, ent_type_name: str):
            ent_type = self.space_system.get_entry_type(ent_type_name)
            encoded_entry = b[:ent_type.encoded_bit_length]
            del b[:ent_type.encoded_bit_length]
            msg.entries[ent_name] = ent_type.decode(encoded_entry)

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
                pop_entry(b, ent_name, ent_type_name)
            elif isinstance(ent, xtceschema.ParameterRefEntry):
                ent_name = ent.parameterRef
                ent_type_name = self.space_system.get_parameter(ent_name).parameterTypeRef
                pop_entry(b, ent_name, ent_type_name)
            elif isinstance(ent, xtceschema.FixedValueEntry):
                encoded_entry, b = b[:ent.sizeInBits], b[ent.sizeInBits:]
                if encoded_entry != ent.value:
                    raise ValueError('fixed value mismatch')
            else:
                raise ValueError(f'unable to decode {ent.__class__}')

        return msg
