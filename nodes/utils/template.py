from functools import wraps
from inspect import getfullargspec
from django.template.base import Template
from django.template.library import InclusionNode, parse_bits
from django import template


def get_from_context(context, variable='request'):
    value = context.get(variable, None)
    if value is None:
        raise template.VariableDoesNotExist(
            'Variable "%s" does not exists.' % variable)
    return value


# Inclusion tags
class ContextTemplateInclusionNode(InclusionNode):

    def render(self, context):
        """
        Render the specified template and context. Cache the template object
        in render_context to avoid reparsing and loading when used in a for
        loop.
        """
        resolved_args, resolved_kwargs = self.get_resolved_arguments(context)
        _dict = self.func(*resolved_args, **resolved_kwargs)

        # get template name from func result first,
        # from instance second and do nothing if it empty
        filename = _dict.get('template', self.filename)
        if not filename:
            return ''

        t = context.render_context.get(self)
        if t is None:
            if isinstance(filename, Template):
                t = filename
            elif isinstance(getattr(filename, 'template', None), Template):
                t = filename.template
            elif not isinstance(filename, str) and is_iterable(filename):
                t = context.template.engine.select_template(filename)
            else:
                t = context.template.engine.get_template(filename)
            context.render_context[self] = t
        new_context = context.new(_dict)
        # Copy across the CSRF token, if present, because inclusion tags are
        # often used for forms, and we need instructions for using CSRF
        # protection to be as simple as possible.
        csrf_token = context.get('csrf_token')
        if csrf_token is not None:
            new_context['csrf_token'] = csrf_token
        return t.render(new_context)


def inclusion_tag_function(func, takes_context=None, filename=None,
                           inclusion_node_class=ContextTemplateInclusionNode):
    """
    Generate a callable to be registered as an inclusion tag.
    - func - function to be called inside to generate context
    - takes_context - add template context as a first args into function
    - filename - template filename to be used by default in inclusion tag
    - inclusion_node_class - InclusionNode class to register in library
    """

    (params, varargs, varkw, defaults,
     kwonly, kwonly_defaults, annotations) = getfullargspec(func)
    function_name = getattr(func, '_decorated_function', func).__name__

    @wraps(func)
    def compile_func(parser, token):
        bits = token.split_contents()[1:]
        args, kwargs = parse_bits(
            parser, bits, params, varargs, varkw, defaults,
            kwonly, kwonly_defaults, takes_context, function_name
        )
        return inclusion_node_class(func, takes_context, args, kwargs, filename)
    return compile_func


# Block tags
class BlockTagFunction:
    tag_name = 'blocktag'
    function_name = 'block_tag_function'
    takes_context = True
    template_node_class = None

    def __init__(self, tag_name=None, function_name=None, takes_context=None,
                 template_node_class=None):
        self.tag_name = tag_name or self.tag_name
        self.tag_name = self.__name__ = tag_name or self.tag_name
        self.function_name = function_name or self.function_name
        self.takes_context = (
            self.takes_context if takes_context is None else takes_context)
        self.template_node_class = (template_node_class or
                                    self.template_node_class)

    def __call__(self, parser, token):
        bits = token.split_contents()[1:]
        params, varargs, varkw, defaults, kwonly, kwonly_defaults = (
            ['context',] if self.takes_context else [],
            'args', 'kwargs', (), [], {},
        )

        target_var = None
        if len(bits) >= 2 and bits[-2] == 'as':
            target_var = bits[-1]
            bits = bits[:-2]

        args, kwargs = parse_bits(
            parser, bits, params, varargs, varkw, defaults,
            kwonly, kwonly_defaults, self.takes_context, self.function_name
        )

        nodelist = parser.parse(('end%s' % self.tag_name,))
        parser.delete_first_token()
        return self.template_node_class(nodelist, args, kwargs, target_var)


class BlockTagNode(template.Node):
    cache_prefix = 'blocktag'
    cache_ns = 'ns'
    cache_timeout = 100

    def __init__(self, nodelist, args, kwargs, target_var):
        self.nodelist = nodelist
        self.args = args
        self.kwargs = kwargs
        self.target_var = target_var

    def get_resolved_arguments(self, context):
        resolved_args = [context] + [var.resolve(context) for var in self.args]
        resolved_kwargs = {k: v.resolve(context) for k, v in self.kwargs.items()}
        return resolved_args, resolved_kwargs

    def get_cache_kwargs(self, resolved_kwargs):
        cache_timeout = resolved_kwargs.get('cache_timeout', None)
        cache_timeout = (isinstance(cache_timeout, int) and cache_timeout or
                         self.cache_timeout)
        cache_ns = resolved_kwargs.get('cache_ns', self.cache_ns)
        cache_key = resolved_kwargs.get('cache_key', None)
        cache_key = ('%s:%s:%s' % (self.cache_prefix, cache_ns, cache_key,)
                     if cache_key else None)
        return (cache_key, cache_timeout,) if cache_key else (None, None,)
