# Parses drawing commands

import yaml
import gui
import re
import random
from copy import copy
from functools import partial

TRANSFORMATIONS = {'scale':'scale', 'translate':'translate', 'rotate':'rotate'}
REVERSE_TRANSFORMATIONS = {'scale':'reverse_scale', 'translate':'reverse_translate', 'rotate':'reverse_rotate'}
PRIMITIVES = {'rect':'draw_rect', 'polygon':'draw_polygon', 'pixel':'draw_pixel', 'pixels':'draw_pixels', 'text':'draw_text'}

class Command(object):
    """ A Command object defines the highest level of commands, its subcommands are simple dictionaries, 
        because only two levels of commands are allowed. """
    def __init__(self, name):
        self.name = name 
        self.sub_commands = []
        self.recursion_depth = 0
        self.variables = {}
        self.vars_to_replace = {}

    def add_subcommand(self, command_name, command_args, command_kwargs):
        self.sub_commands.append( {'name':command_name, 'args':command_args, 'kwargs':command_kwargs} ) 

    def __repr__(self):
        return "Command %s: %s" % (self.name, self.sub_commands)

    def variable_resolver(self, var_name):
        if var_name in self.vars_to_replace: return self.vars_to_replace[var_name]
        return self.variables[var_name]

    def eval_partial(self, arg):
        """ Evaluates arg if it is callable, simply returns it if it is not. """
        if callable(arg): return arg()
        return arg

    def create_color(self, *args):
        args = list(args)
        arg_index = 0
        for arg in args:
            while callable(arg): 
                arg = arg()
                args[arg_index] = arg

            arg_index += 1
        return gui.Color(*args)

    def parse_args(self, arg):
        """ Parse command arguments, converting special types of arguments:
            Color definitions in the form of 'c(r,g,b[,a])' are converted into gui.Color objects
            Random values in the form of rand(from, to) or rand(to):
                These are converted to partial function objects containing random.uniform(from,to)
                The reason for this is that the random numbers need to be regenerated every time the command is used.
                If they weren't recreated, every object would have the same random values and all copies would look the same.
        """
        if type(arg) in [int, float]: return arg
        if type(arg) == list:
            parsed_list = []
            for item in arg:
                parsed_list.append( self.parse_args(item) )
            return parsed_list
        if type(arg) == dict:
            for item in arg:
                arg[item] = self.parse_args(arg[item])
            return arg

        # Variable definitions
        m = re.match(r'^(\w+) ?= ?(.+)$', arg)
        if m:
            var_name = m.groups()[0]
            value = partial(self.variable_resolver, *[self.parse_args(m.groups()[0])])
            self.variables[var_name] = self.parse_args(m.groups()[1])
            self.vars_to_replace[var_name] = self.parse_args(m.groups()[1])
            return value

        # String-encoded numbers
        m = re.match(r'^-?\d*\.?\d+$', arg)
        if m:
            return float(arg)

        # Value multiplication
        m = re.match(r'^ *\*= *(.+)$', arg)
        if m:
            return lambda x: x * self.eval_partial(self.parse_args(m.groups()[0]))
        # Value division
        m = re.match(r'^ *\/= *(.+)$', arg)
        if m:
            return lambda x: float(x) / self.eval_partial(self.parse_args(m.groups()[0]))
        # Value substraction
        m = re.match(r'^ *\-= *(.+)$', arg)
        if m:
            return lambda x: x - self.eval_partial(self.parse_args(m.groups()[0]))
        # Value addition
        m = re.match(r'^ *\+= *(.+)$', arg)
        if m:
            return lambda x: x + self.eval_partial(self.parse_args(m.groups()[0]))

        # Random values
        m = re.match(r'^rand\((-?\d*\.?\d+)(?: *, *(-?\d*\.?\d+))?\)', arg)
        if m: 
            if m.groups()[1]:
                rand_from = float(m.groups()[0])
                rand_to = float(m.groups()[1])
            else:
                rand_from = 0
                rand_to = float(m.groups()[0])
            return partial(random.uniform, *[rand_from, rand_to])

        # Colors
        m = re.match(r'^c\(([^,]+),([^,]+),([^,]+)(?:,([^,]+))?\)$', arg)
        if m:
            r = self.parse_args(m.groups()[0])
            g = self.parse_args(m.groups()[1])
            b = self.parse_args(m.groups()[2])
            if m.groups()[3]: 
                a = self.parse_args(m.groups()[3])
            else:
                a = 1
            return partial(self.create_color, r, g, b, a)
        return arg


