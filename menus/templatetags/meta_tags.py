from django import template
from django.conf import settings
from django.utils.translation import ugettext
from menus.template import inclusion_tag_ex, get_from_context

def show_meta_title(context, main_title='', template="metas/title.html"):
    """render a meta title list into requested template"""
    request = get_from_context(context, 'request')
    title   = [main_title] if main_title else []
    title  += request.meta.title
    title   = [title[i] for i in xrange(len(title)) if not (i and title[i] == title[i-1])]
    context.update({'title':title, 'template':template, })
    return context

def show_meta_chain(context, main_title='', main_url='/', start_level=0, template="metas/chain.html"):
    """
    Shows the breadcrumb from the node that has the same url as the current request
    - main_title: title of the first breadcrumb (if empty, will be ignored with main_url)
    - main_url: url of the first breadcrumb, if main_title (see below)
    - start_level: after which level should the breadcrumb start? 0=home
    - template: template used to render the breadcrumb
    """
    request = get_from_context(context, 'request')
    chain   = [{'name':main_title, 'link':main_url}] if main_title else []
    chain  += request.meta.chain
    chain   = [chain[i] for i in xrange(len(chain)) if not (i and chain[i] == chain[i-1])]
    chain   = chain[start_level:] if len(chain) >= start_level else []
    context.update({'chain': chain, 'template': template, })
    return context

def show_meta_current(context, pattern="<h1>%s</h1>"):
    """shows the current node name"""
    request = get_from_context(context, 'request')
    current = request.meta.current
    pattern = pattern if '%s' in pattern else '%s'
    return pattern % current.title if current and current.attr.get('show_meta_current', True) else ''

def show_meta_keywords(context, main_keywords='', with_tag=False):
    """shows the meta keywords tag"""
    request     = get_from_context(context, 'request')
    keywords    = [main_keywords] if main_keywords else []
    keywords   += request.meta.keywords
    keywords    = ''.join([(' %s' % i.encode('utf8') if i else '') for i in keywords]).strip()
    keywords    = '<meta name="keywords" content="%s" />' % keywords if keywords and with_tag else keywords
    return keywords

def show_meta_description(context, main_description='', with_tag=False):
    """shows the meta description tag"""
    request         = get_from_context(context, 'request')
    description     = [main_description] if main_description else []
    description    += request.meta.description
    description     = ''.join([(' %s' % i.encode('utf8') if i else '') for i in description]).strip()
    description     = '<meta name="description" content="%s" />' % description if description and with_tag else description
    return description

register = template.Library()
register.simple_tag(takes_context=True)(show_meta_current)
register.simple_tag(takes_context=True)(show_meta_keywords)
register.simple_tag(takes_context=True)(show_meta_description)
inclusion_tag_ex(register, takes_context=True)(show_meta_title)
inclusion_tag_ex(register, takes_context=True)(show_meta_chain)