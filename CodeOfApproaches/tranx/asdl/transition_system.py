# coding=utf-8


class Action(object):
    pass


class ApplyRuleAction(Action):
    def __init__(self, production):
        self.production = production

    def __hash__(self):
        return hash(self.production)

    def __eq__(self, other):
        return isinstance(other, ApplyRuleAction) and self.production == other.production

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return 'ApplyRule[%s]' % self.production.__repr__()


class GenTokenAction(Action):
    def __init__(self, token):
        self.token = token

    def is_stop_signal(self):
        return self.token == '</primitive>'

    def __repr__(self):
        return 'GenToken[%s]' % self.token


class ReduceAction(Action):
   def __repr__(self):
       return 'Reduce'


class TransitionSystem(object):
    def __init__(self, grammar):
        self.grammar = grammar

    def get_actions(self, asdl_ast):
        """
        generate action sequence given the ASDL Syntax Tree
        """

        actions = []

        parent_action = ApplyRuleAction(asdl_ast.production)
        actions.append(parent_action)
        # print(asdl_ast)
        for field in asdl_ast.fields:
            # is a composite field

            # print(field.type)
            # print(field.value)
            # print(field.cardinality)
            # print(self.grammar.is_composite_type(field.type))
            if self.grammar.is_composite_type(field.type):

                if field.cardinality == 'single':
                    field_actions = self.get_actions(field.value)
                else:
                    field_actions = []

                    if field.value is not None:
                        if field.cardinality == 'multiple':
                            for val in field.value:
                                cur_child_actions = self.get_actions(val)
                                field_actions.extend(cur_child_actions)
                        elif field.cardinality == 'optional':
                            field_actions = self.get_actions(field.value)

                    # if an optional field is filled, then do not need Reduce action
                    # print('1')
                    # print(field_actions)
                    if field.cardinality == 'multiple' or field.cardinality == 'optional' and not field_actions:
                        field_actions.append(ReduceAction())
            else:  # is a primitive field
                field_actions = self.get_primitive_field_actions(field)

                # # if an optional field is filled, then do not need Reduce action
                # print('2')
                # print(field.type)
                # print(field.value)

                if field.cardinality == 'multiple' or field.cardinality == 'optional' and not field_actions :
                    # print(field.type)
                    # if field.type != 'ASDLPrimitiveType(singleton)':
                    # # reduce action
                    #     field_actions.append(ReduceAction())
                    # if field.type == 'ASDLPrimitiveType(singleton)' and field.value=='None':
                    #     field_actions.append(GenTokenAction(None))
                    # print('reduce')
                    field_actions.append(ReduceAction())
                # if str(field.type) == 'ASDLPrimitiveType(singleton)' and str(field.value) == 'None':
                #     print('womeilaile')
                #     field_actions.append(GenTokenAction(None))
                # print(field_actions)
            actions.extend(field_actions)

        return actions

    def tokenize_code(self, code, mode):
        raise NotImplementedError

    def hyp_correct(self, hyp, example):
        raise NotImplementedError

    def compare_ast(self, hyp_ast, ref_ast):
        raise NotImplementedError

    def ast_to_surface_code(self, asdl_ast):
        raise NotImplementedError

    def surface_code_to_ast(self, code):
        raise NotImplementedError

    def get_primitive_field_actions(self, realized_field):
        raise NotImplementedError

    def get_valid_continuation_types(self, hyp):
        # print(hyp.tree)
        if hyp.tree:
            # print(hyp.frontier_field.cardinality)
            if self.grammar.is_composite_type(hyp.frontier_field.type):
                if hyp.frontier_field.cardinality == 'single':
                    return ApplyRuleAction,
                else:  # optional, multiple
                    return ApplyRuleAction, ReduceAction
            else:

                # print(hyp._value_buffer)
                # print(hyp.frontier_field)
                # print(hyp.frontier_node)

                # if str(hyp.frontier_field) == 'Field(singleton value)':
                #     return ReduceAction,GenTokenAction
                if hyp.frontier_field.cardinality == 'single':
                    return GenTokenAction,
                elif hyp.frontier_field.cardinality == 'optional':
                    if hyp._value_buffer:
                        return GenTokenAction,
                    else:
                        return GenTokenAction, ReduceAction
                else:
                    return GenTokenAction, ReduceAction
        else:
            return ApplyRuleAction,

    def get_valid_continuating_productions(self, hyp):
        # print(hyp.tree)
        if hyp.tree:
            if self.grammar.is_composite_type(hyp.frontier_field.type):
                return self.grammar[hyp.frontier_field.type]
            else:
                raise ValueError
        else:
            return self.grammar[self.grammar.root_type]

    @staticmethod
    def get_class_by_lang(lang):
        if lang == 'python':
            from .lang.py.py_transition_system import PythonTransitionSystem
            return PythonTransitionSystem
        elif lang == 'lambda_dcs':
            from .lang.lambda_dcs.lambda_dcs_transition_system import LambdaCalculusTransitionSystem
            return LambdaCalculusTransitionSystem
        elif lang == 'prolog':
            from .lang.prolog.prolog_transition_system import PrologTransitionSystem
            return PrologTransitionSystem
        elif lang == 'wikisql':
            from .lang.sql.sql_transition_system import SqlTransitionSystem
            return SqlTransitionSystem

        raise ValueError