class GagParser(object):
    """ Parses yaml data to create commands"""
    def __init__(self, raw_data, gui):
        self.data = yaml.load(raw_data)
        if not type(self.data) == list: raise Exception("Root level of data must be a list, not a %s" % type(self.data))
        self.commands = {}
        self.gui = gui

    def _single_key_to_tuple(self, dict):
        """ Converts a single-key dictionary to a (key, value) tuple """
        item_list = dict.items()
        if len(item_list) != 1: 
            raise Exception("Single-key dictionary expected")
        return item_list[0]

    def parse(self):
        """ Parse the from yaml converted data into commands. """
        for definition in self.data:
            (command_name, definition) = self._single_key_to_tuple(definition)
            command = Command(command_name)
            for sub_command in definition:
                (sub_command_name, sub_args) = self._single_key_to_tuple(sub_command)
                args = []
                kwargs = {}
                if type(sub_args) == list:
                    args = [command.parse_args(arg) for arg in sub_args]
                else:
                    if 'args' in sub_args: 
                        args = [command.parse_args(arg) for arg in sub_args['args']]
                    if 'kwargs' in sub_args:
                        kwargs = {}
                        for (arg_name, value) in sub_args['kwargs'].items():
                            kwargs[arg_name] = command.parse_args(value)
                command.add_subcommand(sub_command_name, args, kwargs)
            self.commands[command_name] = command

    def get_draw_funcs(self, command):
        """ Get the correct drawing functions for command and generate an iterator. 
            Yields (function, args, kwargs) tuples for drawing functions.
            Drawing functions can be primitives, transformations or sub-commands
        """
        reverse_transformations = []
        restore_vars = {}
        for sub_command in command.sub_commands:
            if sub_command['name'] in PRIMITIVES: 
                # Draw primitive shapes
                func_name = PRIMITIVES[sub_command['name']]
                draw_func = eval('gui.Gui.%s' % func_name)
                yield (draw_func, sub_command['args'], sub_command['kwargs'])

            elif sub_command['name'] in TRANSFORMATIONS:
                # Apply transformations
                func_name = TRANSFORMATIONS[sub_command['name']]
                reverse_func_name = REVERSE_TRANSFORMATIONS[sub_command['name']]
                draw_func = eval('gui.Gui.%s' % func_name)
                reverse_func = eval('gui.Gui.%s' % reverse_func_name)

                # Evaluate arguments, so that random values can be undone exactly as they were applied
                args, kwargs = self.evaluate_callable_args(sub_command['args'], sub_command['kwargs'])

                for var in command.vars_to_replace:
                    if var in kwargs:
                        kwargs[var] = command.vars_to_replace[var]
                # Remember the applied transformation to undo them after the command is finished
                reverse_transformations.append( (reverse_func, args, kwargs) )
                yield(draw_func, args, kwargs)

            else:
                # Apply subcommands or raise an Exception if no fitting command can be found
                if sub_command['name'] in self.commands:
                    sub_sub_command = self.commands[sub_command['name']]

                    # Sub-commands always have the same arguments: translate-x, translate-y and scale
                    # These can be used to transform the sub-command
                    evaluated_args, evaluated_kwargs = self.evaluate_callable_args(sub_command['args'], sub_command['kwargs'])

                    # Check recursion parameters
                    command.recursion_depth += 1
                    if sub_command['name'] == command.name:
                        if 'stop_recursion' in evaluated_kwargs:
                            if 'max_depth' in evaluated_kwargs['stop_recursion']:
                                if command.recursion_depth >= evaluated_kwargs['stop_recursion']['max_depth'] -1: 
                                    command.recursion_depth = 0
                                    continue
                            del evaluated_kwargs['stop_recursion']
                        if 'vars' in evaluated_kwargs:
                            # Defined variables can be replaced for the next recursion level
                            # Afterwards though, they need to be restored to their former value
                            restore_vars = {}
                            for to_replace, value in evaluated_kwargs['vars'].items():
                                restore_vars[to_replace] = command.vars_to_replace[to_replace]
                                if callable(value): 
                                    try: 
                                        value = value(command.vars_to_replace[to_replace])
                                    except:
                                        value = value()
                                command.vars_to_replace[to_replace] = value
                            del evaluated_kwargs['vars']

                    self.gui.transform(*evaluated_args, **evaluated_kwargs)

                    # Descend into the subcommand, recursively applying it
                    for (draw_func, args, kwargs) in self.get_draw_funcs(sub_sub_command):
                        for var in command.vars_to_replace:
                            if var in kwargs:
                                kwargs[var] = command.vars_to_replace[var]
                        yield (draw_func, args, kwargs)

                    # Revert the subcommand transformation
                    self.gui.reverse_transform(*evaluated_args)

                    # Revert variable assignments
                    for to_restore in restore_vars:
                        command.vars_to_replace[to_restore] = restore_vars[to_restore]
                else:    
                    raise Exception("Illegal sub_command")
        # Reset recursive variable definitions
        command.vars_to_replace = copy(command.variables)

        # Reverse all applied transformations
        reverse_transformations.reverse()
        for (func, args, kwargs) in reverse_transformations:
            func(self.gui, *args, **kwargs)


    def evaluate_callable_args(self, args, kwargs):
        """ For arguments that are callable, evaluate them and replace them with the return value.
            This is mostly used for random values which are packed into partial function objects,
            so that new random numbers can be generated with every use of a command
        """
        args = copy(args)
        kwargs = copy(kwargs)
        arg_index = 0
        for arg in args:
            if type(arg) == list:
                args[arg_index] = self.evaluate_callable_args(arg, {})[0]
            # Apply partials, mostly to get unique random values for every object
            if callable(arg): 
                args[arg_index] = arg()
            arg_index += 1
        for (arg, value) in kwargs.items():
            if callable(value): kwargs[arg] = value()
        return (args, kwargs)

    def execute(self, command_name):
        """ Execute a command. """
        command = self.commands[command_name]
        for (func, args, kwargs) in self.get_draw_funcs(command):
            (evaluated_args, evaluated_kwargs) = self.evaluate_callable_args(args, kwargs)
            try: func(self.gui, *evaluated_args, **evaluated_kwargs)
            except Exception, e:
                print e
                import pdb
                pdb.set_trace()
