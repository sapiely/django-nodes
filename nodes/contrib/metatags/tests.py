import unittest

from tags import (
    registry, VALUE, REATTRS, SUPER, parse_plain, import_path,
    MetaTags, MetaTagValueError, MetaTagRegistryError,
    NameContentStringMetaTag, NameContentCommaSpaceSeparatedValueMetaTag,
    NameContentListMetaTag, NameContentDictMetaTag, PropertyContentDictMetaTag
)


registry.register_tag('description', NameContentStringMetaTag)
registry.register_tag('keywords', NameContentCommaSpaceSeparatedValueMetaTag)
registry.register_tag('generator', NameContentListMetaTag)
registry.register_tag('og', PropertyContentDictMetaTag)
registry.register_tag('twitter', NameContentDictMetaTag)


class MetaTagsCommonTest(unittest.TestCase):
    def test_REATTRS(self):
        checkers = [
            # value without spaces and starting quotes
            ('attr=any-~!@#$%^&*()_+}{:?><\'"-value',
             [('attr', '=', '', '', 'any-~!@#$%^&*()_+}{:?><\'"-value'),],),
            # value with quotes and without
            ('a=a b="b" c="c"d="d" e=e"e f="ff\\" ff" g=\'"g"\' h="h"# i="i j="j" k="k l=l\'',
             [('a', '=', '', '', 'a'), ('b', '=', '"', 'b', ''),
              ('c', '=', '"', 'c', ''), ('e', '=', '', '', 'e"e'),
              ('f', '=', '"', 'ff\\" ff', ''), ('g', '=', "'", '"g"', ''),
              ('h', '=', '"', 'h', ''), ('i', '=', '"', 'i j=', ''),
              ('l', '=', '', '', "l'"),],),
            # multiple also with spaces around sign
            ('a = a  b=b c= c d =d',
             [('a', '=', '', '', 'a'), ('b', '=', '', '', 'b'),
              ('c', '=', '', '', 'c'), ('d', '=', '', '', 'd'),],),
            # variant of sign
            ('a=a b+=b c=+c d+=+d e+ =e f=++f g++=g h==h',
             [('a', '=', '', '', 'a'), ('b', '+=', '', '', 'b'),
              ('c', '=+', '', '', 'c'), ('d', '+=', '', '', '+d'),
              ('f', '=+', '', '', '+f'), ('h', '=', '', '', '=h'),],),
            # attr name allowed chars
            ('any-_:.azAZ09-attr-name=value',
             [('any-_:.azAZ09-attr-name', '=', '', '', 'value'),],),
            # attr starts with space or at start-of-line and ends
            # at space or end-of-line if value and it without quotes
            ('a=a #b=b #c d e# f=f# g="g"#',
             [('a', '=', '', '', 'a'), ('d', '', '', '', ''),
              ('f', '=', '', '', 'f#'), ('g', '=', '"', 'g', ''),],),
        ]

        for pattern, results in checkers:
            self.assertEqual(REATTRS.findall(pattern), results)

    def test_SUPER(self):
        self.assertNotEqual(SUPER, '{super}')
        self.assertEqual(str(SUPER), '{super}')

    def test_parse_plain(self):
        plain = """
        description = value attr=value
        description =+ "v a l u e" :separator=' | ' lang=ru
        description += "v a l u e" lang=en

        keywords =+ "e, f, g, h"

        generator = {super}
        generator = "Generator 1.0"

        @invalid#values$are%ignored&

        og = {super}
        og:a:b:c = 1
        og:i = http://url.com/1.png
        og:i:h = 10
        og:i:w = 10
        og:i = http://url.com/2.png
        og:i:h = 10
        og:i:w = 10
        og:x:y:z = 2
        """

        parsed = {
            'description': [
                [['description'],
                 ('description', '=', '', '', 'value'),
                 ('attr', '=', '', '', 'value')],
                [['description'],
                 ('description', '=+', '"', 'v a l u e', ''),
                 (':separator', '=', "'", ' | ', ''),
                 ('lang', '=', '', '', 'ru')],
                [['description'],
                 ('description', '+=', '"', 'v a l u e', ''),
                 ('lang', '=', '', '', 'en')],
            ],
            'generator': [
                [['generator'], ('generator', '=', '', '', '{super}')],
                [['generator'], ('generator', '=', '"', 'Generator 1.0', '')],
            ],
            'keywords': [
                [['keywords'], ('keywords', '=+', '"', 'e, f, g, h', '')],
            ],
            'og': [
                [['og'], ('og', '=', '', '', '{super}')],
                [['og', 'a', 'b', 'c'], ('og:a:b:c', '=', '', '', '1')],
                [['og', 'i'], ('og:i', '=', '', '', 'http://url.com/1.png')],
                [['og', 'i', 'h'], ('og:i:h', '=', '', '', '10')],
                [['og', 'i', 'w'], ('og:i:w', '=', '', '', '10')],
                [['og', 'i'], ('og:i', '=', '', '', 'http://url.com/2.png')],
                [['og', 'i', 'h'], ('og:i:h', '=', '', '', '10')],
                [['og', 'i', 'w'], ('og:i:w', '=', '', '', '10')],
                [['og', 'x', 'y', 'z'], ('og:x:y:z', '=', '', '', '2')]
            ],
        }

        self.assertEqual(parse_plain(plain), parsed)

    def test_import_path(self):
        self.assertEqual(import_path('unittest.TestCase'), unittest.TestCase)
        self.assertEqual(import_path('unittest.invalid_value'), None)
        self.assertEqual(import_path('unittest.invalid_value', 'alt'), 'alt')
        self.assertEqual(import_path('invalid_module.value'), None)

    def test_exceptions(self):
        e1 = MetaTagValueError('Message')
        e2 = MetaTagValueError('Message', 'tagname')

        self.assertEqual(str(e1), 'Message')
        self.assertEqual(str(e2), 'Tagname: Message')


class RegistryTest(unittest.TestCase):
    def test_register_tag(self):
        registry.register_tag('ncsmt', NameContentStringMetaTag)
        registry.register_tag('ncsmtfromstring', 'NameContentStringMetaTag')

        self.assertTrue(registry.get_tag('ncsmt'), NameContentStringMetaTag)
        self.assertTrue(registry.get_tag('ncsmtfromstring'), NameContentStringMetaTag)

        # already exists
        self.assertRaises(MetaTagRegistryError, registry.register_tag, 'keywords', NameContentCommaSpaceSeparatedValueMetaTag)
        # invalid path to import
        self.assertRaises(MetaTagRegistryError, registry.register_tag, 'tagname', 'invalid.path.to.MetaTagClass')
        # invalid tag class value
        self.assertRaises(MetaTagRegistryError, registry.register_tag, 'tagname', dict)

    def test_get_tag(self):
        self.assertRaises(MetaTagRegistryError, registry.get_tag, 'invalid_tag_name')

    def test_get_and_set_options(self):
        self.assertEqual(registry.get_option('show_empty_tags'), True)
        self.assertEqual(registry.get_option('show_backslash'), False)
        self.assertEqual(registry.get_option('invalid_value'), None)
        self.assertEqual(registry.get_option('invalid_value', default=True), True)

        registry.set_option('new_value', 'new-value')
        self.assertEqual(registry.get_option('new_value'), 'new-value')


