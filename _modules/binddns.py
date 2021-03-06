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
    serial = __salt__['grains.get']('serialnumber', None)
    manuf = __salt__['grains.get']('manufacturer', None)
    if serial and serial.startswith('ec2'):
        return 'ec2'
    elif serial and serial.startswith('Google'):
        return 'gce'
    elif manuf and manuf.startswith('OpenStack'):
        return 'os'
    else:
        raise RuntimeError, "No implemented"

def internal_cloud_ip(corp_suffix=None):
    ctype = _cloud_ip(corp_suffix=corp_suffix)
    return {'ip': ctype['internal_ip'],
            'fqdn': ctype['fqdn']}

def external_cloud_ip(corp_suffix=None):
    ctype = _cloud_ip(corp_suffix=corp_suffix)
    return {'ip': ctype['external_ip'],
            'fqdn': ctype['fqdn']}

def _cloud_ip(corp_suffix=None):
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
        ctype['internal_ip'] = __salt__['grains.get']('ec2_internal_ip', None)
        ctype['external_ip'] = __salt__['grains.get']('ec2_external_ip', None)
        fqdn = __salt__['grains.get']('id')
        if corp_suffix:
            fqdn = fqdn.replace('compute.internal', "aws.%s" % corp_suffix)
        ctype['fqdn'] = fqdn
        return ctype
    elif hy_type == 'gce':
        ctype['type'] = hy_type
        ctype['internal_ip'] = __salt__['grains.get']('gce_internal_ip', None)
        ctype['external_ip'] = __salt__['grains.get']('gce_external_ip', None)
        fqdn = __salt__['grains.get']('id')
        if corp_suffix:
            fqdn = re.sub(r'\.c\.([\w-]+)\.internal', r'.\1.gce.%s' % corp_suffix, fqdn)
        ctype['fqdn'] = fqdn
        return ctype
    elif hy_type == 'os':
        ctype['type'] = hy_type
        ctype['internal_ip'] = __salt__['grains.get']('os_internal_ip', None)
        ctype['external_ip'] = __salt__['grains.get']('os_external_ip', None)
        fqdn = __salt__['grains.get']('id')
        if corp_suffix:
            fqdn = fqdn.replace('novalocal', "os.%s" % corp_suffix)
            fqdn = fqdn.replace('openstacklocal', "os.%s" % corp_suffix)
        ctype['fqdn'] = fqdn
        return ctype
    else:
        raise RuntimeError, "No implemented"

def _node_replace(node, mine_data=None):
    """Extract information from mine data and return node, ip tuple"""

    if isinstance(mine_data, list) and len(mine_data) > 0:
        return (node, mine_data[0])
    elif isinstance(mine_data, (str, unicode)):
        return (node, mine_data)
    elif isinstance(mine_data, dict) and len(mine_data) > 0:
        if 'fqdn' not in mine_data or  'ip' not in mine_data:
            raise RuntimeError, "fqdn or ip not in mine_data"
        node = mine_data['fqdn']
        ip = mine_data['ip']
    else:
        raise RuntimeError, "Unexpected data type"

    return (node, ip)

def records_from_mine(mine_search, mine_func, mine_search_expr):
    """Rerturn list of (node, ip) tuples from Salt mine"""
    ret = __salt__['mine.get'](mine_search, mine_func, mine_search_expr)
    if not ret:
        return []

    data = []
    for node, addr in ret.items():
        (node,ip) = _node_replace(node, addr)
        if ip:
            data.append((node, ip))
    return data

def dual_records_from_mine(mine_search, mine_dual_func, mine_search_expr='pcre', mine_dual_prefix='int-'):
    """Rerturn list of (node, ip) tuples from Salt mine, prefixed with a string"""
    ret = __salt__['mine.get'](mine_search, mine_dual_func, mine_search_expr)
    if not ret:
        return []

    data = []
    for node, addr in ret.items():
        (node, ip) = _node_replace(node, addr)
        node = mine_dual_prefix + node
        if ip:
            data.append((node, ip))
    return data

def auto_delegate_zone_from_mine(auto_delegate_from_mine ):
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
            (node, ip) = _node_replace(node, addr)
            if ip:
                delegated_domain = '.'.join(node.split('.')[1:])
                data.append((delegated_domain, node, ip))

    return data

def auto_delegate_zone_from_grain(auto_delegate_from_grains):
    """Delegate DNS sub-domains to minions matching pattern"""
    data = []
    for auto in auto_delegate_from_grains:
        ret = __salt__['grains.get'](auto['grain'], {})
        if not ret:
            return []
        for node, addr in ret.items():
            (node, ip) = _node_replace(node, addr)
            if ip:
                delegated_domain = '.'.join(node.split('.')[1:])
                data.append((delegated_domain, node, ip))

    return data
