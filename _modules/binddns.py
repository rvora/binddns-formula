import salt.client

def node_replace(node, minion_id_replace):
    for repl_dict in minion_id_replace:
        node = node.replace(repl_dict['from'], repl_dict['to'])
    return node

def records_from_mine(mine_search_pcre, mine_func, minion_id_replace, mine_result):
    #localclient = salt.client.LocalClient()
    ret = __salt__['mine.get'](mine_search_pcre, mine_func, 'pcre')
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