class MetaTagsContainerTest(unittest.TestCase):
    def test_init(self):
        mt = MetaTags('keywords = a,b\ndescription=d')
        self.assertEqual(list(mt.data.keys()), ['keywords', 'description',])

        self.assertEqual(MetaTags().action, 'add')
        self.assertEqual(MetaTags(action='unset').action, 'unset')
        self.assertEqual(MetaTags(action='invalid').action, 'add')

        self.assertEqual(MetaTags(MetaTags('description=d')).action, 'add')
        self.assertEqual(MetaTags(NameContentStringMetaTag('description', 'd')).action, 'add')
        self.assertEqual(MetaTags({'description': 'd'}).action, 'add')

        self.assertEqual(MetaTags(MetaTags(action='set')).action, 'set')
        self.assertEqual(MetaTags({':action': 'set'}).action, 'set')
        self.assertEqual(MetaTags({':action': 'tes'}).action, 'add')
        self.assertEqual(MetaTags({':action': 'set'}, action='non-empty-invalid').action, 'add')

    def test_eq(self):
        self.assertEqual(MetaTags('keywords = k', action='set'), MetaTags('keywords = k', action='set'))
        self.assertNotEqual(MetaTags('keywords = k', action='set'), MetaTags('keywords = v', action='set'))
        self.assertNotEqual(MetaTags('keywords = k', action='add'), MetaTags('keywords = k', action='set'))

    def test_as_plain(self):
        mt = MetaTags('keywords = a,b\ndescription=d')
        self.assertEqual(mt.as_plain(), 'description = "d"\nkeywords = "a, b"')
        self.assertEqual((mt + 'keywords = None').as_plain(), 'description = "d"\nkeywords = None')

    def test_as_html(self):
        mt = MetaTags('keywords = a,b\ndescription=d')
        self.assertEqual(str(mt), mt.as_html())
        self.assertEqual(str(mt), '<meta name="description" content="d">\n<meta name="keywords" content="a, b">')
        self.assertEqual(str(mt + 'keywords = None'), '<meta name="description" content="d">')

    def test_prepare_action(self):
        mt = MetaTags()

        self.assertEqual(mt.prepare_action(None), 'add')
        self.assertEqual(mt.prepare_action('add'), 'add')
        self.assertEqual(mt.prepare_action('invalid'), 'add')
        self.assertEqual(mt.prepare_action('set'), 'set')

    def test_copy(self):
        mt = MetaTags(data='keywords = k', action='set')

        self.assertNotEqual(id(mt), id(mt.copy()))
        self.assertEqual(str(mt), str(mt.copy()))
        self.assertEqual(mt.action, mt.copy().action)
        self.assertEqual(mt.data, mt.copy().data)

    def test_set(self):
        mt = MetaTags(data='keywords = k', action='set')

        self.assertEqual(mt.data, {'keywords': NameContentCommaSpaceSeparatedValueMetaTag('keywords', 'k', action='set'),})
        self.assertEqual(mt.action, 'set')

        mt.set('description =+ d')

        self.assertEqual(mt.data, {'description': NameContentStringMetaTag('description', 'd', action='add'),})
        self.assertEqual(mt.action, 'set')

    def test_add_iadd_radd(self):
        mt = MetaTags('keywords =+ b')
        mt2 = mt.copy()

        # kwarg append testing
        self.assertEqual(mt + 'keywords =+ c', MetaTags('keywords =+ b,c'))
        self.assertEqual('keywords =+ a' + mt, MetaTags('keywords =+ a,b'))

        self.assertEqual(mt + 'keywords =+ c', mt.add('keywords =+ c', append=True, inplace=False))
        self.assertEqual('keywords =+ a' + mt, mt.add('keywords =+ a', append=False, inplace=False))

        # kwarg inplace testing
        self.assertNotEqual(id(mt2), id(mt2 + 'keywords += c'))
        self.assertNotEqual(id(mt2), id('keywords += a' + mt2))
        self.assertEqual(id(mt2), id(mt2.__iadd__('keywords += c')))

        self.assertNotEqual(id(mt2), id(mt2.add('keywords += c', append=True, inplace=False)))
        self.assertNotEqual(id(mt2), id(mt2.add('keywords += a', append=False, inplace=False)))
        self.assertEqual(id(mt2), id(mt2.add('keywords += c', append=True, inplace=True)))

        # action value testing
        self.assertEqual(mt + {':action': 'unset'}, MetaTags())
        self.assertEqual(mt + {'keywords': 'a', ':action': 'set'}, MetaTags('keywords =+ a'))
        self.assertEqual(mt + {'keywords': {VALUE: 'c', ':action': 'add'}, ':action': 'add'}, MetaTags('keywords =+ b,c'))
        self.assertEqual(mt + {'keywords': {VALUE: 'a', ':action': 'addleft'}, ':action': 'addleft'}, MetaTags('keywords += a,b'))

        # adding not existed tags testing
        self.assertEqual(mt + {'description': 'd', 'og': {'key': 'value'}},
                         MetaTags('keywords =+ b\ndescription =+ d\nog = {super}\nog:key = value'))

        # empty and unsupported values addition
        self.assertEqual(mt + '', mt)
        self.assertEqual(mt + [], mt)
        self.assertEqual(mt + {}, mt)
        self.assertEqual(mt + None, mt)

    def test_compile(self):
        mt = MetaTags()
        self.assertEqual(tuple(mt.compile('').keys()), ())
        self.assertEqual(tuple(mt.compile('keywords = k').keys()), ('keywords',))
        self.assertEqual(tuple(mt.compile('keywords = k\ndescription = d').keys()), ('keywords', 'description',))

    def test_get_tags_from_data(self):
        mt = MetaTags()

        tags1, action1 = mt.get_tags_from_data('description = d')
        tags2, action2 = mt.get_tags_from_data(NameContentStringMetaTag(name='description', data='d'))
        tags3, action3 = mt.get_tags_from_data(MetaTags(data=tags1.values(), action='set'))
        tags4, action4 = mt.get_tags_from_data({'description': 'd', ':action': 'set'})
        tags5, action5 = mt.get_tags_from_data([NameContentStringMetaTag(name='description', data='d'),])
        tags6, action6 = mt.get_tags_from_data(None)  # any other value

        self.assertEqual(tuple(tags1.keys()), ('description',))
        self.assertEqual(tuple(tags2.keys()), ('description',))
        self.assertEqual(tuple(tags3.keys()), ('description',))
        self.assertEqual(tuple(tags4.keys()), ('description',))
        self.assertEqual(tuple(tags5.keys()), ('description',))
        self.assertEqual(tuple(tags6.keys()), ())

        self.assertEqual(tags1, {'description': NameContentStringMetaTag('description', 'd', action='set'),})
        self.assertEqual(tags2, {'description': NameContentStringMetaTag('description', 'd', action='add'),})
        self.assertEqual(tags3, {'description': NameContentStringMetaTag('description', 'd', action='set'),})
        self.assertEqual(tags4, {'description': NameContentStringMetaTag('description', 'd', action='add'),})
        self.assertEqual(tags5, {'description': NameContentStringMetaTag('description', 'd', action='add'),})
        self.assertEqual(tags6, {})

        self.assertEqual(action1, 'add')
        self.assertEqual(action2, 'add')
        self.assertEqual(action3, 'set')
        self.assertEqual(action4, 'set')
        self.assertEqual(action5, 'add')
        self.assertEqual(action6, 'add')

    def test_get_tags_from_dict(self):
        mt = MetaTags()

        self.assertEqual(mt.get_tags_from_dict({':action': 'set',})[1], 'set')
        self.assertEqual(mt.get_tags_from_dict({':action': 'tes',})[1], 'add')
        self.assertEqual(mt.get_tags_from_dict({':action': None,})[1], 'add')
        self.assertEqual(mt.get_tags_from_dict({})[1], 'add')

        tags, _ = mt.get_tags_from_dict({'description': 'd', 'keywords': 'k',})
        self.assertEqual(tags, {
            'description': NameContentStringMetaTag('description', 'd'),
            'keywords': NameContentCommaSpaceSeparatedValueMetaTag('keywords', 'k'),
        })

        tags1, _ = mt.get_tags_from_dict({'keywords': {'value': 'k', ':action': 'set',},})
        tags2, _ = mt.get_tags_from_dict({'keywords': {'value': 'k', ':action': 'invalid',},})
        tags3, _ = mt.get_tags_from_dict({'keywords': {'value': 'k',},})
        self.assertEqual(tags1['keywords'].action, 'set')
        self.assertEqual(tags2['keywords'].action, 'add')
        self.assertEqual(tags3['keywords'].action, 'add')

        self.assertRaises(MetaTagRegistryError,
                          mt.get_tags_from_dict, {'invalidtag': 'd',})


