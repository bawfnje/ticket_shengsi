import requests
from pprint import pprint
from os import sys
import yaml
import os
import argparse
import time
# import json
import datetime
import hashlib

print('\n')
print(datetime.datetime.now(),'>>>>>>>>>===================start============================<<<<<<<<')
# load config
fileNamePath = os.path.split(os.path.realpath(__file__))[0]
yamlPath = os.path.join(fileNamePath,'config.yaml')
cf = yaml.load(open(yamlPath,'r',encoding='utf-8').read(),Loader=yaml.FullLoader)

# flagOptions > yaml
parser = argparse.ArgumentParser(usage=" option can coverage .yaml ", description="")
parser.add_argument("-f","--from", default=cf['From'], help="出发站", dest="sfrom")
parser.add_argument("-t","--to", default=cf['To'], help="到达站", dest="to")
parser.add_argument("-d","--date", default=cf['Date'], help="订票日期", dest="date")
parser.add_argument("-lbt","--lbt", default=cf['Customization']['LatestBusTime'], help="最晚开车时间", dest="lbt")
parser.add_argument("-lst","--lst", default=cf['Customization']['LatestShipTime'], help="最晚开船时间", dest="lst")
parser.add_argument("-mst","--mst", default=cf['Customization']['MinShipTime'], help="最早开船时间", dest="mst")
parser.add_argument("-line","--line", default=cf['Customization']['LineNum'], help="指定航班", dest="line")
parser.add_argument("-class","--class", default=cf['Customization']['Class'], help="指定舱位", dest="className")
args = parser.parse_args()

md5 = hashlib.md5()

account = {
        'phoneNum': cf['User']['mobile'],
        'passwd': cf['User']['password'],
        'authentication': cf['User']['authentication'],
        'passengers': [],
        'vehicle': [],
        'seatNeed': 0,
    }

def notice(msg):
    message = ""
    if "成功" in msg['message']:
        message = "抢票成功尽快付款"
        print(datetime.datetime.now(),message)
    else:
        message = msg['message']
        print(datetime.datetime.now(),message)
        return
    if cf['Notice']['flag'] is False:
        print(datetime.datetime.now(),"配置不发通知")
        return
    orderId = msg['data']['orderId']
    expireTime = 1000
    res=get("https://pc.ssky123.com/api/v2/user/order/expireTime?orderId="+orderId,None)
    expireTime = res['data']
    checkToken()
    params = {"userId":userid,"orderId":orderId,"payFee":msg['payFee']}
    res=post("https://pc.ssky123.com/api/v2/pay/wx/qrcodePay",params)
    qrcodeUrl = ""
    if res['code'] == 200:
        qrcodeUrl = res['data']['qrcodeUrl']
    pyload = 'expireTime='+str(expireTime)+'&msg='+''+'&orderId='+str(orderId)+'&qrcodeUrl='+qrcodeUrl+'&title='+message+'&toUser='+cf['Notice']['toUser']
    print(datetime.datetime.now(),pyload)
    pyloadSalt=pyload+cf['Notice']['salt']
    md5.update(pyloadSalt.encode('utf-8'))
    value = md5.hexdigest()
    pyload=pyload+'&sign='+value
    sendMail = requests.post(cf['Notice']['companyWx']+'?'+pyload).json()
    print(datetime.datetime.now(),sendMail['message'])

    params = {"userId":userid,"orderId":orderId,"orderItemId":"0"}
    while expireTime/1000>0:
        res = post("https://pc.ssky123.com/api/v2/pay/check/ioPay",params)
        print(datetime.datetime.now(),res['code'],res['message'],"剩余时间："+str(expireTime))
        if res['code'] == 300:
            time.sleep(5)
            expireTime = expireTime - 5000
        else :
            break   
# notice("script running  ")

def checkToken():
    res = requests.get('https://www.ssky123.com/api/v2/user/tokenCheck', headers={'authentication': account['authentication'], 'token': token,    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
        'Content-Type': 'application/json'}).json()
    print(datetime.datetime.now(),"checkToken:",res['code'],res['message'])
    return   

