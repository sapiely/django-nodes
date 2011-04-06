# -*- coding: utf-8 -*-
from django import template
from django.template import Node, generic_tag_compiler, Variable, TemplateSyntaxError
from django.template.context import Context
from django.utils.functional import curry
from inspect import getargspec

def get_from_context(context, variable='request'):
    value = context.get(variable, None)
    if value is None:
        raise VariableDoesNotExist('Variable "%s" does not exists.' % variable)
    return value

def simple_tag_ex(register, func, takes_context=False):
    """
    simple_tag_ex decorater: works like original, 
    but takes "takes_context" variable like inclusion_tag
    requires register as first param
    """

    params, xx, xxx, defaults = getargspec(func)

    if takes_context:
        if params[0] == 'context':
            params = params[1:]
        else:
            raise TemplateSyntaxError("Any tag function with takes_context set must have a first argument of 'context'")

    class SimpleNode(Node):
        def __init__(self, vars_to_resolve):
            self.vars_to_resolve = map(Variable, vars_to_resolve)

        def render(self, context):
            resolved_vars = [var.resolve(context) for var in self.vars_to_resolve]
            if takes_context:
                return func(context, *resolved_vars)
            else:
                return func(*resolved_vars)

    compile_func = curry(generic_tag_compiler, params, defaults, getattr(func, "_decorated_function", func).__name__, SimpleNode)
    compile_func.__doc__ = func.__doc__
    register.tag(getattr(func, "_decorated_function", func).__name__, compile_func)
    return func

def inclusion_tag_ex(register, context_class=Context, takes_context=False):
    """
    inclusion_tag_ex decorater: works like original, 
    but takes "file_name" variable from result of function call
    requires register as first param
    """
    
    def dec(func):
        params, xx, xxx, defaults = getargspec(func)
        if takes_context:
            if params[0] == 'context':
                params = params[1:]
            else:
                raise TemplateSyntaxError("Any tag function decorated with takes_context=True must have a first argument of 'context'")
        
        class InclusionNode(Node):
            def __init__(self, vars_to_resolve):
                self.vars_to_resolve = map(Variable, vars_to_resolve)

            def render(self, context):
                resolved_vars = [var.resolve(context) for var in self.vars_to_resolve]
                if takes_context:
                    args = [context] + resolved_vars
                else:
                    args = resolved_vars

                extra_context = func(*args)
                file_name = extra_context.get('template', None)
                if not file_name:
                    raise TemplateSyntaxError('Result of fuction, decorated with "inclusion_tag_ex" must contains "template" variable.')

                from django.template.loader import get_template, select_template
                if not isinstance(file_name, basestring) and is_iterable(file_name):
                    t = select_template(file_name)
                else:
                    t = get_template(file_name)
                self.nodelist = t.nodelist
                new_context = context_class(extra_context, autoescape=context.autoescape)
                # Copy across the CSRF token, if present, because inclusion
                # tags are often used for forms, and we need instructions
                # for using CSRF protection to be as simple as possible.
                csrf_token = context.get('csrf_token', None)
                if csrf_token is not None:
                    new_context['csrf_token'] = csrf_token
                return self.nodelist.render(new_context)

        compile_func = curry(generic_tag_compiler, params, defaults, getattr(func, "_decorated_function", func).__name__, InclusionNode)
        compile_func.__doc__ = func.__doc__
        register.tag(getattr(func, "_decorated_function", func).__name__, compile_func)
        return func
    return dec