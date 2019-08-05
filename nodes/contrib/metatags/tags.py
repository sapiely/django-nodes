import re
import sys
import copy
import importlib
import collections


# Common section
class SuperValue(object):
    value = '{super}'

    def __str__(self):
        return self.value


VALUE = 'value'
SUPER = SuperValue()
Q = {'None': None, '{super}': SUPER,}
ACTIONS = ('set', 'unset', 'add', 'addleft')
OPTIONS = {
    'show_empty_tags': True,
    'show_backslash': False,
}
REDICTKEY = re.compile('^(((?:^|:)[a-z][a-z0-9_]*)+)$', re.I)
REATTRS = re.compile(
    '(?:^|\\s)'  # start from start-of-line or with space char
    '([a-z0-9_:\\.-]+)'  # take attr name (g1)
    '(?: \\s*(\\+=|=\\+|=)\\s*'  # take attr sign, "+=", "=+" or "=" (g2)
    '  (?: ("|\')(.*?)(?<!\\\\)\\3 | ([^\\s"\'][^\\s]*)(?=\\s|$) )'
    # try to take left quote (g3), if left quote is taken, try to take anything
    # upto right quote, which is not prepended by slash (g4), else try to take
    # any chars, except spaces and quotes upto any space or end-of-line (g5)
    ')?'
    '(?(2) |(?=\\s|$))',
    # if sign+value part is not presented, check that space char or end-of-line
    # located after attr-name (support for html5 boolean attrs)
    re.I | re.X)


def regex_value(item, check_super=False):
    if not item[2]:
        value = Q.get(item[4], item[4]) if check_super else item[4]
    else:
        value = item[3]
    return value


def parse_plain(plain):
    value = [i.strip() for i in plain.split('\n') if i.strip()]
    mtags = {}

    for item in value:
        item = re.findall(REATTRS, item)
        if item:
            path = item[0][0].split(':')
            if not path[0] in mtags:
                mtags[path[0]] = []
            mtags[path[0]].append([path] + item)

    return mtags


def import_path(import_path, alternate=None):
    """import module by import_path"""
    try:
        module_name, value_name = import_path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        value_name = getattr(module, value_name)
    except ImportError:
        value_name = alternate
    except AttributeError:
        value_name = alternate
    return value_name


# Exceptions
class MetaTagValueError(Exception):
    def __init__(self, message, tagname=None):
        if tagname and message and isinstance(message, str):
            message = '%s: %s' % (tagname.title(), message,)
        self.tagname = tagname
        self.message = message
        self.args = (message,)


class MetaTagRegistryError(Exception):
    pass


# Main registry
class Registry(object):
    data = None
    options = None

    def __init__(self):
        self.data = {}
        self.options = OPTIONS

    def register_tag(self, name, cls):
        if name in self.data:
            raise MetaTagRegistryError('Tag "%s" is already registered.' % name)
        if isinstance(cls, str):
            cls, strcls = (import_path(cls, None) if '.' in cls else
                           getattr(sys.modules[__name__], cls, None)), cls
            if cls is None:
                raise MetaTagRegistryError('Value "%s" is not importable.' % strcls)
        if not isinstance(cls, type) or not issubclass(cls, BaseMetaTag):
            raise MetaTagRegistryError('Value "%s" is not a tag class.' % cls)
        self.data[name] = cls

    def get_tag(self, name):
        cls = self.data.get(name, None)
        if cls is None:
            raise MetaTagRegistryError('Tag "%s" is not registered.' % name)
        return cls

    def get_option(self, name, default=None):
        return self.options.get(name, default)

    def set_option(self, name, value):
        self.options[name] = value