class BaseMetaTagTest(unittest.TestCase):
    def test_tag_init(self):
        cls = NameContentStringMetaTag

        # None value and unset action testing
        self.assertEqual(cls('description', action='unset').data, None)
        self.assertEqual(cls('description', None, action='unset').data, None)
        self.assertEqual(cls('description', 'd').action, 'add')
        self.assertRaises(MetaTagValueError, cls, 'description')
        self.assertRaises(MetaTagValueError, cls, 'description', None)
        self.assertRaises(MetaTagValueError, cls, 'description', None, action='set')
        self.assertRaises(MetaTagValueError, cls, 'description', 'non-none', action='unset')

    def test_prepare_action(self):
        tag = NameContentStringMetaTag(action='unset')

        self.assertEqual(tag.prepare_action(None), 'add')
        self.assertEqual(tag.prepare_action('add'), 'add')
        self.assertEqual(tag.prepare_action('invalid'), 'add')
        self.assertEqual(tag.prepare_action('set'), 'set')

    def test_copy(self):
        tag = NameContentStringMetaTag('keywords', 'k', action='set')

        self.assertNotEqual(id(tag), id(tag.copy()))
        self.assertEqual(str(tag), str(tag.copy()))
        self.assertEqual(tag.name, tag.copy().name)
        self.assertEqual(tag.action, tag.copy().action)
        self.assertEqual(tag.data, tag.copy().data)

    def test_eq(self):
        cls = NameContentStringMetaTag

        self.assertEqual(cls('keywords', 'k'), cls('keywords','k'))
        self.assertNotEqual(cls('nonkeywords', 'k'), cls('keywords', 'k'))
        self.assertNotEqual(cls('keywords', 'k'), cls('keywords', 'nonk'))
        self.assertNotEqual(cls('keywords', 'k'), cls('keywords', 'k', action='set'))


class StringMetaTagTest(unittest.TestCase):
    def test_tag_init(self):
        tag1 = NameContentStringMetaTag('description', 'd1')
        tag2 = NameContentStringMetaTag('description', action='unset')

        self.assertEqual(tag1.name, 'description')
        self.assertEqual(tag1.data, {VALUE: 'd1'})
        self.assertEqual(tag1.action, 'add')  # action by default
        self.assertEqual(tag2.data, None)  # value by default (only with unset)
        self.assertEqual(tag2.action, 'unset')

    def test_tag_to_python(self):
        tag1 = NameContentStringMetaTag('description', 'd')
        self.assertEqual(tag1.to_python(None), None)
        self.assertEqual(tag1.to_python('d'), {VALUE: 'd'})
        self.assertEqual(tag1.to_python({VALUE: 1,}), {VALUE: '1'})
        self.assertEqual(tag1.to_python({VALUE: None}), {VALUE: 'None'})
        self.assertEqual(tag1.to_python({VALUE: [1,2],}), {VALUE: '[1, 2]'})
        self.assertEqual(tag1.to_python({'a': 1}), {VALUE: '', 'a': '1'})
        self.assertEqual(tag1.to_python({VALUE: 'd'}), {VALUE: 'd'})
        self.assertEqual(tag1.to_python({VALUE: 'd', ':separator': ' | '}), {VALUE: 'd', ':separator': ' | '})
        # any non None value
        self.assertEqual(tag1.to_python(0), {VALUE: '0'})
        self.assertEqual(tag1.to_python(''), {VALUE: ''})

    def test_tag_to_plain(self):
        tag1 = NameContentStringMetaTag('description', 'text')

        self.assertEqual(tag1.to_plain(None), 'description = None')
        self.assertEqual(tag1.to_plain(None, sign='+='), 'description = None')
        self.assertEqual(tag1.to_plain({VALUE: None}), 'description = "None"')
        self.assertEqual(tag1.to_plain({VALUE: 'text'}), 'description = "text"')
        self.assertEqual(tag1.to_plain({VALUE: 'text', 'b': 'b', 'a': 'a'}), 'description = "text" a="a" b="b"')
        self.assertEqual(tag1.to_plain({VALUE: 'text', 'a': 'a', ':b': 'b'}), 'description = "text" :b="b" a="a"')
        self.assertEqual(tag1.to_plain({VALUE: 'text'}, sign="+="), 'description += "text"')

    def test_tag_to_html(self):
        tag1 = NameContentStringMetaTag('description', 'd')

        self.assertEqual(tag1.to_html(None), '')
        self.assertEqual(tag1.to_html({VALUE: None}), '<meta name="description" content="None">')
        self.assertEqual(tag1.to_html({VALUE: 'text'}), '<meta name="description" content="text">')
        self.assertEqual(tag1.to_html({VALUE: 'text', 'b': 'b', 'a': 'a', ':c': 'c'}), '<meta name="description" content="text" a="a" b="b">')

        self.assertEqual(tag1.to_html({VALUE: ''}), '<meta name="description" content="">')
        registry.set_option('show_empty_tags', False)
        self.assertEqual(tag1.to_html({VALUE: ''}), '')
        registry.set_option('show_empty_tags', True)

        registry.set_option('show_backslash', True)
        self.assertEqual(tag1.to_html({VALUE: 'text',}), '<meta name="description" content="text" />')
        registry.set_option('show_backslash', False)

    def test_tag_as_plain(self):
        tag1 = NameContentStringMetaTag('description', 'text')
        tag2 = NameContentStringMetaTag('description', {VALUE: 'text', ':separator': ' | ', 'a': 'a'})
        tag3 = NameContentStringMetaTag('description', {VALUE: 'text',}, action='add')
        tag4 = NameContentStringMetaTag('description', {VALUE: 'text',}, action='addleft')
        tag5 = NameContentStringMetaTag('description', {VALUE: 'text',}, action='set')
        tag6 = NameContentStringMetaTag('description', action='unset')

        self.assertEqual(tag1.as_plain(), 'description =+ "text"')
        self.assertEqual(tag2.as_plain(), 'description =+ "text" :separator=" | " a="a"')
        self.assertEqual(tag3.as_plain(), 'description =+ "text"')
        self.assertEqual(tag4.as_plain(), 'description += "text"')
        self.assertEqual(tag5.as_plain(), 'description = "text"')
        self.assertEqual(tag6.as_plain(), 'description = None')

    def test_tag_as_html(self):
        tag1 = NameContentStringMetaTag('description', 'd')
        tag2 = NameContentStringMetaTag('description', action='unset')

        self.assertEqual(str(tag1), tag1.as_html())
        self.assertEqual(str(tag1), '<meta name="description" content="d">')
        self.assertEqual(str(tag2), '')

    def test_tag_add(self):
        cls = NameContentStringMetaTag

        tag1 = cls('description', '1')
        tag2 = cls('description', '2', action='set')
        tag3 = cls('description', None, action='unset')
        tag4 = cls('description', '', action='set')

        # non tag value adding
        self.assertRaises(MetaTagValueError, tag1.__add__, 'NonTagValue')

        # inplace adding kwarg
        inplacetag1 = tag1.copy()
        self.assertNotEqual(id(inplacetag1), id(inplacetag1.add(tag2)))
        self.assertEqual(id(inplacetag1), id(inplacetag1.add(tag2, inplace=True)))

        # set and unset actions
        self.assertEqual(str(tag1), '<meta name="description" content="1">')
        self.assertEqual(str(tag1 + tag2), '<meta name="description" content="2">')
        self.assertEqual(str(tag1 + tag3), '')
        self.assertEqual(str(tag1 + tag4), '<meta name="description" content="">')
        self.assertEqual(str(tag1 + tag2 + tag3), '')
        self.assertEqual(str(tag1 + tag3 + tag2), '<meta name="description" content="2">')

        # add and addleft actions
        tag1 = cls('description', {VALUE: '1', 'a': 'a', 'b': 'b'})
        tag2 = cls('description', {VALUE: '2'}, action='add')
        tag3 = cls('description', {VALUE: '3'}, action='addleft')
        tag4 = cls('description', {VALUE: '4', ':separator': ' | ', 'b': 'B', 'c': 'c'}, action='add')

        self.assertEqual(str(tag1 + tag2), '<meta name="description" content="1 2" a="a" b="b">')
        self.assertEqual(str(tag1 + tag3), '<meta name="description" content="3 1" a="a" b="b">')
        self.assertEqual(str(tag1 + tag4), '<meta name="description" content="1 | 4" a="a" b="B" c="c">')
        self.assertEqual(str(tag1 + tag2 + tag3), '<meta name="description" content="3 1 2" a="a" b="b">')
        self.assertEqual(tag1.data, {VALUE: '1', 'a': 'a', 'b': 'b'})  # tag1 not changed

        # tags addition modifies left tag in expression
        tag1 = cls('description', {VALUE: '1', 'a': 'a', 'b': 'b', ':s': 's'}, action='add')
        tag2 = cls('description', {VALUE: '2', 'c': 'C', 'b': 'B', ':s': 'S'}, action='addleft')
        tag3 = tag1 + tag2
        tag4 = tag1.copy()
        tag4 += tag2

        self.assertEqual(tag1.action, tag3.action)
        self.assertEqual(tag3.data, {'value': '2 1', 'a': 'a', 'b': 'b', 'c': 'C', ':s': 's'})
        self.assertEqual(tag3, tag4)

    def test_tag_compile(self):
        # for parser logic look at test_parse_plain
        cls = NameContentStringMetaTag
        value_only = [[['description'], ('description', '=', '', '', 'value')]]
        value_attr = [[['description'], ('description', '=', '"', '{super}', ''),
                       ('a', '=', '', '', 'a'), (':b', '=', '', '', 'b')]]
        value_upd1 = [[['description'], ('description', '=+', '', '', 'value')]]
        value_upd2 = [[['description'], ('description', '+=', '', '', 'value')]]
        value_none = [[['description'], ('description', '=', '', '', 'None'),
                       ('a', '=', '', '', 'a'), (':b', '=', '', '', 'b')]]
        value_err1 = [[['description'], ('description', '=', '', '', 'value1')],
                      [['description'], ('description', '=', '', '', 'value2')]]
        value_err2 = [[['description'], ('description', '=', '', '', '{super}')]]
        value_err3 = [[['description', 'colon'], ('description:colon', '=', '', '', 'value')]]

        tag = cls.compile('description', value_only)
        self.assertEqual(tag.data, {VALUE: 'value'})
        self.assertEqual(tag.action, 'set')

        tag = cls.compile('description', value_attr)
        self.assertEqual(tag.data, {VALUE: '{super}', 'a': 'a', ':b': 'b'})
        self.assertEqual(tag.action, 'set')

        tag = cls.compile('description', value_upd1)
        self.assertEqual(tag.data, {VALUE: 'value'})
        self.assertEqual(tag.action, 'add')

        tag = cls.compile('description', value_upd2)
        self.assertEqual(tag.data, {VALUE: 'value'})
        self.assertEqual(tag.action, 'addleft')

        tag = cls.compile('description', value_none)
        self.assertEqual(tag.data, None)
        self.assertEqual(tag.action, 'unset')

        # more than one line
        self.assertRaises(MetaTagValueError, cls.compile, 'description', value_err1)
        # {super} value without quotes
        self.assertRaises(MetaTagValueError, cls.compile, 'description', value_err2)
        # colon in tag name
        self.assertRaises(MetaTagValueError, cls.compile, 'description', value_err3)

    def test_tag_from_form(self):
        cls = NameContentStringMetaTag

        value_add = ('description', 'value', 'add')
        value_addleft = ('description', 'value', 'addleft')
        value_set = ('description', 'value', 'set')
        value_unset = ('description', '', 'unset')
        value_empty = ('description', '""', 'set')
        value_attr = ('description', '"v a l u e" attr=value', 'add')
        value_auto_1 = ('description', 'v a l u e', 'add')
        value_auto_2 = ('description', 'v a l = e', 'add')
        value_auto_3 = ('description', '"v a l = e"', 'add')
        value_auto_4 = ('description', '"v a l u e"', 'add')
        value_err1 = ('description', ' {super}  ', 'add')
        value_err11 = ('description', 'None  ', 'add')
        value_err2 = ('description', 'non-empty', 'unset')
        value_err22 = ('description', '', 'set')
        value_err3 = ('description', 'multi\nline', 'set')

        tag = cls.from_form(*value_add)
        self.assertEqual(tag.name, 'description')
        self.assertEqual(tag.data, {VALUE: 'value'})
        self.assertEqual(tag.action, 'add')

        tag1 = cls.from_form(*value_addleft)
        tag2 = cls.from_form(*value_set)
        tag3 = cls.from_form(*value_unset)

        self.assertEqual(tag1.action, 'addleft')
        self.assertEqual(tag2.action, 'set')
        self.assertEqual(tag3.action, 'unset')
        self.assertEqual(tag3.data, None)  # unset action turns all into None

        tag = cls.from_form(*value_empty)
        self.assertEqual(tag.data, {VALUE: ''})

        tag = cls.from_form(*value_attr)
        self.assertEqual(tag.data, {VALUE: 'v a l u e', 'attr': 'value'})

        # if equal sign exists value is processed as is
        tag1 = cls.from_form(*value_auto_1)
        tag2 = cls.from_form(*value_auto_2)
        tag3 = cls.from_form(*value_auto_3)
        tag4 = cls.from_form(*value_auto_4)
        self.assertEqual(tag1.data, {VALUE: 'v a l u e'})
        self.assertEqual(tag2.data, {VALUE: 'v', 'a': '', 'l': 'e'})
        self.assertEqual(tag3.data, {VALUE: 'v a l = e'})
        self.assertEqual(tag4.data, {VALUE: 'v a l u e'})

        # super value should not be used in form-like definition
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err1)
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err11)
        # value should be empty only if action is unset
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err2)
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err22)
        # value contains multiple lines
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err3)


