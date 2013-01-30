from functools import partial
from inspect import getargspec
from django import template
from django.template.base import TagHelperNode, Template, generic_tag_compiler
from django.template.context import Context

def get_from_context(context, variable='request'):
    value = context.get(variable, None)
    if value is None:
        raise template.VariableDoesNotExist('Variable "%s" does not exists.' % variable)
    return value

def inclusion_tag_ex(register, context_class=Context, takes_context=False, name=None):
    """
    inclusion_tag_ex decorator: works like original,
    but takes "file_name" variable from result of function call
    requires register object as first param
    note: all code ripped from django except "fix:" strings
    """

    def dec(func):
        params, varargs, varkw, defaults = getargspec(func)

        class InclusionNode(TagHelperNode):

            def render(self, context):
                resolved_args, resolved_kwargs = self.get_resolved_arguments(context)
                _dict = func(*resolved_args, **resolved_kwargs)
                
                # fix: get template name from func result
                file_name = _dict.get('template', None)

                if not getattr(self, 'nodelist', False):
                    from django.template.loader import get_template, select_template
                    if isinstance(file_name, Template):
                        t = file_name
                    elif not isinstance(file_name, basestring) and is_iterable(file_name):
                        t = select_template(file_name)
                    else:
                        t = get_template(file_name)
                    self.nodelist = t.nodelist
                new_context = context_class(_dict, **{
                    'autoescape': context.autoescape,
                    'current_app': context.current_app,
                    'use_l10n': context.use_l10n,
                    'use_tz': context.use_tz,
                })
                # Copy across the CSRF token, if present, because
                # inclusion tags are often used for forms, and we need
                # instructions for using CSRF protection to be as simple
                # as possible.
                csrf_token = context.get('csrf_token', None)
                if csrf_token is not None:
                    new_context['csrf_token'] = csrf_token
                return self.nodelist.render(new_context)

        function_name = (name or getattr(func, '_decorated_function', func).__name__)
        compile_func = partial(generic_tag_compiler, 
                               params=params, varargs=varargs, varkw=varkw,
                               defaults=defaults, name=function_name,
                               takes_context=takes_context, node_class=InclusionNode)
        compile_func.__doc__ = func.__doc__

        # fix: replace self object with register (not method)
        register.tag(function_name, compile_func)

        return func
    return dec