# Meta tags container
class MetaTags(object):
    data = None
    action = None

    def __init__(self, data=None, action=None):
        tags, action_from_data = self.get_tags_from_data(data)
        self.data = tags
        self.action = self.prepare_action(action or action_from_data)

    def __add__(self, other):
        return self.add(other)

    def __iadd__(self, other):
        return self.add(other, inplace=True)

    def __radd__(self, other):
        return self.add(other, append=False)  # other is not MetaTags instance

    def __eq__(self, other):
        return (type(self) is type(other) and self.action == other.action and
                self.data == other.data)

    def __str__(self):
        return self.as_html()

    def as_plain(self):
        tags = [tag.as_plain() for name, tag in sorted(self.data.items())]
        return '\n'.join(i for i in tags if i)

    def as_html(self):
        tags = [tag.as_html() for name, tag in sorted(self.data.items())]
        return '\n'.join(i for i in tags if i)

    def prepare_action(self, value):
        return value if value in ACTIONS else 'add'

    def copy(self):
        return copy.deepcopy(self)

    def set(self, data):
        self.data, _ = self.get_tags_from_data(data)

    def add(self, other, append=True, inplace=False):
        tags, action = self.get_tags_from_data(other)
        if append:  # self + other
            this = self if inplace else self.copy()
        else:  # other + self
            this = type(self)(data=tags.values(), action=action)
            tags, action = self.copy().data, self.action

        if action in ('set', 'unset',):
            this.data = tags
        elif action in ('add', 'addleft',) and tags:
            lside, rside = ((this.data, tags,) if action == 'add' else
                            (tags, this.data,))
            for name, rtag in rside.items():
                ltag = lside.get(name, None)
                lside[name] = ltag + rtag if ltag else rtag
            this.data = lside
        return this

    def compile(self, plain):
        tags = {k: registry.get_tag(k).compile(k, v)
                for k, v in parse_plain(plain).items()}
        return tags

    def get_tags_from_data(self, data):
        if isinstance(data, str):
            tags, action = self.compile(data), 'add'
        elif isinstance(data, BaseMetaTag):
            tags, action = {data.name: data,}, 'add'
        elif isinstance(data, MetaTags):
            tags, action = data.copy().data, data.action
        elif isinstance(data, dict):
            tags, action = self.get_tags_from_dict(data)
        elif isinstance(data, collections.Iterable):
            tags, action = {tag.name: tag for tag in data}, 'add'
        else:
            tags, action = {}, 'add'
        return tags, action

    def get_tags_from_dict(self, value):
        tags, container_action = {}, value.pop(':action', 'add')
        if not container_action or not container_action in ACTIONS:
            container_action = 'add'
        for k, v in value.items():
            action = v.pop(':action', None) if isinstance(v, dict) else None
            if action is not None and not action in ACTIONS:
                action = None
            tags[k] = registry.get_tag(k)(k, v, action)

        return tags, container_action


# Meta tags classes
class BaseMetaTag(object):
    name = None
    data = None
    action = None

    tag_name = 'meta'
    tag_name_property = None
    tag_value_property = 'content'

    data_type = 'unknown'  # used only for informing users

    def __init__(self, name=None, data=None, action=None):
        self.name = name
        self.data = self.to_python(data)
        self.action = self.prepare_action(action)

        if (self.data is None and not self.action == 'unset' or
                self.data is not None and self.action == 'unset'):
            raise MetaTagValueError(
                'Value may be None only if action is unset.', self.name)

    def prepare_action(self, value):
        return value if value in ACTIONS else 'add'

    def copy(self):
        return copy.deepcopy(self)

    def to_python(self, data):
        raise NotImplementedError

    def to_plain(self, item):
        raise NotImplementedError

    def to_html(self, value):
        raise NotImplementedError

    def as_plain(self):
        raise NotImplementedError

    def as_html(self):
        raise NotImplementedError

    def __str__(self):
        return self.as_html()

    def __repr__(self):
        return '<%s %s %s>' % (self.tag_name, self.name, type(self).__name__,)

    def __eq__(self, other):
        return (type(self) is type(other) and self.name == other.name and
                self.data == other.data and self.action == other.action)

    def __add__(self, other):
        return self.add(other)

    def __iadd__(self, other):
        return self.add(other, inplace=True)

    def add(self, other, inplace=False):
        raise NotImplementedError

    @classmethod
    def compile(cls, name, values):
        raise NotImplementedError

    @classmethod
    def from_form(self, name, text, action):
        raise NotImplementedError

    # common helpers
    def _attrs_render_helper(self, attrs):
        return ' %s' % (' '.join(
            '%s="%s"' % i for i in sorted(attrs.items(), key=lambda x: x[0])
        )) if attrs else u''

    def _backslash_render_helper(self):
        return ' /' if registry.get_option('show_backslash') else ''


