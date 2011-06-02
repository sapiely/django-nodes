from django.core.management.base import BaseCommand, CommandError
from django.db import models
from optparse import make_option
from nodes.models import Node
import pytils, os

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-f', '--file', dest='filename', default=None, help='Full path to file for parsing.'),
        make_option('-n', '--nodetype', dest='nodetype', default='NodeMain', help='Name of node model, default NodeMain.'),
        make_option('-t', '--testmode', dest='testmode', default='true', help='Testmode flag, must be "false" to disable test mode.'),
    )

    def handle(self, *args, **options):
        filename = options['filename']
        nodetype = options['nodetype']
        testmode = options['testmode'] != 'false'

        model = self.get_model(nodetype)
        if not nodetype or not model:
            print 'Error: nodetype param error or model does not exist', nodetype
            return None

        if not filename:
            print 'Error: filename param (-f) is not specialized'
            return None

        if not os.path.isfile(filename):
            print 'Error: specialized path "%s" is not a file' % filename
            return None

        data = open(filename, 'r')
        root = {'kwargs': {'name':'import_root', 'slug':'import_root',}, 'nodes': [], 'level': 0,}
        chain = [root]

        # parser code
        index = 0
        for i in data:
            index += 1
            i = i.decode('utf8')

            if not i.strip().__len__():
                # empty line
                print "Warning: empty string at line #%d" % index
                continue

            level = (i.__len__()-i.lstrip().__len__()) / 4 + 1
            line = i.strip()
            slug = pytils.translit.slugify(line)

            if not slug.__len__():
                # empty slug
                print "Error: empty slug for line #%d" % index, line
                return

            if level==chain[-1]['level']:
                # equal level
                chain.pop()
            elif level==chain[-1]['level']+1:
                # do nothing
                pass
            elif level>chain[-1]['level']:
                # error struct
                print 'Error: error file struct at lne #%d\n' % index, i.rstrip()
                return
            elif level<chain[-1]['level']:
                # fallback
                chain = chain[:level]

            node = {'kwargs': {'name': line, 'slug': pytils.translit.slugify(line),}, 'nodes': [], 'level': level,}
            # add new node as child in parent
            chain[-1]['nodes'].append(node)
            # add new node to chain
            chain.append(node)

        if testmode:
            print 'Success: Testmode is on, type "-t false" or "--testmode=false" to disable'
        else:
            self.insert_tree(root, model=model)
            print 'Success generating node tree from file', filename

    def get_model(self, name):
        """Get required model by name"""
        model = None
        for i in models.get_models():
            if i.__name__ == name and issubclass(i, Node):
                model = i
                break
        return model

    def insert_tree(self, data, parent=None, model=None):
        """Reccursive tree generating from datadict."""

        # create node
        node = model(**data['kwargs'])
        # insert at or root save
        node.insert_at(parent, 'first-child', True) if parent else node.save()
        # reccursive creating items (reversed for non reload node each time)
        for datadict in reversed(data['nodes']):
            self.insert_tree(datadict, node, model=model)