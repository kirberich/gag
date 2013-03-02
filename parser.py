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

    def add_subcommand(self, command_name, command_args, command_kwargs):
        self.sub_commands.append( {'name':command_name, 'args':command_args, 'kwargs':command_kwargs} ) 

    def __repr__(self):
        return "Command %s: %s" % (self.name, self.sub_commands)


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
        m = re.match(r'^c\((\d*\.?\d+),(\d*\.?\d+),(\d*\.?\d+)(?:,(\d*\.?\d+))?\)$', arg)
        if m:
            r = float(m.groups()[0])
            g = float(m.groups()[1])
            b = float(m.groups()[2])
            if m.groups()[3]: 
                a = float(m.groups()[3])
            else:
                a = 1
            return gui.Color(r,g,b,a)
        return arg

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
                    args = [self.parse_args(arg) for arg in sub_args]
                else:
                    if 'args' in sub_args: 
                        args = [self.parse_args(arg) for arg in sub_args['args']]
                    if 'kwargs' in sub_args:
                        kwargs = {}
                        for (arg_name, value) in sub_args['kwargs'].items():
                            kwargs[arg_name] = self.parse_args(value)
                command.add_subcommand(sub_command_name, args, kwargs)
            self.commands[command_name] = command

    def get_draw_funcs(self, command):
        """ Get the correct drawing functions for command and generate an iterator. 
            Yields (function, args, kwargs) tuples for drawing functions.
            Drawing functions can be primitives, transformations or sub-commands
        """
        reverse_transformations = []
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
                    self.gui.transform(*evaluated_args, **evaluated_kwargs)

                    # Descend into the subcommand, recursively applying it
                    for (draw_func, args, kwargs) in self.get_draw_funcs(sub_sub_command):
                        yield (draw_func, args, kwargs)

                    # Reverse the subcommand transformation
                    self.gui.reverse_transform(*evaluated_args, **evaluated_kwargs)
                else:    
                    raise Exception("Illegal sub_command")
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
            args, kwargs = self.evaluate_callable_args(args, kwargs)
            func(self.gui, *args, **kwargs)