class StringMetaTag(BaseMetaTag):
    value_separator = ' '
    data_type = 'string'

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, dict):
            value[VALUE] = value.get(VALUE, '')
        else:
            value = {VALUE: value}
        return {k: str(v) for k, v in value.items()}

    def to_plain(self, data, sign="="):
        if data is None:
            return '%s = %s' % (self.name, data,)
        attrs = {k: v for k, v in data.items() if not k == VALUE}
        return u'%s %s "%s"%s' % (
            self.name, sign, data[VALUE], self._attrs_render_helper(attrs),
        )

    def to_html(self, data):
        if data is None:
            return ''
        value = data.get(VALUE, None)
        if value == '' and not registry.get_option('show_empty_tags'):
            return ''
        attrs = {k: v for k, v in data.items()
                 if not k == VALUE and not k.startswith(':')}
        return '<%s %s="%s" %s="%s"%s%s>' % (
            self.tag_name, self.tag_name_property, self.name,
            self.tag_value_property, value,
            self._attrs_render_helper(attrs), self._backslash_render_helper(),
        )

    def as_plain(self):
        sign = '='
        if self.action in ('add', 'addleft',):
            sign = '=+' if self.action == 'add' else '+='
        return self.to_plain(self.data, sign=sign)

    def as_html(self):
        return self.to_html(self.data)

    def add(self, other, inplace=False):
        if type(self) is not type(other):
            raise MetaTagValueError(
                'It is possible to add only same typed tag.', self.name)
        this = self if inplace else self.copy()

        if other.action in ('set', 'unset',):
            this.data = other.data
        elif other.action in ('add', 'addleft',):
            if this.action == 'unset' and this.data is None:
                this.data = {VALUE: '',}

            localdata = {k:v for k, v in this.data.items() if not k == VALUE}
            otherdata = {k:v for k, v in other.data.items()
                         if not k == VALUE and not k.startswith(':')}
            separator = other.data.get(':separator', this.value_separator)
            if other.action == 'add':
                value = this.data[VALUE] + separator + other.data[VALUE]
                attrs = {**localdata, **otherdata}
            else:
                value = other.data[VALUE] + separator + this.data[VALUE]
                attrs = {**otherdata, **localdata}
            this.data = {**attrs, VALUE: value.strip()}

        return this

    @classmethod
    def compile(cls, name, values, as_tag=True):
        value = regex_value(values[0][1], check_super=True)
        attrs = {i[0]: regex_value(i) for i in values[0][2:]}

        if not len(values) == 1:
            raise MetaTagValueError(
                'Value should be defined in one line.', name)
        elif value == SUPER:
            raise MetaTagValueError(
                'Value should not contains "%s".' % SUPER, name)
        elif not len(values[0][0]) == 1:
            raise MetaTagValueError(
                'Tag name definition should not contains colon.', name)

        if value is None:
            action = 'unset'
        elif '+' in values[0][1][1]:
            action = 'add' if values[0][1][1] == '=+' else 'addleft'
        else:
            action = 'set'

        data = dict(attrs, **{VALUE: value}) if value is not None else None
        return cls(name, data, action) if as_tag else (data, action,)

    @classmethod
    def from_form(cls, name, text, action):
        text = text.strip()
        if text in (str(SUPER), 'None'):
            raise MetaTagValueError(
                '%s/%s value should not be defined in form fields,'
                ' use action value instead.' % (SUPER, None,), name)
        if text if action == 'unset' else not text:
            raise MetaTagValueError(
                'Value should be empty only if action is "unset".', name)
        if len(text.splitlines()) > 1:
            raise MetaTagValueError(
                'Value should be defined in one line.', name)

        sign = '='
        if action in ('add', 'addleft',):
            sign = '=+' if action == 'add' else '+='

        if action == 'unset':
            text = 'None'
        elif text[0] not in '\'"' and not '=' in text and ' ' in text:
            text = '"%s"' % text

        plain = ''.join((name, sign, text,))
        parsed = parse_plain(plain)
        return cls.compile(name, parsed[name], as_tag=True)


