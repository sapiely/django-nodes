from inspect import getargspec
from functools import partial
from django.utils import six
from django.template.base import TagHelperNode, Template, generic_tag_compiler
from django import template

def get_from_context(context, variable='request'):
    value = context.get(variable, None)
    if value is None:
        raise template.VariableDoesNotExist('Variable "%s" does not exists.' % variable)
    return value

def inclusion_tag(register, takes_context=False, name=None):
    """
    inclusion_tag decorator: works like original,
    but takes "file_name" variable from result of function call
    requires register object as first param
    note: all code ripped from django except "fix:" strings
    """
    def dec(func):
        params, varargs, varkw, defaults = getargspec(func)

        class InclusionNode(TagHelperNode):

            def render(self, context):
                """
                Renders the specified template and context. Caches the
                template object in render_context to avoid reparsing and
                loading when used in a for loop.
                """
                resolved_args, resolved_kwargs = self.get_resolved_arguments(context)
                _dict = func(*resolved_args, **resolved_kwargs)

                # fix: get template name from func result
                file_name = _dict.get('template', None)

                t = context.render_context.get(self)
                if t is None:
                    if isinstance(file_name, Template):
                        t = file_name
                    elif isinstance(getattr(file_name, 'template', None), Template):
                        t = file_name.template
                    elif not isinstance(file_name, six.string_types) and is_iterable(file_name):
                        t = context.template.engine.select_template(file_name)
                    else:
                        t = context.template.engine.get_template(file_name)
                    context.render_context[self] = t
                new_context = context.new(_dict)
                # Copy across the CSRF token, if present, because
                # inclusion tags are often used for forms, and we need
                # instructions for using CSRF protection to be as simple
                # as possible.
                csrf_token = context.get('csrf_token', None)
                if csrf_token is not None:
                    new_context['csrf_token'] = csrf_token
                return t.render(new_context)

        function_name = (name or
            getattr(func, '_decorated_function', func).__name__)
        compile_func = partial(generic_tag_compiler,
            params=params, varargs=varargs, varkw=varkw,
            defaults=defaults, name=function_name,
            takes_context=takes_context, node_class=InclusionNode)
        compile_func.__doc__ = func.__doc__
        # fix: replace self object with register object (not method)
        register.tag(function_name, compile_func)
        return func
    return dec