def get(url, params={}):
    checkToken()
    print(datetime.datetime.now(),"getRequestURL:",url)
    res = requests.get(url, headers={'authentication': account['authentication'], 'token': token,
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            'Content-Type': 'application/json'}, params=params).json()
    print(datetime.datetime.now(),"getResponse:",res['code'],res['message'])
    return res

def post(url, params={}):
    checkToken()
    print(datetime.datetime.now(),"postRequestURL:",url)
    res =  requests.post(url, headers={'authentication': account['authentication'], 'token': token,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
        'Content-Type': 'application/json'}, json=params).json()
    print(datetime.datetime.now(),"postResponse:",res['code'],res['message'])
    return res


def getPassengers():
    print(datetime.datetime.now(),'===================get passengers Info============================')
    res = get("https://www.ssky123.com/api/v2/user/passenger/list",None)
    account['passengers'].clear()
    # print(datetime.datetime.now(),"=====check====")
    # pprint(passengers)
    # print(datetime.datetime.now(),"======vs======")
    # pprint(account['passengers'])
    # print(datetime.datetime.now(),"======end======")
    for passer in res['data'][::-1]:
        if len(cf['User']['passengers'])>0 and passer['passName'] not in cf['User']['passengers'] and passer['passName'] not in cf['User']['childPassengers']:
            continue
        account['passengers'].append({
            'passName':passer['passName'],
            'passId':passer['id'],
            'credentialType':passer['passType'],
        })
        account['seatNeed']+=1

def getVehicle():
    print(datetime.datetime.now(),'===================get vehicle Info============================')
    res = get("https://www.ssky123.com/api/v2/user/vehicle/list",None)
    account['vehicle'] = []
    for passer in res['data'][::1]:
        if len(cf['User']['vehicle'])>0 and passer['plateNum'] not in cf['User']['vehicle']:
            continue
        account['vehicle'].append({
            'plateNum':passer['plateNum'],
            'id':passer['id'],
            'passType':"10",
        })


code = 0
errors = 0
tryTimes = 1
diffDays = 4
debug = False
url = 'https://www.ssky123.com/api/v2/user/passLogin?phoneNum=' + account['phoneNum'] + '&passwd=' + account['passwd'] + '&deviceType=3'
# print(datetime.datetime.now(),'url:',url)
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
    'Content-Type': 'application/json'
}
print(datetime.datetime.now(),'===================Login Info============================')
login_res = requests.post(url,headers=headers)
# print(datetime.datetime.now(),'login_res:',login_res)
login_res = login_res.json()
token = login_res['data']['token']
print(datetime.datetime.now(),'token:',token)
passengers = account['passengers']
userid = login_res['data']['userId']
token = login_res['data']['token']
shipWithCar = False
if len(cf['User']['vehicle'])>0:
    shipWithCar = True
# 提前获得，避免网络拥堵
getPassengers()
if shipWithCar :
    getVehicle()
    