class SeparatedValueMetaTagTest(unittest.TestCase):
    def test_tag_init(self):
        tag1 = NameContentCommaSpaceSeparatedValueMetaTag('keywords', '1,2')
        tag2 = NameContentCommaSpaceSeparatedValueMetaTag('keywords', action='unset')

        self.assertEqual(tag1.name, 'keywords')
        self.assertEqual(tag1.data, {VALUE: ['1', '2']})
        self.assertEqual(tag1.action, 'add')  # action by default
        self.assertEqual(tag2.data, None)  # value by default (only with unset)
        self.assertEqual(tag2.action, 'unset')

    def test_tag_to_python(self):
        tag1 = NameContentCommaSpaceSeparatedValueMetaTag('keywords', 'a, b, c')

        self.assertEqual(tag1.to_python(None), None)
        self.assertEqual(tag1.to_python('a,b, c, 1,  None'), {VALUE: ['a', 'b', 'c', '1', 'None']})
        self.assertEqual(tag1.to_python({VALUE: ['a', 'b']}), {VALUE: ['a', 'b'],})
        self.assertEqual(tag1.to_python({VALUE: ['1', 2, None,]}), {VALUE: ['1', '2', 'None'],})
        self.assertEqual(tag1.to_python({VALUE: None}), {VALUE: ['None']})
        self.assertEqual(tag1.to_python({VALUE: ''}), {VALUE: []})
        self.assertEqual(tag1.to_python({VALUE: []}), {VALUE: []})
        self.assertEqual(tag1.to_python(1), {VALUE: ['1']})
        self.assertEqual(tag1.to_python([1, 2]), {VALUE: ['1', '2']})
        self.assertEqual(tag1.to_python({'a': 'a'}), {VALUE: [], 'a': 'a'})

    def test_tag_as_plain(self):
        cls = NameContentCommaSpaceSeparatedValueMetaTag

        tag1 = cls('keywords', '1,2')
        tag2 = cls('keywords', {VALUE: '1,2', ':a': 'a', 'b': 'b'})
        tag3 = cls('keywords', {VALUE: '1,2',}, action='add')
        tag4 = cls('keywords', {VALUE: '1,2',}, action='addleft')
        tag5 = cls('keywords', {VALUE: '1,2',}, action='set')
        tag6 = cls('keywords', action='unset')

        self.assertEqual(tag1.as_plain(), 'keywords =+ "1, 2"')
        self.assertEqual(tag2.as_plain(), 'keywords =+ "1, 2" :a="a" b="b"')
        self.assertEqual(tag3.as_plain(), 'keywords =+ "1, 2"')
        self.assertEqual(tag4.as_plain(), 'keywords += "1, 2"')
        self.assertEqual(tag5.as_plain(), 'keywords = "1, 2"')
        self.assertEqual(tag6.as_plain(), 'keywords = None')

    def test_tag_as_html(self):
        tag1 = NameContentCommaSpaceSeparatedValueMetaTag('keywords', '1,2,3')
        tag2 = NameContentCommaSpaceSeparatedValueMetaTag('keywords', action='unset')

        self.assertEqual(str(tag1), tag1.as_html())
        self.assertEqual(str(tag1), '<meta name="keywords" content="1, 2, 3">')
        self.assertEqual(str(tag2), '')

    def test_tag_add(self):
        cls = NameContentCommaSpaceSeparatedValueMetaTag

        tag1 = cls('keywords', '1,2')
        tag2 = cls('keywords', '3,4', action='set')
        tag3 = cls('keywords', None, action='unset')
        tag4 = cls('keywords', '', action='set')

        # non tag value adding
        self.assertRaises(MetaTagValueError, tag1.__add__, 'NonTagValue')

        # inplace adding kwarg
        inplacetag1 = tag1.copy()
        self.assertNotEqual(id(inplacetag1), id(inplacetag1.add(tag2)))
        self.assertEqual(id(inplacetag1), id(inplacetag1.add(tag2, inplace=True)))

        # set and unset actions
        self.assertEqual(str(tag1), '<meta name="keywords" content="1, 2">')
        self.assertEqual(str(tag1 + tag2), '<meta name="keywords" content="3, 4">')
        self.assertEqual(str(tag1 + tag3), '')
        self.assertEqual(str(tag1 + tag4), '<meta name="keywords" content="">')
        self.assertEqual(str(tag1 + tag2 + tag3), '')
        self.assertEqual(str(tag1 + tag3 + tag2), '<meta name="keywords" content="3, 4">')

        # add and addleft actions
        tag1 = cls('description', {VALUE: '1,2', 'a': 'a', 'b': 'b'})
        tag2 = cls('description', {VALUE: '3,4'}, action='add')
        tag3 = cls('description', {VALUE: '5,6'}, action='addleft')
        tag4 = cls('description', {VALUE: '7,8', ':separator': ' | ', 'b': 'B', 'c': 'c'}, action='add')

        self.assertEqual(str(tag1 + tag2), '<meta name="description" content="1, 2, 3, 4" a="a" b="b">')
        self.assertEqual(str(tag1 + tag3), '<meta name="description" content="5, 6, 1, 2" a="a" b="b">')
        self.assertEqual(str(tag1 + tag4), '<meta name="description" content="1, 2, 7, 8" a="a" b="B" c="c">')
        self.assertEqual(str(tag1 + tag2 + tag3), '<meta name="description" content="5, 6, 1, 2, 3, 4" a="a" b="b">')
        self.assertEqual(tag1.data, {VALUE: ['1', '2',], 'a': 'a', 'b': 'b'})  # tag1 not changed

        # tags addition modifies left tag in expression
        tag1 = cls('keywords', {VALUE: '1,2', 'a': 'a', 'b': 'b', ':s': 's'}, action='add')
        tag2 = cls('keywords', {VALUE: '3,4', 'c': 'C', 'b': 'B', ':s': 'S'}, action='addleft')
        tag3 = tag1 + tag2
        tag4 = tag1.copy()
        tag4 += tag2

        self.assertEqual(tag1.action, tag3.action)
        self.assertEqual(tag3.data, {'value': ['3','4','1','2'], 'a': 'a', 'b': 'b', 'c': 'C', ':s': 's'})
        self.assertEqual(tag3, tag4)

    def test_tag_compile(self):
        # for parser logic look at test_parse_plain
        cls = NameContentCommaSpaceSeparatedValueMetaTag
        value_only = [[['keywords'], ('keywords', '=', '', '', '1,2')]]
        value_attr = [[['keywords'], ('keywords', '=', '"', '{super}', ''),
                       ('a', '=', '', '', 'a'), (':b', '=', '', '', 'b')]]
        value_upd1 = [[['keywords'], ('keywords', '=+', '', '', '1,2')]]
        value_upd2 = [[['keywords'], ('keywords', '+=', '', '', '1,2')]]
        value_none = [[['keywords'], ('keywords', '=', '', '', 'None'),
                       ('a', '=', '', '', 'a'), (':b', '=', '', '', 'b')]]
        value_err1 = [[['keywords'], ('keywords', '=', '', '', '1,2')],
                      [['keywords'], ('keywords', '=', '', '', '1,2')]]
        value_err2 = [[['keywords'], ('keywords', '=', '', '', '{super}')]]
        value_err3 = [[['keywords', 'colon'], ('keywords:colon', '=', '', '', '1,2')]]

        tag = cls.compile('keywords', value_only)
        self.assertEqual(tag.data, {VALUE: ['1', '2']})
        self.assertEqual(tag.action, 'set')

        tag = cls.compile('keywords', value_attr)
        self.assertEqual(tag.data, {VALUE: ['{super}'], 'a': 'a', ':b': 'b'})
        self.assertEqual(tag.action, 'set')

        tag = cls.compile('keywords', value_upd1)
        self.assertEqual(tag.data, {VALUE: ['1','2']})
        self.assertEqual(tag.action, 'add')

        tag = cls.compile('keywords', value_upd2)
        self.assertEqual(tag.data, {VALUE: ['1','2']})
        self.assertEqual(tag.action, 'addleft')

        tag = cls.compile('keywords', value_none)
        self.assertEqual(tag.data, None)
        self.assertEqual(tag.action, 'unset')

        # more than one line
        self.assertRaises(MetaTagValueError, cls.compile, 'keywords', value_err1)
        # {super} value without quotes
        self.assertRaises(MetaTagValueError, cls.compile, 'keywords', value_err2)
        # colon in tag name
        self.assertRaises(MetaTagValueError, cls.compile, 'description', value_err3)


