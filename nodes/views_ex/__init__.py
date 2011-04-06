"""
Views extra for each node stored in file with name equal node_name.
Node view_ex:
    receive:    request and **kwparams,
    return:     subclass of HttpResponse or kwparams
Item view_ex:
    receive:    request, item and **kwparams,
    return:     subclass of HttpResponse or (item, kwparams) tuple
"""