#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Get external IP address from OpenStack or GCE VM
"""
import re
import logging
import httplib
import socket
from salt.grains import core

# Set up logging
LOG = logging.getLogger(__name__)

def _call_http(url, body=None, headers=None):
    """
    Call http requiest via httplib. Require correct path.
    Host: 169.254.169.254
    """
    conn = httplib.HTTPConnection("169.254.169.254", 80, timeout=1)
    if body or headers:
        conn.request('GET', url, body, headers)
    else:
        conn.request('GET', url)
    return conn.getresponse().read().strip()


def _get_ip_address(url, body=None, headers=None):
    try:
        ipv4 = _call_http(url, body, headers)
        if re.match(r'[\d\.]+$', ipv4):
            return ipv4
        else:
            return None

    except httplib.BadStatusLine, error:
        LOG.debug(error)
        return None

    except socket.timeout, serr:
        LOG.info("Could not read metadata (timeout): %s" % (serr))
        return None

    except socket.error, serr:
        LOG.info("Could not read metadata (error): %s" % (serr))
        return None

    except IOError, serr:
        LOG.info("Could not read metadata (IOError): %s" % (serr))
        return None


def os_internal_ip():
    """
    """
    local_url = "/latest/meta-data/local-ipv4"
    body = ''
    headers = {}
    local_ip = _get_ip_address(local_url)
    
    return {'os_internal_ip': local_ip}


def os_external_ip():
    """
    """
    public_url = "/latest/meta-data/public-ipv4"
    local_url = "/latest/meta-data/local-ipv4"
    body = ''
    headers = {}
    public_ip = _get_ip_address(public_url)
    local_ip = _get_ip_address(local_url)
    
    if public_ip:
        #neutron
        return {'os_external_ip': public_ip}
    else:
        #nova
        return {'os_external_ip': local_ip}


def gce_internal_ip():
    """
    """
    url = '/computeMetadata/v1/instance/network-interfaces/0/ip'
    body = ' '
    headers = {'X-Google-Metadata-Request': 'True'}
    local_ip = _get_ip_address(url, body, headers)
    if local_ip:
        return {'gce_internal_ip': local_ip}
    else:
        return {}

def gce_external_ip():
    """
    """
    url = '/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip'
    body = ' '
    headers = {'X-Google-Metadata-Request': 'True'}
    public_ip = _get_ip_address(url, body, headers)
    if public_ip:
        return {'gce_external_ip': public_ip}
    else:
        return {}


if __name__ == "__main__":
    print os_external_ip()
    print gce_external_ip()
    print os_internal_ip()
    print gce_internal_ip()

