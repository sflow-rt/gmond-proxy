#!/usr/bin/env python
### BEGIN INIT INFO
# Provides:          gmond_proxy
# Required-Start:    $network
# Required-Stop:     $network
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Ganglia Gmond Proxy
# Description:       Proxy Ganglia Gmond queryies to sFlow-RT REST API
### END INIT INFO

import SocketServer
import requests
import xml.etree.cElementTree as ET
from daemon import runner
from time import time

metrics = {
  "machine_type": {"group":"system", "title":"Machine Type", "type":"string", "slope":"zero"},
  "os_name":      {"group":"system", "title":"Operating System", "type":"string", "slope":"zero"}, 
  "os_release":   {"group":"system", "title":"Operating System Release", "type":"string", "slope":"zero"},
  "load_one":     {"group":"load", "title":"One minute load average", "type":"float", "slope":"both"},
  "load_five":    {"group":"load", "title":"Five minute load average", "type":"float", "slope":"both"},
  "load_fifteen": {"group":"load", "title":"Fifteen minute load average", "type":"float", "slope":"both"},
  "cpu_num":      {"group":"cpu", "title":"Total number of CPUs", "units":"CPUs", "type":"uint16", "slope":"zero"},
  "cpu_speed":    {"group":"cpu", "title":"CPU Speed", "units":"MHz", "type":"uint32", "slope":"zero"},
  "cpu_user":     {"group":"cpu", "title":"CPU User", "units":"%", "type":"float", "slope":"both"},
  "cpu_nice":     {"group":"cpu", "title":"CPU Nice", "units":"%", "type":"float", "slope":"both"},
  "cpu_system":   {"group":"cpu", "title":"CPU System", "units":"%", "type":"float", "slope":"both"},
  "cpu_idle":     {"group":"cpu", "title":"CPU Idle", "units":"%", "type":"float", "slope":"both"},
  "cpu_wio":      {"group":"cpu", "title":"CPU wio", "units":"%", "type":"float", "slope":"both"},
  "cpu_intr":     {"group":"cpu", "title":"CPU intr", "units":"%", "type":"float", "slope":"both"},
  "cpu_sintr":    {"group":"cpu", "title":"CPU sintr", "units":"%", "type":"float", "slope":"both"},
  "proc_run":     {"group":"process", "title":"Total Running Processes", "type":"uint32", "slope":"both"},
  "proc_total":   {"group":"process", "title":"Total Processes", "type":"uint32", "slope":"both"},
  "mem_total":    {"group":"memory", "title":"Memory Total", "units":"KB", "type":"float", "slope":"zero", "scale":1024},
  "mem_free":     {"group":"memory", "title":"Free Memory", "units":"KB", "type":"float", "slope":"both", "scale":1024},
  "mem_shared":   {"group":"memory", "title":"Shared Memory", "units":"KB", "type":"float", "slope":"both", "scale":1024},
  "mem_buffers":  {"group":"memory", "title":"Memory Buffers", "units":"KB", "type":"float", "slope":"both", "scale":1024},
  "mem_cached":   {"group":"memory", "title":"Cached Memory", "units":"KB", "type":"float", "slope":"both", "scale":1024},
  "swap_total":   {"group":"memory", "title":"Swap Space Total", "units":"KB", "type":"float", "slope":"zero", "scale":1024},
  "swap_free":    {"group":"memory", "title":"Free Swap Space", "units":"KB", "type":"float", "slope":"both", "scale":1024},
  "bytes_in":     {"group":"network", "title":"Bytes Received", "units":"bytes/sec", "type":"float", "slope":"both"},
  "bytes_out":    {"group":"network", "title":"Bytes Sent", "units":"bytes/sec", "type":"float", "slope":"both"},
  "pkts_in":      {"group":"network", "title":"Packets Received", "units":"packets/sec", "type":"float", "slope":"both"},
  "pkts_out":     {"group":"network", "title":"Packets Sent", "units":"packets/sec", "type":"float", "slope":"both"},
  "disk_total":   {"group":"disk", "title":"Total Disk Space", "units":"GB", "type":"double", "slope":"both", "scale":1073741824},
  "disk_free":    {"group":"disk", "title":"Disk Space Available", "units":"GB", "type":"double", "slope":"both", "scale":1073741824},
}
tmax = "300"
dmax = "0"