class ListMetaTagTest(unittest.TestCase):
    def test_tag_init(self):
        tag1 = NameContentListMetaTag('generator', [1, 2])
        tag2 = NameContentListMetaTag('generator', action='unset')

        self.assertEqual(tag1.name, 'generator')
        self.assertEqual(tag1.data, [{VALUE: '1'}, {VALUE: '2'}])
        self.assertEqual(tag1.action, 'add')  # action by default
        self.assertEqual(tag2.data, None)  # value by default (only with unset)
        self.assertEqual(tag2.action, 'unset')

    def test_tag_to_python(self):
        tag1 = NameContentListMetaTag('generator', 'g')

        self.assertEqual(tag1.to_python(None), None)
        self.assertEqual(tag1.to_python('text'), [{VALUE: 'text'}])
        self.assertEqual(tag1.to_python(1), [{VALUE: '1'}])
        self.assertEqual(tag1.to_python([1, '2', True,]), [{VALUE: '1'}, {VALUE: '2'}, {VALUE: 'True'}])
        self.assertEqual(tag1.to_python({VALUE: None}), [{VALUE: 'None'}])
        self.assertEqual(tag1.to_python({'a': 'a'}), [{VALUE: '', 'a': 'a'}])
        self.assertEqual(tag1.to_python([{'a': 1}]), [{VALUE: '', 'a': '1'}])

    def test_tag_to_plain(self):
        tag1 = NameContentListMetaTag('generator', 'g')

        self.assertEqual(tag1.to_plain(None), 'generator = None')
        self.assertEqual(tag1.to_plain({VALUE: None}), 'generator = "None"')
        self.assertEqual(tag1.to_plain({VALUE: 'text'}), 'generator = "text"')
        self.assertEqual(tag1.to_plain({VALUE: 'text', 'b': 'b', 'a': 'a'}), 'generator = "text" a="a" b="b"')
        self.assertEqual(tag1.to_plain({VALUE: 'text', 'a': 'a', ':b': 'b'}), 'generator = "text" :b="b" a="a"')

    def test_tag_to_html(self):
        tag1 = NameContentListMetaTag('generator', 'g')

        self.assertEqual(tag1.to_html(None), '')
        self.assertEqual(tag1.to_html({VALUE: None}), '<meta name="generator" content="None">')
        self.assertEqual(tag1.to_html({VALUE: 'text'}), '<meta name="generator" content="text">')
        self.assertEqual(tag1.to_html({VALUE: 'text', 'b': 'b', 'a': 'a', ':c': 'c'}), '<meta name="generator" content="text" a="a" b="b">')

        self.assertEqual(tag1.to_html({VALUE: ''}), '<meta name="generator" content="">')
        registry.set_option('show_empty_tags', False)
        self.assertEqual(tag1.to_html({VALUE: ''}), '')
        registry.set_option('show_empty_tags', True)

        registry.set_option('show_backslash', True)
        self.assertEqual(tag1.to_html({VALUE: 'text',}), '<meta name="generator" content="text" />')
        registry.set_option('show_backslash', False)

    def test_tag_as_plain(self):
        cls = NameContentListMetaTag

        tag1 = cls('generator', 'text')
        tag2 = cls('generator', {VALUE: 'text', ':a': 'a', 'b': 'b'})
        tag3 = cls('generator', 'text', action='add')
        tag4 = cls('generator', 'text', action='addleft')
        tag5 = cls('generator', 'text', action='set')
        tag6 = cls('generator', ['text1', 'text2',], action='set')
        tag7 = cls('generator', action='unset')

        self.assertEqual(tag1.as_plain(), 'generator = {super}\ngenerator = "text"')
        self.assertEqual(tag2.as_plain(), 'generator = {super}\ngenerator = "text" :a="a" b="b"')
        self.assertEqual(tag3.as_plain(), 'generator = {super}\ngenerator = "text"')
        self.assertEqual(tag4.as_plain(), 'generator = "text"\ngenerator = {super}')
        self.assertEqual(tag5.as_plain(), 'generator = "text"')
        self.assertEqual(tag6.as_plain(), 'generator = "text1"\ngenerator = "text2"')
        self.assertEqual(tag7.as_plain(), 'generator = None')

    def test_tag_as_html(self):
        tag1 = NameContentListMetaTag('generator', ['text1','text2'])
        tag2 = NameContentListMetaTag('generator', action='unset')

        self.assertEqual(str(tag1), tag1.as_html())
        self.assertEqual(str(tag1), '<meta name="generator" content="text1">\n<meta name="generator" content="text2">')
        self.assertEqual(str(tag2), '')

    def test_tag_add(self):
        cls = NameContentListMetaTag

        tag1 = cls('generator', '1')
        tag2 = cls('generator', '2', action='set')
        tag3 = cls('generator', None, action='unset')
        tag4 = cls('generator', '', action='set')

        # non tag value adding
        self.assertRaises(MetaTagValueError, tag1.__add__, 'NonTagValue')

        # inplace adding kwarg
        inplacetag1 = tag1.copy()
        self.assertNotEqual(id(inplacetag1), id(inplacetag1.add(tag2)))
        self.assertEqual(id(inplacetag1), id(inplacetag1.add(tag2, inplace=True)))

        # set and unset actions
        self.assertEqual(str(tag1), '<meta name="generator" content="1">')
        self.assertEqual(str(tag1 + tag2), '<meta name="generator" content="2">')
        self.assertEqual(str(tag1 + tag3), '')
        self.assertEqual(str(tag1 + tag4), '<meta name="generator" content="">')
        self.assertEqual(str(tag1 + tag2 + tag3), '')
        self.assertEqual(str(tag1 + tag3 + tag2), '<meta name="generator" content="2">')

        # add and addleft actions
        tag1 = cls('generator', {VALUE: '1', 'a': 'a',})
        tag2 = cls('generator', {VALUE: '2'}, action='add')
        tag3 = cls('generator', {VALUE: '3'}, action='addleft')
        tag4 = cls('generator', {VALUE: '4', ':b': 'b', 'a': 'A',}, action='add')

        self.assertEqual(str(tag1 + tag2), '<meta name="generator" content="1" a="a">\n<meta name="generator" content="2">')
        self.assertEqual(str(tag1 + tag3), '<meta name="generator" content="3">\n<meta name="generator" content="1" a="a">')
        self.assertEqual(str(tag1 + tag4), '<meta name="generator" content="1" a="a">\n<meta name="generator" content="4" a="A">')
        self.assertEqual(str(tag1 + tag2 + tag3), '<meta name="generator" content="3">\n<meta name="generator" content="1" a="a">\n<meta name="generator" content="2">')
        self.assertEqual(tag1.data, [{VALUE: '1', 'a': 'a',}])

        # tags addition modifies left tag in expression
        tag1 = cls('generator', {VALUE: '1', 'a': 'a',}, action='add')
        tag2 = cls('generator', {VALUE: '2', 'a': 'A',}, action='addleft')
        tag3 = tag1 + tag2
        tag4 = tag1.copy()
        tag4 += tag2

        self.assertEqual(tag1.action, tag3.action)
        self.assertEqual(tag3.data, [{VALUE: '2', 'a': 'A',}, {VALUE: '1', 'a': 'a',}])
        self.assertEqual(tag3, tag4)

    def test_tag_compile(self):
        # for parser logic look at test_parse_plain
        cls = NameContentListMetaTag
        value_only = [[['generator'], ('generator', '=', '', '', 'value')]]
        value_attr = [[['generator'], ('generator', '=', '"', '{super}', ''),
                       ('a', '=', '', '', 'a'), (':b', '=', '', '', 'b')]]
        value_upd1 = [[['generator'], ('generator', '=', '', '', '{super}')],
                      [['generator'], ('generator', '=', '', '', 'value')]]
        value_upd2 = [[['generator'], ('generator', '=', '', '', 'value')],
                      [['generator'], ('generator', '=', '', '', '{super}')]]
        value_none = [[['generator'], ('generator', '=', '', '', 'None'),
                       ('a', '=', '', '', 'a'), (':b', '=', '', '', 'b')]]
        value_spr1 = [[['generator'], ('generator', '=', '', '', '{super}')]]
        value_err1 = [[['generator', 'colon'], ('generator:colon', '=', '', '', 'value')]]
        value_err2 = [[['generator'], ('generator', '=', '', '', '{super}')],
                      [['generator'], ('generator', '=', '', '', '{super}')]]
        value_err3 = [[['generator'], ('generator', '=', '', '', 'None')],
                      [['generator'], ('generator', '=', '', '', 'second')]]

        tag = cls.compile('generator', value_only)
        self.assertEqual(tag.data, [{VALUE: 'value'}])
        self.assertEqual(tag.action, 'set')

        tag = cls.compile('generator', value_attr)
        self.assertEqual(tag.data, [{VALUE: '{super}', 'a': 'a', ':b': 'b'}])
        self.assertEqual(tag.action, 'set')

        tag = cls.compile('generator', value_upd1)
        self.assertEqual(tag.data, [{VALUE: 'value'}])
        self.assertEqual(tag.action, 'add')

        tag = cls.compile('generator', value_upd2)
        self.assertEqual(tag.data, [{VALUE: 'value'}])
        self.assertEqual(tag.action, 'addleft')

        tag = cls.compile('generator', value_none)
        self.assertEqual(tag.data, None)
        self.assertEqual(tag.action, 'unset')

        tag = cls.compile('generator', value_spr1)
        self.assertEqual(tag.data, [])
        self.assertEqual(tag.action, 'add')

        # colon in tag name
        self.assertRaises(MetaTagValueError, cls.compile, 'generator', value_err1)
        # more than one {super} values
        self.assertRaises(MetaTagValueError, cls.compile, 'generator', value_err2)
        # None value exists in non oneline definition
        self.assertRaises(MetaTagValueError, cls.compile, 'generator', value_err3)

    def test_tag_from_form(self):
        cls = NameContentListMetaTag

        value_add = ('generator', 'value', 'add')
        value_addleft = ('generator', 'value', 'addleft')
        value_set = ('generator', 'value', 'set')
        value_unset = ('generator', '', 'unset')
        value_empty = ('generator', '""', 'set')
        value_attr = ('generator', '"v a l u e" attr=value', 'add')
        value_auto_1 = ('description', 'v a l u e', 'add')
        value_auto_2 = ('description', 'v a l = e', 'add')
        value_auto_3 = ('description', '"v a l = e"', 'add')
        value_multi = ('generator', '  value1\n\n   value2 ', 'add')
        value_err1 = ('generator', ' {super} ', 'add')
        value_err11 = ('generator', ' None\n1', 'add')
        value_err2 = ('generator', 'non-empty', 'unset')
        value_err22 = ('description', '  ', 'set')

        tag = cls.from_form(*value_add)
        self.assertEqual(tag.name, 'generator')
        self.assertEqual(tag.data, [{VALUE: 'value'}])
        self.assertEqual(tag.action, 'add')

        tag1 = cls.from_form(*value_addleft)
        tag2 = cls.from_form(*value_set)
        tag3 = cls.from_form(*value_unset)

        self.assertEqual(tag1.action, 'addleft')
        self.assertEqual(tag2.action, 'set')
        self.assertEqual(tag3.action, 'unset')
        self.assertEqual(tag3.data, None)

        # if equal sign exists value is processed as is
        tag1 = cls.from_form(*value_auto_1)
        tag2 = cls.from_form(*value_auto_2)
        tag3 = cls.from_form(*value_auto_3)
        self.assertEqual(tag1.data, [{VALUE: 'v a l u e'}])
        self.assertEqual(tag2.data, [{VALUE: 'v', 'a': '', 'l': 'e'}])
        self.assertEqual(tag3.data, [{VALUE: 'v a l = e'}])

        tag = cls.from_form(*value_empty)
        self.assertEqual(tag.data, [{VALUE: ''}])

        tag = cls.from_form(*value_attr)
        self.assertEqual(tag.data, [{VALUE: 'v a l u e', 'attr': 'value'}])

        tag = cls.from_form(*value_multi)
        self.assertEqual(tag.data, [{VALUE: 'value1'}, {VALUE: 'value2'}])

        # {super}/None values should not be used in form-like definition
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err1)
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err11)
        # value should be empty only if action is unset
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err2)
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err22)


