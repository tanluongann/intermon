config = {
    
    "ping": {
        "count": 3,
        "targets": [
            {"name": "local", "ip": "192.168.1.1"},
            {"name": "national", "ip": "baidu.com"},
            {"name": "international", "ip": "8.8.8.8"},
        ]
    },
    "influxdb": {
        "server": "192.168.1.101",
        "port": 8086,
        "user": "xxxxx",
        "password": "yyyyy",
        "dbname": "internetmon"
    },
    "snmp": {
        "ip": "192.168.1.1",
        "community": "zzzzzzz",
        "port": 161,
        "interfaces": {
            "eth1": { "name": "LAN" },
            "ath1": { "name": "Wifi-2.5Gz" },
            "ath0": { "name": "Wifi-5Gz" },
            "ppp0": { "name": "WAN" }
        }
    },
    "info": {
        "name": "router",
        "interval": 2
    }
}