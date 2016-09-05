import functools
from inspect import getargspec
from django.utils import six
from django.template.base import Template
from django.template.library import InclusionNode, parse_bits
from django import template


def get_from_context(context, variable='request'):
    value = context.get(variable, None)
    if value is None:
        raise template.VariableDoesNotExist('Variable "%s" does not exists.' % variable)
    return value


class InclusionNode(InclusionNode):

    def render(self, context):
        """
        Render the specified template and context. Cache the template object
        in render_context to avoid reparsing and loading when used in a for
        loop.

        FIXES:
        Note: all code ripped from django except "fix:" strings
        """
        resolved_args, resolved_kwargs = self.get_resolved_arguments(context)
        _dict = self.func(*resolved_args, **resolved_kwargs)

        # fix: get template name from func result and do nothing if it empty (3 lines)
        self.filename = _dict.get('template', None)
        if not self.filename:
            return u''

        t = context.render_context.get(self)
        if t is None:
            if isinstance(self.filename, Template):
                t = self.filename
            elif isinstance(getattr(self.filename, 'template', None), Template):
                t = self.filename.template
            elif not isinstance(self.filename, six.string_types) and is_iterable(self.filename):
                t = context.template.engine.select_template(self.filename)
            else:
                t = context.template.engine.get_template(self.filename)
            context.render_context[self] = t
        new_context = context.new(_dict)
        # Copy across the CSRF token, if present, because inclusion tags are
        # often used for forms, and we need instructions for using CSRF
        # protection to be as simple as possible.
        csrf_token = context.get('csrf_token')
        if csrf_token is not None:
            new_context['csrf_token'] = csrf_token
        return t.render(new_context)


def inclusion_tag(register, func=None, takes_context=None, name=None):
    """
    Register a callable as an inclusion tag:

    @register.inclusion_tag('results.html')
    def show_results(poll):
        choices = poll.choice_set.all()
        return {'choices': choices}

    FIXES:
    Info: inclusion_tag decorator - works like original,
        but takes "template" variable from result of function call,
        requires template register object as first param
    Note: all code ripped from django except "fix:" strings
    Todo: register modified InclusionNode by regular register.tag call
    """

    def dec(func):
        params, varargs, varkw, defaults = getargspec(func)
        function_name = (name or getattr(func, '_decorated_function', func).__name__)

        @functools.wraps(func)
        def compile_func(parser, token):
            bits = token.split_contents()[1:]
            args, kwargs = parse_bits(
                parser, bits, params, varargs, varkw, defaults,
                takes_context, function_name,
            )
            return InclusionNode(
                func, takes_context, args, kwargs, '',
            )
        # fix: replace self object with register object (not method)
        register.tag(function_name, compile_func)
        return func
    return dec