class SeparatedValueMetaTag(StringMetaTag):
    value_separator = ', '
    data_type = 'separated string'

    def to_python(self, data):
        if data is None:
            return None

        if isinstance(data, dict):
            item = data.get(VALUE, '')
        else:
            item, data = data, {}

        if isinstance(item, str):
            item = [i.strip() for i in item.split(self.value_separator.strip())
                    if i.strip()]
        if not isinstance(item, (list, tuple,)):
            item = [item]
        item = [str(i) for i in item]

        return {**data, VALUE: item}

    def as_plain(self):
        sign = '='
        if self.action in ('add', 'addleft',):
            sign = '=+' if self.action == 'add' else '+='
        if self.data is not None:
            value = self.value_separator.join(self.data[VALUE])
            value = {**self.data, VALUE: value}
        else:
            value = None
        return self.to_plain(value, sign=sign)

    def as_html(self):
        if self.data is not None:
            value = self.value_separator.join(self.data[VALUE])
            value = {**self.data, VALUE: value}
        else:
            value = None
        return self.to_html(value)

    def add(self, other, inplace=False):
        if not type(self) is type(other):
            raise MetaTagValueError(
                'It is possible to add only same typed tag.', self.name)
        this = self if inplace else self.copy()

        if other.action in ('set', 'unset',):
            this.data = other.data
        elif other.action in ('add', 'addleft',):
            if this.action == 'unset' and this.data is None:
                this.data = {VALUE: [],}

            localdata = {k:v for k, v in this.data.items() if not k == VALUE}
            otherdata = {k:v for k, v in other.data.items()
                         if not k == VALUE and not k.startswith(':')}
            if other.action == 'add':
                value = this.data[VALUE] + other.data[VALUE]
                attrs = {**localdata, **otherdata}
            else:
                value = other.data[VALUE] + this.data[VALUE]
                attrs = {**otherdata, **localdata}
            this.data = {**attrs, VALUE: value}

        return this

    @classmethod
    def compile(cls, name, values, as_tag=True):
        value = regex_value(values[0][1], check_super=True)
        attrs = {i[0]: regex_value(i) for i in values[0][2:]}

        if not len(values) == 1:
            raise MetaTagValueError(
                'Value should be defined in one line.', name)
        elif value == SUPER:
            raise MetaTagValueError(
                'Value should not contains "%s".' % SUPER, name)
        elif not len(values[0][0]) == 1:
            raise MetaTagValueError(
                'Tag name definition should not contains colon.', name)

        if value is None:
            action = 'unset'
        elif '+' in values[0][1][1]:
            action = 'add' if values[0][1][1] == '=+' else 'addleft'
        else:
            action = 'set'

        data = {**attrs, **{VALUE: value}} if value is not None else None
        return cls(name, data, action) if as_tag else (data, action,)


