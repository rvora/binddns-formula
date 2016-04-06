import re

def _get_addr(addr):
    """Return single IP address"""
    if isinstance(addr, list) and len(addr) > 0:
        return addr[0]
    elif isinstance(addr, (str, unicode)):
        return addr
    else:
        # unknown data type, return something sane
        return '127.0.0.1'

def _get_hybridtype():
    serial = salt['grains.get']('serialnumber', None)
    manuf = salt['grains.get']('manufacturer', None)
    if serial and serial.startswith('ec2'):
        return 'ec2'
    elif serial and serial.startswith('Google'):
        return 'gce'
    elif manuf and manuf.startswith('OpenStack'):
        return 'os'
    else:
        raise RuntimeError, "No implemented"

def ip_cloud(corp=None):
    """Returns a dictionary
    {internal_ip:
     external_ip:
     type:
     fqdn: }
    """
    hy_type = _get_hybridtype()
    ctype = {}
    if hy_type == 'ec2':
        ctype['type'] = hy_type
        ctype['internal_ip'] = salt['grains.get']('ec2_internal_ip', None)
        ctype['external_ip'] = salt['grains.get']('ec2_external_ip', None)
        ctype['fqdn'] = salt['grains.get']('id').replace('compute.internal', corp)
        return ctype
    elif hy_type == 'gce':
        ctype['type'] = hy_type
        ctype['internal_ip'] = salt['grains.get']('ec2_internal_ip', None)
        ctype['external_ip'] = salt['grains.get']('ec2_external_ip', None)
        fqdn = salt['grains.get']('id')
        fqdn = re.sub(r'\.c\.([\w-]+)\.internal', '.\1.' + corp, fqdn)
        ctype['fqdn'] = fqdn
        return ctype
    elif hy_type == 'os':
        ctype['type'] = hy_type
        ctype['internal_ip'] = salt['grains.get']('os_internal_ip', None)
        ctype['external_ip'] = salt['grains.get']('os_external_ip', None)
        ctype['fqdn'] = salt['grains.get']('id').replace('novalocal', corp)
        ctype['fqdn'] = ctype['fqdn'].replace('openstacklocal', corp)
        return ctype
    else:
        raise RuntimeError, "No implemented"

def _node_replace(node, minion_id_replace):
    """Rename minion id using string replace patterns"""
    if 'type' not in minion_id_replace:
        return node
    if minion_id_replace['type'] == 'replace':
        if 'replace_list' not in minion_id_replace:
            return node
        for repl_dict in minion_id_replace['replace_list']:
            node = node.replace(repl_dict['from'], repl_dict['to'])
        return node
    elif minion_id_replace['type'] == 'regex':
        if 'regex_list' not in minion_id_replace:
            return node
        for repl_dict in minion_id_replace['regex_list']:
            node = re.sub(repl_dict['pattern'], repl_dict['repl'])
        return node
    elif minion_id_replace['type'] == 'mine_map':
        # unimplemented
        return node
    else:
        return node

def records_from_mine(mine_search, mine_func, minion_id_replace, mine_search_expr):
    """Rerturn list of (node, ip) tuples from Salt mine"""
    ret = __salt__['mine.get'](mine_search, mine_func, mine_search_expr)
    if not ret:
        return []

    data = []
    for node, addr in ret.items():
        if minion_id_replace:
            node = _node_replace(node, minion_id_replace)
        data.append((node, _get_addr(addr)))
    return data

def dual_records_from_mine(mine_search, mine_dual_func, minion_id_replace, mine_search_expr='pcre', mine_dual_prefix='int-'):
    """Rerturn list of (node, ip) tuples from Salt mine, prefixed with a string"""
    ret = __salt__['mine.get'](mine_search, mine_dual_func, mine_search_expr)
    if not ret:
        return []

    data = []
    for node, addr in ret.items():
        if minion_id_replace:
            node = _node_replace(node, minion_id_replace)
        node = mine_dual_prefix + node
        data.append((node, _get_addr(addr)))
    return data

def auto_delegate_zone_from_mine(auto_delegate_from_mine, minion_id_replace):
    """Delegate DNS sub-domains to minions matching pattern"""
    data = []
    for auto in auto_delegate_from_mine:
        searchdom = auto['nameserver_match']
        auto_mine_func = auto.get('auto_mine_func', 'network.ip_addrs')
        auto_mine_expr = auto.get('auto_mine_expr', 'pcre')
        ret = __salt__['mine.get'](searchdom, auto_mine_func, auto_mine_expr)
        if not ret:
            return []
        for node, addr in ret.items():
            if minion_id_replace:
                node = _node_replace(node, minion_id_replace)
            delegated_domain = '.'.join(node.split('.')[1:])
            data.append((delegated_domain, node, _get_addr(addr)))

    return data

def auto_delegate_zone_from_grain(auto_delegate_from_grains, minion_id_replace):
    """Delegate DNS sub-domains to minions matching pattern"""
    data = []
    for auto in auto_delegate_from_grains:
        ret = __salt__['grains.get'](auto['grain'], {})
        if not ret:
            return []
        for node, addr in ret.items():
            if minion_id_replace:
                node = _node_replace(node, minion_id_replace)
            delegated_domain = '.'.join(node.split('.')[1:])
            data.append((delegated_domain, node, _get_addr(addr)))

    return data