url = 'http://localhost:8008/table/ALL/host_name,'+(','.join(list(metrics.keys())))+'/json'
started = "%d" % time()
class GmondTcpHandler(SocketServer.BaseRequestHandler):
  def handle(self):
    r = requests.get(url);
    if r.status_code != 200: return
    table = r.json()
    now = "%d" % time()
    ganglia = ET.Element("GANLGLIA_XML")
    ganglia.attrib["source"] = "sflow-rt"
    cluster = ET.SubElement(ganglia,"CLUSTER")
    cluster.attrib["NAME"] = "unspecified"
    cluster.attrib["LOCALTIME"] = now
    cluster.attrib["OWNER"] = "unspecified"
    cluster.attrib["LATLONG"] = "unspecified"
    cluster.attrib["URL"] = "unspecified"
    for row in table:
      tn = "%d" % (row[0]["lastUpdate"] / 1000)
      host = ET.SubElement(cluster,"HOST")
      host.attrib["NAME"] = row[0]["metricValue"]
      host.attrib["IP"] = row[0]["agent"]
      host.attrib["TAGS"] = ""
      host.attrib["REPORTED"] = now
      host.attrib["TN"] = tn
      host.attrib["TMAX"] = tmax
      host.attrib["DMAX"] = dmax
      host.attrib["LOCATION"] = "unspecified"
      host.attrib["GMOND_STARTED"] = started
      for c in range(1,len(row)):
        tn = "%d" % (row[c]["lastUpdate"] / 1000)
        metric = ET.SubElement(host,"METRIC")
        name = row[c]["metricName"]
        metric.attrib["NAME"] = name
        metric.attrib["TN"] = tn
        meta = metrics[name]
        if "units" in meta: 
          metric.attrib["UNITS"] = meta["units"]
        else:
          metric.attrib["UNITS"] = " "
        metric.attrib["TMAX"] = tmax
        metric.attrib["DMAX"] = dmax
        metric.attrib["SLOPE"] = meta["slope"]
        metric.attrib["TYPE"] = meta["type"]
        val = row[c]["metricValue"]
        if "scale" in meta:
          val /= meta["scale"]
        metric.attrib["VAL"] = str(val) 
        extra = ET.SubElement(metric,"EXTRA_DATA")
        if "group" in meta:
          group = ET.SubElement(extra,"EXTRA_ELEMENT")
          group.attrib["NAME"] = "GROUP"
          group.attrib["VAL"] = meta["group"]
        if "title" in meta:
          title = ET.SubElement(extra,"EXTRA_ELEMENT")
          title.attrib["NAME"] = "TITLE"
          title.attrib["VAL"] = meta["title"]
        if "desc" in meta:
          desc = ET.SubElement(extra,"EXTRA_ELEMENT")
          desc.attrib["NAME"] = "DESC"
          desc.attrib["VAL"] = meta["desc"]
   
    self.data = ET.tostring(ganglia)
    self.request.sendall(self.data)

class GmondProxyDaemon():
  def __init__(self):
    self.stdin_path = '/dev/null'
    self.stdout_path = '/dev/tty'
    self.stderr_path = '/dev/tty'
    self.pidfile_path = '/var/run/gmond_proxy.pid'
    self.pidfile_timeout = 5
  def run(self):
    server = SocketServer.TCPServer(('',8649), GmondTcpHandler) 
    server.serve_forever()

app = GmondProxyDaemon()
daemon_runner = runner.DaemonRunner(app)
daemon_runner.do_action()
