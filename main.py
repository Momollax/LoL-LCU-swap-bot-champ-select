import sys
import requests
import json
from time import sleep
import platform
import psutil
import base64
from os import system, name
from lcu_driver import Connector
from riotwatcher import LolWatcher, ApiError
import warnings
warnings.filterwarnings('ignore')
# variables

app_port = None
auth_token = None
riotclient_auth_token = None
riotclient_app_port = None
region = None
lcu_name = None   # LeagueClientUx executable name
showNotInChampSelect = True
# functions


def getLCUName():
    '''
    Get LeagueClient executable name depending on platform.
    '''
    global lcu_name
    if platform.system() == 'Windows':
        lcu_name = 'LeagueClientUx.exe'
    elif platform.system() == 'Darwin':
        lcu_name = 'LeagueClientUx'
    elif platform.system() == 'Linux':
        lcu_name = 'LeagueClientUx'


def LCUAvailable():
    '''
    Check whether a client is available.
    '''
    return lcu_name in (p.name() for p in psutil.process_iter())


def getLCUArguments():
    global auth_token, app_port, region, riotclient_auth_token, riotclient_app_port
    '''
    Get region, remoting-auth-token and app-port for LeagueClientUx.
    '''
    if not LCUAvailable():
        sys.exit('No ' + lcu_name + ' found. Login to an account and try again.')

    for p in psutil.process_iter():
        if p.name() == lcu_name:
            args = p.cmdline()

            for a in args:
                if '--region=' in a:
                    region = a.split('--region=', 1)[1].lower()
                if '--remoting-auth-token=' in a:
                    auth_token = a.split('--remoting-auth-token=', 1)[1]
                if '--app-port' in a:
                    app_port = a.split('--app-port=', 1)[1]
                if '--riotclient-auth-token=' in a:
                    riotclient_auth_token = a.split('--riotclient-auth-token=', 1)[1]
                if '--riotclient-app-port=' in a:
                    riotclient_app_port = a.split('--riotclient-app-port=', 1)[1]

                    
def clear():
    # for windows
    if name == 'nt':
        _ = system('cls')
    # for mac and linux(here, os.name is 'posix')
    else:
        _ = system('clear')


connector = Connector()
@connector.ready

async def connect(connection):
    
    global showNotInChampSelect

    getLCUName()

    getLCUArguments()

    lcu_api = 'https://127.0.0.1:' + app_port
    riotclient_api = 'https://127.0.0.1:' + riotclient_app_port

    lcu_session_token = base64.b64encode(
        ('riot:' + auth_token).encode('ascii')).decode('ascii')

    riotclient_session_token = base64.b64encode(
        ('riot:' + riotclient_auth_token).encode('ascii')).decode('ascii')

    lcu_headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': 'Basic ' + lcu_session_token
    }

    riotclient_headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'LeagueOfLegendsClient',
        'Authorization': 'Basic ' + riotclient_session_token
    }

    get_current_summoner = lcu_api + '/lol-summoner/v1/current-summoner'
    headers = {'Content-type': 'application/json'}
    r = requests.get(get_current_summoner, headers=lcu_headers, verify=False)
    r = json.loads(r.text)
    print("Welcome to the League of Legends swap bot :)!")
    print('Connected: ' + r['displayName'])

    checkForLobby = True
    while True:
        get_champ_select = lcu_api + '/lol-champ-select/v1/session'
        r = requests.get(get_champ_select, headers=lcu_headers, verify=False)
        r = json.loads(r.text)
        if 'errorCode' in r:
            checkForLobby = True
            if showNotInChampSelect:
                print('Not in champ select. Waiting for game...')
                showNotInChampSelect = False
        else:
            if checkForLobby:
                clear()
                print('\n* Found lobby. *\n')

                friends = []
                tmp = await connection.request('get', '/lol-chat/v1/friends')
                tmp = await tmp.json()
                for i in tmp:
                    friends.append(i['summonerId'])
                #me = await connection.request('get', '/lol-chat/v1/me')
                #me = await me.json()
                #friends.append(me['summonerId'])
                while True: 
                    session = '/lol-champ-select/v1/session'
                    request = await connection.request('get', session)
                    request = await request.json()
                    #print(request)
                    
                    for i in request['myTeam']:
                        for j in friends:
                            if i['summonerId'] == j:
                                print('Found friend in lobby: ' + str(i['summonerId']))
                                try:
                                    counter = 0
                                    for k in request['pickOrderSwaps']:
                                        print(request['pickOrderSwaps'][counter]['cellId'], i['cellId'])
                                        if request['pickOrderSwaps'][counter]['cellId'] == i['cellId']:
                                            cellId = request['pickOrderSwaps'][counter]['cellId']
                                            print('cellId: ' + str(cellId))
                                            id = request['pickOrderSwaps'][counter]['id']
                                            print('id: ' + str(id))
                                            state = request['pickOrderSwaps'][counter]['state']
                                            print('state: ' + str(state))
                                            #if state == 'AVAILABLE':
                                            #print('Found available trade Sending request...')
                                            await connection.request('post', '/lol-champ-select/v1/session/swaps/' + str(id) + '/request', json={'cellId': cellId, 'id': id, 'state': state})
                                            await connection.request('post', '/lol-champ-select/v1/session/swaps/' + str(id) + '/cancel')
                                        counter = counter + 1
                                except:
                                    print('No available trades')
                    # accept trade
                    try:
                        await connection.request('post', '/lol-champ-select/v1/session/swaps/' + str(id) + '/accept')
                    except:
                        print('No trades to accept')

connector.start()

#reminder
#https://127.0.0.1:53127/lol-champ-select/v1/session/swaps/29/request
#{cellId: 5, id: 29, state: "AVAILABLE"}
#cellId: 5
#id: 29
#state: "AVAILABLE"

#accept
#https://127.0.0.1:58028/lol-champ-select/v1/session/swaps/33/accept
#