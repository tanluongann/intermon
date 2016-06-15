import subprocess
import re
import time, datetime, pytz
from pysnmp.entity.rfc3413.oneliner import cmdgen

from influxdb import InfluxDBClient
from config import config

# ----------------------------------
# Useful functions
# ----------------------------------

def extract_time(output):
    """
    Parse time from ping output
    Return an array with the value and the unit
    """
    output = output.decode('utf-8').strip()
    m = re.match(r".+ time=(([\w,\.]+)\s\w+)", output)
    return m.group(1).split(' ') if m else None

def get_ping(target, count):
    """
    Performs a ping to the target
    """
    ping = subprocess.Popen(["ping", "-c%s" % count, target.strip()], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    res = 0
    rt = 0
    for r in ping.stdout.readlines():
        e = extract_time(r)
        if e:
            res += float(e[0])
            rt += 1
            if e[1] == 's': res *= 1000
    ping.stdout.close()
    if rt > 0: 
        return res / rt
    else: 
        return None

def get_snmp(community, target, port):
     
    cmdGen = cmdgen.CommandGenerator()

    t = time.time()     
    errorIndication, errorStatus, errorIndex, varBindTable = cmdGen.nextCmd(
        cmdgen.CommunityData('azerty'),
        cmdgen.UdpTransportTarget(('192.168.1.1', 161)),
        cmdgen.MibVariable('IF-MIB', 'ifNumber'),
        cmdgen.MibVariable('IF-MIB', 'ifDescr'),
        cmdgen.MibVariable('IF-MIB', 'ifType'),
        cmdgen.MibVariable('IF-MIB', 'ifMtu'),
        cmdgen.MibVariable('IF-MIB', 'ifSpeed'),
        cmdgen.MibVariable('IF-MIB', 'ifPhysAddress'),
        cmdgen.MibVariable('IF-MIB', 'ifPhysAddress'),
        cmdgen.MibVariable('IF-MIB', 'ifInOctets'),
        cmdgen.MibVariable('IF-MIB', 'ifOutOctets'),
        lookupValues=True
    )
    data = {}
     
    if errorIndication:
        print("Error ", errorIndication)
    else:
        if errorStatus:
            print('%s at %s' % (
                errorStatus.prettyPrint(),
                errorIndex and varBindTable[-1][int(errorIndex) - 1] or '?')
            )
        else:
            for varBindTableRow in varBindTable:
                tdata = {}
                for name, val in varBindTableRow:
                    n = name.prettyPrint().split('.')
                    i = n[1]
                    l = n[0].split('::')[1]
                    v = val.prettyPrint()
                    tdata[l] = v
                tdata['posix'] = t
                data[tdata['ifDescr']] = tdata

    return data

def db_write(client, data):
    try:
        client.write_points(data)
    except Exception as e:
        if str(e.code) == '404':
            print("       /!\ Unable to find the database")
        elif str(e.code) == '400':
            print("       /!\ Unable to save the value")
        else:
            print("       /!\ Error with DB, ", e)
            print("       /!\ Data, ", data)

# ----------------------------------
# Execution
# ----------------------------------

if __name__ == '__main__':

    # Initialize the tools
    pdata = {}
    client = InfluxDBClient(config['influxdb']['server'], 
        config['influxdb']['port'], 
        config['influxdb']['user'],
        config['influxdb']['password'], 
        config['influxdb']['dbname']
    )
    a = 0

    # Main loop
    while 1:

        print("Iteration %s" % a)
        a += 1

        # Fetching the SNMP data
        ndata = get_snmp(config['snmp']['community'], config['snmp']['ip'],
            config['snmp']['port'],
        )

        # Processing data and adding calculated values
        for k in ndata:

            if not k in pdata:
                pdata[k] = {}

            dIn = float(ndata[k]['ifInOctets']) - float(pdata[k]['ifInOctets']) if 'ifInOctets' in pdata[k] else -1
            dOut = float(ndata[k]['ifOutOctets']) - float(pdata[k]['ifOutOctets']) if 'ifOutOctets' in pdata[k] else -1
            dTime = float(ndata[k]['posix']) - float(pdata[k]['posix']) if 'posix' in pdata[k] else 1

            ndata[k]['ifInSpeed'] = (dIn / dTime) / 1000
            ndata[k]['ifOutSpeed'] = (dOut / dTime) / 1000
            pdata[k] = ndata[k]

        # Saving data to influxdb
        for k in ndata:
            if k in config['snmp']['interfaces']:

                # Set timestamp for data
                ctime = datetime.datetime.fromtimestamp(ndata[k]['posix'], pytz.UTC)

                l = config['snmp']['interfaces'][k]['name']
                print("   (" + k + ") " + l + " : out {0:.3}".format(str(ndata[k]['ifOutSpeed'])) + " kB/s   -   in {0:.3} ".format(str(ndata[k]['ifInSpeed']) + " kB/s"))

                valin = ndata[k]['ifInSpeed'] if ndata[k]['ifInSpeed'] > 0 else None 
                valout = ndata[k]['ifOutSpeed'] if ndata[k]['ifOutSpeed'] > 0 else None 
                data = [
                    {
                        "measurement": config['info']['name'],
                        "tags": {
                            "property": '%s_speed_in' % l,
                            "group": k,
                        },
                        "time": ctime,
                        "fields": {
                            "value": valin
                        },
                    },
                    {
                        "measurement": config['info']['name'],
                        "tags": {
                            "property": '%s_speed_out' % l,
                            "group": k,
                        },
                        "time": ctime,
                        "fields": {
                            "value": valout
                        },
                    }
                ]
                db_write(client, data)
     
            # for e in ndata[k]:
            #     print("      " + e + " = " + str(ndata[k][e]))

        # Perform all ping tests
        for t in config['ping']['targets']:

            # Getting the data
            ndata = get_ping(t['ip'], config['ping']['count'])
            print("   ping " + t['name'] + " {0:.2} ms".format(str(ndata)))

            # Save the data to influxdb
            ctime = datetime.datetime.fromtimestamp(time.time(), pytz.UTC)
            data = [
                {
                    "measurement": config['info']['name'],
                    "tags": {
                        "property": "ping_%s" % t['name'] ,
                        "group": None
                    },
                    "time": ctime,
                    "fields": {
                        "value": ndata
                    },
                }
            ]
            db_write(client, data)

        # Waiting before repeating
        time.sleep(config['info']['interval'])





