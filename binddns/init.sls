#!jinja|yaml

{% if salt['pillar.get']('binddns', None) %}
{% from "binddns/defaults.yaml" import rawmap with context %}
{% set datamap = salt['grains.filter_by'](rawmap, merge=salt['pillar.get']('binddns:lookup')) %}

binddns:
  pkg:
    - installed
    - pkgs: {{ datamap.pkgs }}
  service:
    - running
    - name: {{ datamap.service.name }}
{% if datamap.service.reload|default(False) %}
    - reload: True
{% endif %}
    - enable: {{ datamap.service.enable|default(True) }}
    - watch:
{% for c in datamap.config.manage|default([]) %}
      - file: {{ c }}
{% endfor %}
    - require:
      - pkg: binddns
      - file: zonedir

zonedir:
  file:
    - directory
    - name: {{ datamap.zonedir }}
    - mode: 750
    - user: {{ datamap.user.name }}
    - group: {{ datamap.group.name }}

{% if 'defaults_file' in datamap.config.manage %}
defaults_file:
  file:
    - managed
    - name: {{ datamap.config.defaults_file.path }}
    - makedirs: True
    - source: {{ datamap.config.defaults_file.template_path|default('salt://binddns/files/defaults_file.' ~ salt['grains.get']('os_family')) }}
    - template: {{ datamap.config.defaults_file.template_renderer|default('jinja') }}
    - mode: {{ datamap.config.defaults_file.mode|default('644') }}
    - user: {{ datamap.config.defaults_file.user|default(datamap.user.name) }}
    - group: {{ datamap.config.defaults_file.group|default(datamap.group.name) }}
{% endif %}

{% if 'named_conf' in datamap.config.manage %}
named_conf:
  file:
    - managed
    - name: {{ datamap.config.named_conf.path }}
    - source: {{ datamap.config.named_conf.template_path|default('salt://binddns/files/named.conf') }}
    - template: {{ datamap.config.named_conf.template_renderer|default('jinja') }}
    - mode: {{ datamap.config.named_conf.mode|default('640') }}
    - user: {{ datamap.config.named_conf.user|default(datamap.user.name) }}
    - group: {{ datamap.config.named_conf.group|default(datamap.group.name) }}
{% endif %}

{% if 'rndc_key' in datamap.config.manage %}
rndc_key:
  cmd:
    - run
    - name: {{ datamap.config.rndc_key.gen_cmd|default('/usr/sbin/rndc-confgen -r /dev/urandom -a -c ' ~ datamap.config.rndc_key.path ) }}
    - unless: test -f {{ datamap.config.rndc_key.path }}
  file:
    - managed
    - name: {{ datamap.config.rndc_key.path }}
    - mode: {{ datamap.config.rndc_key.mode|default('640') }}
    - user: {{ datamap.config.rndc_key.user|default('root') }}
    - group: {{ datamap.config.rndc_key.group|default(datamap.group.name) }}
    - require:
      - cmd: rndc_key
{% endif %}

{% if 'options' in datamap.config.manage %}
options:
  file:
    - managed
    - name: {{ datamap.config.options.path }}
    - source: {{ datamap.config.options.template_path|default('salt://binddns/files/named.conf.options') }}
    - template: {{ datamap.config.options.template_renderer|default('jinja') }}
    - mode: {{ datamap.config.options.mode|default('640') }}
    - user: {{ datamap.config.options.user|default(datamap.user.name) }}
    - group: {{ datamap.config.options.group|default(datamap.group.name) }}
{% endif %}


