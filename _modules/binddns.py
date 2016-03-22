import salt.client

def node_replace(node, minion_id_replace):
    for key, repl in minion_id_replace.iteritems():
        node = node.replace(repl['from'], repl['to'])
    return node

def records_from_mine(mine_search_pcre, mine_func, minion_id_replace, mine_result):
    localclient = salt.client.LocalClient()
    ret = localclient.cmd(mine_search_pcre, mine_func, expr_form='pcre')
    if not ret:
        return None

    data = []
    for node, addr in ret.items():
        if minion_id_replace:
            node = node_replace(node, minion_id_replace)
        if type(addr) is list and len(addr) > 0:
            data.append((node, addr[0]))
        else:
            data.append((node, addr))
    return data