while code != 200 and errors<3 and diffDays>0: # and tryTimes<6
    print(datetime.datetime.now(),'Let\'s go ... ... ... ')
    if tryTimes%100==0:#刷新token
        print(datetime.datetime.now(),'===================Login refresh Info============================')
        login_res = requests.post('https://www.ssky123.com/api/v2/user/passLogin?phoneNum=' + account['phoneNum'] + '&passwd=' + account['passwd'] + '&deviceType=3').json()
        token = login_res['data']['token']
        print(datetime.datetime.now(),'token:',token)
    time.sleep(0.01)

    def checkSeat(s):
        if args.className!='' and s['className']==args.className:
            return False

        if s['pubCurrentCount'] > 0:
            return True
        return False

    print(datetime.datetime.now(),'===================get Route Info============================')
    if args.date is None or diffDays <4 : #or route is None
        args.date = (datetime.datetime.now() + datetime.timedelta(days=diffDays)).strftime('%Y-%m-%d')
    print(datetime.datetime.now(),'date:'+args.date,',diffDays:'+str(diffDays))
    shipUrl = "https://pc.ssky123.com/api/v2/line/ship/enq"
    if shipWithCar:
        shipUrl = 'https://www.ssky123.com/api/v2/line/ferry/enq'
    query_ticket_res = post(shipUrl,
                            {
                                'startPortNo': cf['PortNo'][args.sfrom],
                                'endPortNo': cf['PortNo'][args.to],
                                'startDate': args.date
                            })
    # pprint(query_ticket_res)
    # route = None
    routes = []
    for tr in query_ticket_res['data'][::1]:
        line = str(tr['lineNum']) + str(tr['sx'])
        # pprint(tr)
        # check route
        if args.lbt!="" and tr['busStartTime']!="" and tr['busStartTime']>args.lbt:
            print(datetime.datetime.now(),"route >>>>",line,tr['sailTime'],tr['busStartTime'],"开车时间晚于设置的最晚开车时间"+args.lbt)
            continue
        if args.lst!="" and tr['sailTime']!="" and tr['sailTime']>args.lst:
            print(datetime.datetime.now(),"route >>>>",line,tr['sailTime'],tr['busStartTime'],"开船时间晚于设置的最晚开船时间"+args.lst)
            continue
        if args.mst!="" and tr['sailTime']!="" and tr['sailTime']<args.mst:
            print(datetime.datetime.now(),"route >>>>",line,tr['sailTime'],tr['busStartTime'],"开船时间早于设置的最早开船时间"+args.mst)
            continue
        if args.line!='' and (tr['lineNum']+tr['sx'])!=args.line:
            print(datetime.datetime.now(),"route >>>>",line,tr['sailTime'],tr['busStartTime'],"航次不是设置的指定航线"+args.line)
            continue
        # ii = 0
        seatClass = "seatClasses"
        if shipWithCar :
            seatClass = "driverSeatClass"
        for s in tr[seatClass][::-1]:
            # notice localCurrentCount>0 but pubCurrentCount=0
            # if s['localCurrentCount'] > 0 or s['pubCurrentCount'] > 0:
            #     print(datetime.datetime.now(),"route >>>>",line,'>localCurrentCount:',s['localCurrentCount'],'>className:',s['className'],'>pubCurrentCount:',s['pubCurrentCount'])
            if checkSeat(s) is True:
                # seatIndex = ii
                route = tr
                route[seatClass] = []
                route[seatClass].append(s)
                if debug:
                    pprint(route)
                routes.append(route)
                print(datetime.datetime.now(),"route >>>>",line,tr['sailTime'],tr['busStartTime'],s['className'],">>>>>>有票:大众-"+str(s['pubCurrentCount'])+" 当地居民-"+str(s['localCurrentCount']))
                # break
            else:
                print(datetime.datetime.now(),"route >>>>",line,tr['sailTime'],tr['busStartTime'],s['className'],">>>>>>无票:大众-"+str(s['pubCurrentCount'])+' 当地居民票:'+str(s['localCurrentCount']))
            # ii+=1
        # if route is not None:

    for route in routes[::1]:
        if route is not None and code != 200:
            print(datetime.datetime.now(),tryTimes,'.Let\'s go ... ... ... ',route['sailDate'],route['sailTime'])
            print(datetime.datetime.now(),'===================Route Info============================',len(routes),route['sailDate'],route['sailTime'])
            if debug:
                pprint(route)
            else:
                print(datetime.datetime.now(),"Route:",str(tr['lineNum']) + str(tr['sx']),route['lineName'],route['sailDate'],route['sailTime'],route['startPortName'],route['endPortName'])
            # notice(route)
            print(datetime.datetime.now(),'===================Seat Info============================')
            seat = route['seatClasses'][0]
            if debug:
                pprint(seat)
            else:
                print(datetime.datetime.now(),"Seat:",seat['className'],seat['pubCurrentCount'],seat['localCurrentCount'],seat['seatStateName'],seat['totalCount'])
            # notice(seat)
            if shipWithCar:
                print(datetime.datetime.now(),'===================driverSeat Info============================')
                driverSeat = route['driverSeatClass'][0]
                if debug:
                    pprint(driverSeat)
                else:
                    print(datetime.datetime.now(),"DriverSeat:",driverSeat['className'],driverSeat['pubCurrentCount'],driverSeat['localCurrentCount'],driverSeat['seatStateName'],driverSeat['totalCount'])
            print(datetime.datetime.now(),'===================passengers Info============================')
            if debug:
                pprint(passengers)
            else:
                for passenger in passengers:
                    print(datetime.datetime.now(),"passenger:",passenger['passName'],passenger['credentialType'],passenger['passId'])
            if shipWithCar:
                vehicle = account['vehicle'][0]
                print(datetime.datetime.now(),'===================vehicle Info============================')
                if debug:
                    pprint(vehicle)
                else:
                    print(datetime.datetime.now(),"vehicle:",vehicle['plateNum'],vehicle['passType'],vehicle['id'])
            orderItemRequests = []
            order = route
            order['totalFee'] = 0
            order['totalPayFee'] = 0
            for p in passengers:
                if len(cf['User']['passengers'])>0 and p['passName'] == passengers[0]['passName'] and shipWithCar:
                    p['seatClassName'] = driverSeat['className']
                    p['seatClass'] = driverSeat['classNum']
                    p['realFee'] = driverSeat['totalPrice']
                    p['ticketFee'] = driverSeat['totalPrice']
                    p['plateNum'] = vehicle['plateNum']
                    p['passType'] = vehicle['passType']
                    order['totalPayFee'] = order['totalPayFee'] + driverSeat['totalPrice']
                    order['totalFee'] = order['totalFee'] + driverSeat['totalPrice']
                else:
                    p['seatClassName'] = seat['className']
                    p['seatClass'] = seat['classNum']
                    p['realFee'] = seat['totalPrice']
                    p['ticketFee'] = seat['totalPrice']
                    if p['credentialType'] == 2:
                        p['realFee'] = seat['totalPrice'] * 0.5 + 2
                    order['totalPayFee'] = order['totalPayFee'] + p['realFee']
                    order['totalFee'] = order['totalFee'] + p['ticketFee']
                if len(cf['User']['addFreeChild'])>0 and p['passName'] in cf['User']['addFreeChild']:
                    p['freeChildCount'] = 1
                else:
                    p['freeChildCount'] = 0
                orderItemRequests.append(p)

            order['seatClasses'] = []
            order['driverSeatClass'] = []
            order['orderItemRequests'] = orderItemRequests
            order['userId'] = userid
            order['contactNum'] = account['phoneNum']
            order['sailDate'] = args.date
            print(datetime.datetime.now(),'=====================order==========================',route['sailDate'],route['sailTime'])
            if debug:
                pprint(order)
            else:
                for item in order['orderItemRequests']:
                    print(datetime.datetime.now(),"OrderItem:",item['passName'],item['seatClass'],item['seatClassName'],item['realFee'])    
                print(datetime.datetime.now(),"Order:",route['totalPayFee'])    
            print(datetime.datetime.now(),"第"+str(tryTimes)+"提交......")
            if (tryTimes-1)%3==0 and tryTimes>1:
                print(datetime.datetime.now(),"满3次，休息15秒再提交")
                time.sleep(15)
            # second = datetime.datetime.now().strftime('%S')
            # minute = datetime.datetime.now().strftime('%M')
            hour = datetime.datetime.now().strftime('%H')
            while int(hour) < 7:
                print(datetime.datetime.now(),"未到时间",hour,"休息1秒再继续")
                time.sleep(1)
                # second = datetime.datetime.now().strftime('%S')
                hour = datetime.datetime.now().strftime('%H')
            # res = {'code':300,'message':'当前航班网上售票时间是07:00到23:00，请在售票时间内购票'}
            # res = {'code':300,'message':'车客渡司机无票'}
            # res = {'code':200,'message':'成功'}
            res = post('https://www.ssky123.com/api/v2/holding/save', order)
            code = res['code']
            # pprint(res)
            res['payFee'] = route['totalPayFee']
            notice(res)
            print(datetime.datetime.now(),tryTimes,'.This\'s over ... .... ',route['sailDate'],route['sailTime'])
            tryTimes+=1
            if code !=200 and code!=300:
                errors+=1
                continue
            if code == 200:
                break
            if "请在售票时间内购票" in res['message']:
                print(datetime.datetime.now(),"休息1秒再继续")
                time.sleep(1)
                continue
        # else:
    if code == 200:
        break
    # if routes == []:
    print(datetime.datetime.now(),'This\'s over ... .... ')
    # if args.date != datetime.datetime.now().strftime('%Y-%m-%d'):
    diffDays = diffDays - 1
        # continue
print(datetime.datetime.now(),'>>>>>>>>>>===================end============================<<<<<<<<<<')