{# Zones #}

{%
set z_def = {
  'ttl': 300,
  'serial': salt['grains.get']('bind_serial', '1'),
  'refresh': 86400,
  'retry': 3600,
  'expire': 604800,
  'minimum': 10,
}
%}

{% if 'zoneconfigs' in datamap.config.manage|default([]) %}
zoneconfigs:
  file:
    - managed
    - name: {{ datamap.config.zoneconfigs.path }}
    - source: {{ datamap.config.zoneconfigs.template_path|default('salt://binddns/files/named.conf.zones') }}
    - template: {{ datamap.config.zoneconfigs.template_renderer|default('jinja') }}
    - mode: {{ datamap.config.zoneconfigs.mode|default('644') }}
    - user: {{ datamap.config.zoneconfigs.user|default(datamap.user.name) }}
    - group: {{ datamap.config.zoneconfigs.group|default(datamap.group.name) }}
{% endif %}

{% for z in salt['pillar.get']('binddns:zones', []) %}
  {% if z.create_db_only is not defined %}
    {% set create_db_only = True %}
  {% else %}
    {% set create_db_only = z.create_db_only %}
  {% endif %}
  {% if not (create_db_only and salt['file.file_exists'](datamap.zonedir ~ '/db.' ~ z.name)) %}
    {% set include_list = [] %}
    {% if (z.zone_recs_from_mine is defined and z.zone_recs_from_mine) or
          (z.auto_delegate_from_mine is defined and z.auto_delegate_from_mine) %}
        {% do include_list.append( { 'path': datamap.zonedir + "/in." + z.name } ) %}
    {% endif %}
    {% if z.includes is defined and z.includes %}
      {% for include_dict in z.includes %}
        {% do include_list.append( include_dict ) %}
      {% endfor %}
    {% endif %}
zone_{{ z.name }}:
  file:
    - managed
    - name: {{ datamap.zonedir }}/db.{{ z.name }}
    - source: {{ datamap.config.zones.template_path|default('salt://binddns/files/zonefile') }}
    - template: {{ datamap.config.zones.template_renderer|default('jinja') }}
    - mode: {{ datamap.config.zones.mode|default('644') }}
    - user: {{ datamap.config.zones.user|default(datamap.user.name) }}
    - group: {{ datamap.config.zones.group|default(datamap.group.name) }}
    - require:
      - file: zonedir
    - watch_in:
      - service: binddns
    - context:
        name: {{ z.name }}
        soa: {{ z.soa }}
        ttl: {{ z.ttl|default(z_def.ttl) }}
        serial: {{ z.serial|default(z_def.serial) }}
        refresh: {{ z.refresh|default(z_def.refresh) }}
        retry: {{ z.retry|default(z_def.retry) }}
        expire: {{ z.expire|default(z_def.expire) }}
        minimum: {{ z.minimum|default(z_def.minimum) }}
        contact: {{ z.contact|default('root.' ~ z.name ~ '.') }}
        records: {{ z.records|default([]) }}
        includes: {{ include_list }}
  {% endif %}
{% endfor %}

{% for z in salt['pillar.get']('binddns:zones', []) %}
  {% if z.zone_recs_from_mine is defined or z.auto_delegate_from_mine is defined or z.auto_delegate_from_grains is defined %}
incl_{{ z.name }}:
  file:
    - managed
    - name: {{ datamap.zonedir }}/in.{{ z.name }}
    - source: {{ datamap.config.zones.template_path|default('salt://binddns/files/zone_recs_from_salt') }}
    - template: {{ datamap.config.zones.template_renderer|default('jinja') }}
    - mode: {{ datamap.config.zones.mode|default('644') }}
    - user: {{ datamap.config.zones.user|default(datamap.user.name) }}
    - group: {{ datamap.config.zones.group|default(datamap.group.name) }}
    - require:
      - file: zonedir
    - watch_in:
      - service: binddns
    - context:
        name: {{ z.name }}
        soa: {{ z.soa }}
        ttl: {{ z.ttl|default(z_def.ttl) }}
        serial: {{ z.serial|default(z_def.serial) }}
        refresh: {{ z.refresh|default(z_def.refresh) }}
        retry: {{ z.retry|default(z_def.retry) }}
        expire: {{ z.expire|default(z_def.expire) }}
        minimum: {{ z.minimum|default(z_def.minimum) }}
        contact: {{ z.contact|default('root.' ~ z.name ~ '.') }}
        records: {{ z.records|default([]) }}

        mine_search: {{ z.mine_search|default("[\w-]+\." ~ z.name) }}
        mine_search_expr: {{ z.mine_search_expr|default("pcre") }}

        mine_func: {{ z.mine_func|default('network.ip_addrs') }}

        mine_dual_records: {{ z.mine_dual_records|default(False) }}
        mine_dual_func:  {{ z.mine_dual_func|default('network.ip_addrs') }}
        mine_dual_prefix: {{ z.mine_dual_prefix|default('int-') }}

        auto_delegate_from_mine: {{ z.auto_delegate_from_mine|default([]) }}
        auto_delegate_from_grains: {{ z.auto_delegate_from_grains|default([]) }}

        minion_id_replace: {{ z.minion_id_replace|default({}) }}
  {% endif %}
{% endfor %}

{% endif %}
