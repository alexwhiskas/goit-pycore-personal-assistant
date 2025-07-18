# src/core/decorators.py


def method_args_as_command_params (func):
    func._method_args_as_command_params = True
    return func


def hidden_method (func):
    func._hidden = True
    return func