class ListMetaTag(BaseMetaTag):
    data_type = 'list'

    def to_python(self, data):
        if data is None:
            return None
        data = data if isinstance(data, (list, tuple,)) else [data]
        for index, item in enumerate(data):
            if isinstance(item, dict):
                item[VALUE] = item.get(VALUE, '')
            else:
                data[index] = {VALUE: item}
            data[index] = {k: str(v) for k, v in data[index].items()}
        return data

    def to_plain(self, data):
        if data is None:
            return '%s = %s' % (self.name, data,)
        attrs = {k: v for k, v in data.items() if not k == VALUE}
        return '%s = "%s"%s' % (
            self.name, data[VALUE], self._attrs_render_helper(attrs),
        )

    def to_html(self, data):
        if data is None:
            return ''
        value = data.get(VALUE, None)
        if value == '' and not registry.get_option('show_empty_tags'):
            return ''
        attrs = {k: v for k, v in data.items()
                 if not k == VALUE and not k.startswith(':')}
        return u'<%s %s="%s" %s="%s"%s%s>' % (
            self.tag_name, self.tag_name_property, self.name,
            self.tag_value_property, value,
            self._attrs_render_helper(attrs), self._backslash_render_helper(),
        )

    def as_plain(self):
        if self.data is None:
            return self.to_plain(self.data)
        lines = [self.to_plain(item) for item in self.data]
        if self.action in ('add', 'addleft',):
            lines.insert(0 if self.action == 'add' else len(lines),
                         '%s = %s' % (self.name, SUPER,))
        return '\n'.join(lines)

    def as_html(self):
        if self.data is None:
            return ''
        return '\n'.join(self.to_html(item) for item in self.data)

    def add(self, other, inplace=False):
        if not type(self) is type(other):
            raise MetaTagValueError(
                'It is possible to add only same typed tag.', self.name)
        this = self if inplace else self.copy()

        if other.action in ('set', 'unset',):
            this.data = other.data
        elif other.action in ('add', 'addleft',):
            if this.action == 'unset' and this.data is None:
                this.data = []

            if other.action == 'add':
                value = this.data + other.data
            else:
                value = other.data + this.data
            this.data = value

        return this

    @classmethod
    def compile(cls, name, values, as_tag=True):
        if not max([len(i[0]) for i in values]) == 1:
            raise MetaTagValueError(
                'Tag name definition should not contains colon.', name)

        data, super_indexes = [], []
        for index, vitem in enumerate(values):
            value = regex_value(vitem[1], check_super=True)
            attrs = {i[0]: regex_value(i) for i in vitem[2:]}
            if value == SUPER:
                super_indexes.append(index-len(super_indexes))
                continue
            data.append({**attrs, **{VALUE: value}})

        if len(super_indexes) > 1:
            raise MetaTagValueError(
                'Values should not contain more than one %s.' % SUPER, name)
        if len(data) > 1 and None in [i[VALUE] for i in data]:
            raise MetaTagValueError(
                'None value should be only one value in a tag.', name)

        if len(data) == 1 and data[0][VALUE] is None:
            action, data = 'unset', None
        elif super_indexes:
            action = 'add' if super_indexes[0] == 0 else 'addleft'
        else:
            action = 'set'

        return cls(name, data, action) if as_tag else (data, action,)

    @classmethod
    def from_form(cls, name, text, action):
        values = [i.strip() for i in text.strip().replace('\r', '').split('\n')
                  if i.strip()]
        if str(SUPER) in values or 'None' in values:
            raise MetaTagValueError(
                '%s/%s value should not be defined in form fields,'
                ' use action value instead.' % (SUPER, None,), name)
        if values if action == 'unset' else not values:
            raise MetaTagValueError(
                'Value should be empty only if action is "unset".', name)

        for index, value in enumerate(values):
            if value[0] not in '\'"' and '=' not in value and ' ' in value:
                values[index] = '"%s"' % value

        if action == 'unset':
            values = ['None']
        elif action in ('add', 'addleft',):
            values.insert(0 if action == 'add' else len(values), str(SUPER))

        plain = '\n'.join('%s = %s' % (name, v,) for v in values)
        parsed = parse_plain(plain)
        return cls.compile(name, parsed[name], as_tag=True)


