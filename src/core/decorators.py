# src/core/decorators.py


def method_args_as_command_params (func):
    func._method_args_as_command_params = True
    return func

def hidden_method (func):
    func._hidden = True
    return func

def method_for_bot_interface (func):
    func._method_for_bot_interface = True
    return func
