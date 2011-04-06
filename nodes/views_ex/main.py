from django.http import HttpResponse

def node_test(request, **kwargs):
    print 'node_test'
    return kwargs
    
def item_test(request, item, **kwargs):
    print 'item_test'
    return item, kwargs