class DictMetaTagTest(unittest.TestCase):
    def test_tag_init(self):
        tag1 = NameContentDictMetaTag('og', {'o': 'g'})
        tag2 = NameContentDictMetaTag('og', action='unset')

        self.assertEqual(tag1.name, 'og')
        self.assertEqual(tag1.data, {'o': 'g'})
        self.assertEqual(tag1.action, 'add')  # action by default
        self.assertEqual(tag2.data, None)  # value by default (only with unset)
        self.assertEqual(tag2.action, 'unset')

    def test_tag_to_python(self):
        cls = NameContentDictMetaTag
        tag1 = cls('og', {'o': 'g'})

        self.assertEqual(tag1.to_python(None), None)
        self.assertEqual(tag1.to_python({VALUE: None, 'a': 1}), {VALUE: 'None', 'a': '1'})
        self.assertEqual(tag1.to_python({'a': 'a'}), {'a': 'a'})
        self.assertEqual(tag1.to_python({'a': {'b': 1, 'c': [1, None, '']}}), {'a': {'b': '1', 'c': ['1', 'None', '']}})
        self.assertRaises(MetaTagValueError, cls, 'og', 'non-dict-value')

    def test_tag_to_plain(self):
        tag1 = NameContentDictMetaTag('og', {'o': 'g'})

        self.assertEqual(tag1.to_plain(None), 'og = None')
        self.assertEqual(tag1.to_plain('str'), 'og = "str"')
        self.assertEqual(tag1.to_plain('str', name='og:attr'), 'og:attr = "str"')
        self.assertEqual(tag1.to_plain(1, name='og:int'), 'og:int = "1"')

    def test_tag_to_html(self):
        tag1 = NameContentDictMetaTag('og', {'o': 'g'})

        self.assertEqual(tag1.to_html(None), '')
        self.assertEqual(tag1.to_html('str'), '<meta name="og" content="str">')
        self.assertEqual(tag1.to_html('str', name='og:str'), '<meta name="og:str" content="str">')
        self.assertEqual(tag1.to_html(1, 'og:int'), '<meta name="og:int" content="1">')

        self.assertEqual(tag1.to_html('', name='og:a'), '<meta name="og:a" content="">')
        registry.set_option('show_empty_tags', False)
        self.assertEqual(tag1.to_html('', name='og:a'), '')
        registry.set_option('show_empty_tags', True)

        registry.set_option('show_backslash', True)
        self.assertEqual(tag1.to_html('str', name='og:str'), '<meta name="og:str" content="str" />')
        registry.set_option('show_backslash', False)

    def test_tag_as_plain(self):
        cls = NameContentDictMetaTag

        tag1 = cls('og', {'a': 'a'})
        tag2 = cls('og', {'a': 'a'}, action='addleft')
        tag3 = cls('og', {'a': 1, 'b': None, 'c': [1,2], 'd': (1,2), 'e': {'o': 'g', 'e2': {'oo': ['g', 'g',]}}, 'f': ''}, action='set')  # many types of data

        # elements of list/tuple should not be list/tuple
        tag4 = cls('og', {'a': [0, {VALUE: 1, 'b': 'b'}, [2, 2], (2, 2)]}, action='set')  # lists

        # VALUE should be on 1+ level and be scalar (not dict, list or tuple)
        tag5 = cls('og', {'a': {VALUE: 1}, 'b': {VALUE: {'c': 'c'}, 'c': 'c'}, VALUE: 'v'}, action='set')  # dicts
        tag6 = cls('og', action='unset')

        self.assertEqual(tag1.as_plain(), 'og = {super}\nog:a = "a"')
        self.assertEqual(tag2.as_plain(), 'og:a = "a"\nog = {super}')
        self.assertEqual(tag3.as_plain(), 'og:a = "1"\nog:b = "None"\nog:c = "1"\nog:c = "2"\nog:d = "1"\nog:d = "2"'
                                          '\nog:e:e2:oo = "g"\nog:e:e2:oo = "g"\nog:e:o = "g"\nog:f = ""')
        self.assertEqual(tag4.as_plain(), 'og:a = "0"\nog:a = "1"\nog:a:b = "b"')
        self.assertEqual(tag5.as_plain(), 'og:a = "1"\nog:b:c = "c"')
        self.assertEqual(tag6.as_plain(), 'og = None')

    def test_tag_as_html(self):
        cls = NameContentDictMetaTag

        tag1 = cls('og', {'a': 'a'})
        tag2 = cls('og', {'a': 'a'}, action='addleft')
        tag3 = cls('og', {'a': 1, 'b': None, 'c': [1,2], 'd': (1,2), 'e': {'o': 'g', 'e2': {'oo': ['g', 'g',]}}, 'f': ''}, action='set')  # many types of data

        # elements of list/tuple should not be list/tuple
        tag4 = cls('og', {'a': [0, {VALUE: 1, 'b': 'b'}, [2, 2], (2, 2)]}, action='set')  # lists

        # VALUE should be on 1+ level and be scalar (not dict, list or tuple)
        tag5 = cls('og', {'a': {VALUE: 1}, 'b': {VALUE: {'c': 'c'}, 'c': 'c'}, VALUE: 'v'}, action='set')  # dicts
        tag6 = cls('og', action='unset')

        self.assertEqual(str(tag1), tag1.as_html())
        self.assertEqual(str(tag1), '<meta name="og:a" content="a">')
        self.assertEqual(str(tag2), '<meta name="og:a" content="a">')
        self.assertEqual(str(tag3),
            '<meta name="og:a" content="1">'
            '\n<meta name="og:b" content="None">'
            '\n<meta name="og:c" content="1">'
            '\n<meta name="og:c" content="2">'
            '\n<meta name="og:d" content="1">'
            '\n<meta name="og:d" content="2">'
            '\n<meta name="og:e:e2:oo" content="g">'
            '\n<meta name="og:e:e2:oo" content="g">'
            '\n<meta name="og:e:o" content="g">'
            '\n<meta name="og:f" content="">'
        )
        self.assertEqual(str(tag4),
            '<meta name="og:a" content="0">'
            '\n<meta name="og:a" content="1">'
            '\n<meta name="og:a:b" content="b">'
        )
        self.assertEqual(str(tag5),
            '<meta name="og:a" content="1">'
            '\n<meta name="og:b:c" content="c">'
        )
        self.assertEqual(str(tag6), '')

    def test_tag_add(self):
        cls = NameContentDictMetaTag

        tag1 = cls('og', {'a': 'a'})
        tag2 = cls('og', {'a': 'b'}, action='set')
        tag3 = cls('og', None, action='unset')
        tag4 = cls('og', {}, action='set')

        # non tag value adding
        self.assertRaises(MetaTagValueError, tag1.__add__, 'NonTagValue')

        # inplace adding kwarg
        inplacetag1 = tag1.copy()
        self.assertNotEqual(id(inplacetag1), id(inplacetag1.add(tag2)))
        self.assertEqual(id(inplacetag1), id(inplacetag1.add(tag2, inplace=True)))

        # set and unset actions
        self.assertEqual(str(tag1), '<meta name="og:a" content="a">')
        self.assertEqual(str(tag1 + tag2), '<meta name="og:a" content="b">')
        self.assertEqual(str(tag1 + tag3), '')
        self.assertEqual(str(tag1 + tag4), '')
        self.assertEqual(str(tag1 + tag2 + tag3), '')
        self.assertEqual(str(tag1 + tag3 + tag2), '<meta name="og:a" content="b">')

        # add and addleft actions
        tag1 = cls('og', {'a': '1', 'b': '1'})
        tag2 = cls('og', {'a': '2'}, action='add')
        tag3 = cls('og', {'a': '3', 'c': '3'}, action='addleft')

        self.assertEqual(str(tag1 + tag2), '<meta name="og:a" content="2">\n<meta name="og:b" content="1">')
        self.assertEqual(str(tag1 + tag3), '<meta name="og:a" content="1">\n<meta name="og:b" content="1">\n<meta name="og:c" content="3">')
        self.assertEqual(str(tag1 + tag2 + tag3), '<meta name="og:a" content="2">\n<meta name="og:b" content="1">\n<meta name="og:c" content="3">')
        self.assertEqual(tag1.data, {'a': '1', 'b': '1',})

        # tags addition modifies left tag in expression
        tag1 = cls('og', {'a': '1'}, action='add')
        tag2 = cls('og', {'a': '2', 'b': '2'}, action='addleft')
        tag3 = tag1 + tag2
        tag4 = tag1.copy()
        tag4 += tag2

        self.assertEqual(tag1.action, tag3.action)
        self.assertEqual(tag3.data, {'a': '1', 'b': '2'})
        self.assertEqual(tag3, tag4)

        # dicts merge testing
        tag1 = cls('og', {'a': '1', 'b': [1, 2], 'c': [1, 2], 'd': {'d1': '1', 'e': 3}})
        tag2 = cls('og', {'a': '2', 'b': [3, 4], 'c': '2', 'd': {'d2': '2', 'e': [1, 2]}})

        self.assertEqual(
            (tag1 + tag2).data,
            {'a': '2', 'b': ['3', '4'], 'c': '2', 'd': {'d1': '1', 'd2': '2', 'e': ['1', '2']}})

    def test_tag_compile(self):
        # for parser logic look at test_parse_plain
        cls = NameContentDictMetaTag
        value_none = [[['og'], ('og', '=', '', '', 'None')]]
        value_test = [[['og', 'a'], ('og:a', '=', '', '', 'value')],
                      [['og', 'a'], ('og:c', '=', '"', 'None', '')],
                      [['og', 'a'], ('og:b', '=', '', '', 'None')],
                      [['og', 'a'], ('og:b', '=', '', '', 'True')],
                      [['og', 'a'], ('og:b', '=', '', '', 'False')],
                      [['og', 'a'], ('og:b', '=', '', '', '0')],
                      [['og', 'a'], ('og:b', '=', '', '', '0.0')],
                      [['og', 'a'], ('og:b', '=', '', '', '')],]

        value_upd1 = [[['og'], ('og', '=', '', '', '{super}')],
                      [['og','a'], ('og:a', '=', '', '', 'a')]]
        value_upd2 = [[['og','a'], ('og:a', '=', '', '', 'a')],
                      [['og'], ('og', '=', '', '', '{super}')]]
        value_list = [[['og','a'], ('og:a', '=', '', '', '1')],
                      [['og','a'], ('og:a', '=', '', '', '2')]]
        value_dict = [[['og','a'], ('og:a', '=', '', '', 'a')],
                      [['og','a','b'], ('og:a:b', '=', '', '', 'ab')],
                      [['og','b','a'], ('og:b:a', '=', '', '', 'ba1')],
                      [['og','b','a'], ('og:b:a', '=', '', '', 'ba2')],
                      [['og','c',], ('og:c', '=', '', '', 'cv1')],
                      [['og','c','d'], ('og:c:d', '=', '', '', 'cd1')],
                      [['og','c',], ('og:c', '=', '', '', 'cv2')],
                      [['og','c','d'], ('og:c:d', '=', '', '', 'cd2')],
                      [['og','c',], ('og:c', '=', '', '', 'cv3')],
                      [['og','c','d'], ('og:c:d', '=', '', '', 'cd3')],
                      [['og','c','e'], ('og:c:e', '=', '', '', 'ce3')],
                      [['og','d','a'], ('og:d:a', '=', '', '', 'da1')],
                      [['og','d','a'], ('og:d:a', '=', '', '', 'da2')],
                      [['og','d','a','b'], ('og:d:a:b', '=', '', '', 'dab2')],]

        value_err1 = []
        value_err2 = [[['og'], ('og', '=', '', '', 'None')],
                      [['og'], ('og', '=', '', '', '{super}')]]
        value_err3 = [[['og'], ('og', '=', '', '', 'None')],
                      [['og', 'a'], ('og:a', '=', '', '', 'a')]]
        value_err4 = [[['og'], ('og', '=', '', '', 'value')]]

        value_err5 = [[['og', 'a'], ('og:a', '=', '', '', 'value'),
                       ('b', '=', '', '', 'b')]]

        tag = cls.compile('og', value_none)
        self.assertEqual(tag.data, None)
        self.assertEqual(tag.action, 'unset')

        tag = cls.compile('og', value_test)
        self.assertEqual(tag.data, {'a': ['value', 'None', 'None', 'True', 'False', '0', '0.0', '']})
        self.assertEqual(tag.action, 'set')

        tag = cls.compile('og', value_upd1)
        self.assertEqual(tag.data, {'a': 'a'})
        self.assertEqual(tag.action, 'add')

        tag = cls.compile('og', value_upd2)
        self.assertEqual(tag.data, {'a': 'a'})
        self.assertEqual(tag.action, 'addleft')

        tag = cls.compile('og', value_list)
        self.assertEqual(tag.data, {'a': ['1', '2']})

        tag = cls.compile('og', value_dict)
        self.assertEqual(tag.data, {
            'a': {'value': 'a', 'b': 'ab'},
            'b': {'a': ['ba1', 'ba2']},
            'c': [{'value': 'cv1', 'd': 'cd1'},
                  {'value': 'cv2', 'd': 'cd2'},
                  {'value': 'cv3', 'd': 'cd3', 'e': 'ce3'}],
            'd': {'a': ['da1', {'value': 'da2', 'b': 'dab2'}]},
        })

        # incorrect definition - empty compiled values
        self.assertRaises(MetaTagValueError, cls.compile, 'og', value_err1)
        # more than one root value
        self.assertRaises(MetaTagValueError, cls.compile, 'og', value_err2)
        # none value should be on the first line and only one line
        self.assertRaises(MetaTagValueError, cls.compile, 'og', value_err3)
        # root value should be None or {super}
        self.assertRaises(MetaTagValueError, cls.compile, 'og', value_err4)
        # additional attrs in dict tags is not allowed
        self.assertRaises(MetaTagValueError, cls.compile, 'og', value_err5)

    def test_tag_from_form(self):
        cls = NameContentDictMetaTag

        value_add = ('og', 'a = value', 'add')
        value_addleft = ('og', 'a = value', 'addleft')
        value_set = ('og', 'a = value', 'set')
        value_unset = ('og', '', 'unset')
        value_quotes = ('og', 'a = "v a l u e"', 'add')
        value_spaces = ('og', 'a = v a l u e without quotes and equals', 'add')
        value_multi = ('og', 'a = 1\na = 2', 'set')
        value_types = ('og', 'a = 1\na = True\na = None\na =\na = 0.0', 'set')

        value_err1 = ('og', '{super}\na = 1', 'add')
        value_err11 = ('og', 'None', 'unset')
        value_err2 = ('og', 'a = non-empty', 'unset')
        value_err21 = ('og', '', 'set')
        value_err3 = ('og', 'incorrect-value-without-param-name', 'set')
        value_err31 = ('og', '=incorrect-value-with-empty-param-name', 'set')
        value_err4 = ('og', 'a a = incorrect-param-name', 'set')

        tag = cls.from_form(*value_add)
        self.assertEqual(tag.data, {'a': 'value'})
        self.assertEqual(tag.action, 'add')

        tag = cls.from_form(*value_addleft)
        self.assertEqual(tag.action, 'addleft')

        tag = cls.from_form(*value_set)
        self.assertEqual(tag.action, 'set')

        tag = cls.from_form(*value_unset)
        self.assertEqual(tag.data, None)
        self.assertEqual(tag.action, 'unset')

        tag = cls.from_form(*value_quotes)
        self.assertEqual(tag.data, {'a': 'v a l u e'})

        tag = cls.from_form(*value_spaces)
        self.assertEqual(tag.data, {'a': 'v a l u e without quotes and equals'})

        tag = cls.from_form(*value_multi)
        self.assertEqual(tag.data, {'a': ['1', '2']})

        tag = cls.from_form(*value_types)
        self.assertEqual(tag.data, {'a': ['1', 'True', 'None', '', '0.0',]})

        # {super}/None values should not be used in form-like definition
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err1)
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err11)
        # value should be empty only if action is unset
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err2)
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err21)
        # incorrect value without equal sign, param name and/or value
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err3)
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err31)
        # incorrect attr name (should be word[:word])
        self.assertRaises(MetaTagValueError, cls.from_form, *value_err4)


if __name__ == "__main__":
    unittest.main()