class DictMetaTag(BaseMetaTag):
    data_type = 'dict'

    def to_python(self, data):
        if data is None:
            return None
        if not isinstance(data, dict):
            raise MetaTagValueError('Value may be only dict.', self.name)
        return self._to_python_rec_helper(data)

    def to_plain(self, item, name=None):
        if item is None:
            return '%s = %s' % (self.name, item,)
        return '%s = "%s"' % (name or self.name, item,)

    def to_html(self, data, name=None):
        if data is None:
            return ''
        if data == '' and not registry.get_option('show_empty_tags'):
            return ''
        return '<%s %s="%s" %s="%s"%s>' % (
            self.tag_name, self.tag_name_property, name or self.name,
            self.tag_value_property, data, self._backslash_render_helper()
        )

    def as_plain(self):
        if self.data is None:
            return self.to_plain(self.data)
        lines = list(self._to_string_rec_helper(self.data, [self.name],
                                                self.to_plain))
        if self.action in ('add', 'addleft'):
            lines.insert(0 if self.action == 'add' else len(lines),
                         '%s = %s' % (self.name, SUPER))
        return '\n'.join(lines)

    def as_html(self):
        return '\n'.join(list(self._to_string_rec_helper(
            self.data, [self.name], self.to_html
        ))) if self.data is not None else ''

    def add(self, other, inplace=False):
        if not type(self) is type(other):
            raise MetaTagValueError(
                'It is possible to add only same typed tag.', self.name)
        this = self if inplace else self.copy()

        if other.action in ('set', 'unset',):
            this.data = other.data
        elif other.action in ('add', 'addleft',):
            if this.action == 'unset' and this.data is None:
                this.data = {}

            if other.action == 'add':
                ldata, rdata = this.data, other.data
            else:
                ldata, rdata = other.data, this.data
            this.data = self._dicts_merge_rec_helper(copy.deepcopy(ldata),
                                                     copy.deepcopy(rdata))

        return this

    @classmethod
    def compile(cls, name, values, as_tag=True):
        if not values:
            raise MetaTagValueError('Value should be set correctly.', name)

        vroot = [(i, regex_value(v[1], check_super=True),)
                 for i, v in enumerate(values) if len(v[0]) == 1]
        values = [i for i in values if len(i[0]) > 1]

        if vroot:
            if len(vroot) > 1:
                raise MetaTagValueError(
                    'Value have more than one root entities.', name)
            if vroot[0][1] is None and (vroot[0][0] > 0 or values):
                raise MetaTagValueError(
                    'None value should be only one value in a tag.', name)
            if vroot[0][1] not in (None, SUPER):
                raise MetaTagValueError(
                    'Root value should be only %s or %s.' % (None, SUPER,), name)

        if values and not all(len(i) == 2 for i in values):
            raise MetaTagValueError(
                'Additional attrs setting is not allowed in dict tags.', name)

        iroot, vroot = vroot[0] if vroot else (0, False,)
        if vroot == SUPER:
            action = 'addleft' if iroot > 0 else 'add'
        elif vroot is None:
            action = 'unset'
        else:
            action = 'set'

        if action == 'unset':
            data = None
        else:
            data = cls._dict_value_processor_helper(values)

        return cls(name, data, action) if as_tag else (data, action,)

    @classmethod
    def from_form(cls, name, text, action):
        values = [i.strip() for i in text.strip().replace('\r', '').split('\n')
                  if i.strip()]
        if str(SUPER) in values or 'None' in values:
            raise MetaTagValueError(
                '%s/%s value should not be defined in form fields,'
                ' use action value instead.' % (SUPER, None,), name)
        if values if action == 'unset' else not values:
            raise MetaTagValueError(
                'Value should be empty only if action is "unset".', name)

        values = [[j.strip() for j in i.strip().split('=', 1)] for i in values]

        for v in values:
            if not len(v) == 2 or not v[0]:
                raise MetaTagValueError(
                    'Non empty keys and values devided by "=" sign'
                    ' are required in dict tags.', name)
            if not re.match(REDICTKEY, v[0]):
                raise MetaTagValueError(
                    'Key value error "%s" (allowed only a-z, 0-9, _ and :,'
                    ' e.g. "a0:z9")' % v[0], name)

        for v in values:
            if v[1] and v[1][0] not in '\'"' and not '=' in v[1] and ' ' in v[1]:
                v[1] = '"%s"' % v[1]

        if action == 'unset':
            values = ['None']
        elif action in ('add', 'addleft',):
            values.insert(0 if action == 'add' else len(values), str(SUPER))

        plain = '\n'.join((
            '%s:%s = %s' % (name, *value,) if len(value) == 2 else
            '%s = %s' % (name, value,)
        ) for value in values)

        parsed = parse_plain(plain)
        return cls.compile(name, parsed.get(name, None), as_tag=True)

    # dict helpers
    def _to_python_rec_helper(self, data):
        if isinstance(data, dict):
            for k, v in data.items():
                data[k] = self._to_python_rec_helper(v)
        elif isinstance(data, (list, tuple)):
            data = [self._to_python_rec_helper(i) for i in data]
        else:
            data = str(data)
        return data

    def _to_string_rec_helper(self, data, path, method, level=0):
        if isinstance(data, (list, tuple,)):
            for item in data:
                if isinstance(item, dict):
                    for html in self._to_string_rec_helper(item, path, method,
                                                           level+1):
                        yield html
                # ignore any list/tuple value inside other list/tuple
                elif not isinstance(item, (list, tuple,)):
                    yield method(str(item), name=':'.join(path))
        else:
            # ignore VALUE on zero level and non scalar VALUE on 1+ levels
            if (level and VALUE in data and
                    not isinstance(data[VALUE], (dict, list, tuple,))):
                yield method(str(data[VALUE]), name=':'.join(path))

            for key, value in sorted((k, v,) for k, v in data.items()
                                     if not k == VALUE):
                if isinstance(value, (list, tuple, dict,)):
                    for html in self._to_string_rec_helper(value, path + [key],
                                                           method, level+1):
                        yield html
                else:
                    yield method(str(value), name=':'.join(path + [key]))

    def _dicts_merge_rec_helper(self, left, right):
        for k, v in right.items():
            if isinstance(v, dict) and k in left and isinstance(left[k], dict):
                self._dicts_merge_rec_helper(left[k], right[k])
            else:
                left[k] = v
        return left

    @classmethod
    def _dict_value_processor_helper(cls, items):
        value = {}
        for key, item in items:
            vitem = regex_value(item, check_super=False)
            parent = value
            for i in key[1:-1]:
                if not i in parent:
                    parent[i] = {}
                    parent = parent[i]
                elif isinstance(parent[i], list):
                    if not isinstance(parent[i][-1], dict):
                        parent[i][-1] = {VALUE: parent[i][-1]}
                    parent = parent[i][-1]
                elif isinstance(parent[i], dict):
                    parent = parent[i]
                else:
                    parent[i] = {VALUE: parent[i]}
                    parent = parent[i]

            if key[-1] in parent:
                if not isinstance(parent[key[-1]], list):
                    parent[key[-1]] = [parent[key[-1]]]
                parent[key[-1]].append(vitem)
            else:
                parent[key[-1]] = vitem
        return value

# Builtin meta tags
class NameContentStringMetaTag(StringMetaTag):
    tag_name_property = 'name'


class HttpEquivContentStringMetaTag(StringMetaTag):
    tag_name_property = 'http-equiv'


class NameContentListMetaTag(ListMetaTag):
    tag_name_property = 'name'


class HttpEquivContentListMetaTag(ListMetaTag):
    tag_name_property = 'http-equiv'


class NameContentDictMetaTag(DictMetaTag):
    tag_name_property = 'name'


class PropertyContentDictMetaTag(DictMetaTag):
    tag_name_property = 'property'


class NameContentCommaSpaceSeparatedValueMetaTag(SeparatedValueMetaTag):
    tag_name_property = 'name'
    value_separator = u', '


class NameContentCommaSeparatedValueMetaTag(SeparatedValueMetaTag):
    tag_name_property = 'name'
    value_separator = u','


# registry instance
registry = Registry()
