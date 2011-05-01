from django import get_version
if get_version() < '1.3':
    raise Exception('Since nodes use CBV, it require Django 1.3 or greater.')