#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import request , jsonify, make_response
from flask_restful import Resource, reqparse, Api

from aip import AipOcr
import json
import os
import gc
import base64
import MySQLdb
import re

from ast import literal_eval

import urllib.request
import urllib.parse

HTTP_200_SUCCESS=200
HTTP_400_BAD_REQUEST = 400

class FetchBaiduApi(Resource):
    def __init__(self, DB_HOST, DB_USER, DB_PASSWD, DB_NAME):
        self.db_host = DB_HOST
        self.db_user = DB_USER
        self.db_passwd = DB_PASSWD
        self.db_name = DB_NAME
        self.app_id = '11206246'
        self.api_key= 'Xdp8WvFlZfG7eGQ54vlTUOc3'
        self.secret_key = '2AEFzhIp4TF8c3xzLpWOqqFE1p25K22f'
        self.vaturl= "https://aip.baidubce.com/rest/2.0/ocr/v1/vat_invoice"
        self.RESULT_FOLDER="./tmp"
        self.IMAGE_FOLDER="./images"

        self.client = AipOcr(self.app_id, self.api_key, self.secret_key)
        pass

    def send_request(self, url, values):
        data = urllib.parse.urlencode(values)
        data = data.encode()
        req = urllib.request.Request(url, data=data)

        with urllib.request.urlopen(req) as response:
            result = response.read()
            return result

    def baidu_gettoken(self, api_key, secret_key):
        url= 'https://aip.baidubce.com/oauth/2.0/token'
        values = {"grant_type": "client_credentials",
                "client_id": api_key, 'client_secret':secret_key}
        #print("url=>", url)
        #print("values=>", values)
        strData=self.send_request(url, values)

        return strData
        pass

    def get_file_content(self, filePath):
        with open(filePath, 'rb') as fp:
            return fp.read()

    def baidu_api(self, client, url, image, options=None):
        """
            通用文字识别
        """
        options = options or {}

        data = {}
        data['image'] = base64.b64encode(image).decode()
        data.update(options)
        return client._request(url, data)

    def getInternal(self, user_id, task_id, file_type):
        try:
            if user_id and task_id:
                print("R=>", self.RESULT_FOLDER)
                print("taskid=>", task_id)
                sdir = os.path.join(self.RESULT_FOLDER, task_id)
                baidu_response_file = os.path.join(sdir, 'response_baidu.json')
                if not os.path.exists(sdir):
                    os.makedirs(sdir)
                    if os.path.exists(baidu_response_file):
                        with open (baidu_response_file, 'r') as file:
                            json_string = json.load(file)
                            return json_string
                else :
                    raise ValueError("error in create folder:", sdir)

                imagename = task_id + "." + file_type
                filePath = os.path.join(self.IMAGE_FOLDER, imagename)

                if os.path.exists(filePath):
                    image = self.get_file_content(filePath)
                else:
                    raise ValueError("Can't find specific file image:", task_id, user_id)

                conn = MySQLdb.connect(self.db_host, self.db_user, self.db_passwd, self.db_name)
                with conn:
                    cursor = conn.cursor()
                    query_string="SELECT  access_token FROM baiduinfo WHERE api_key='{apikey}' and secret_key='{secretkey}'".format(apikey=self.api_key, secretkey = self.secret_key)
                    cursor.execute(query_string)
                    conn.commit()

                    dataset = cursor.fetchall()
                    print('total row fetched:', cursor.rowcount)

                    if not cursor.rowcount:
                        raise ValueError("Can't find access_token with info:", self.api_key, self.secret_key)

                    for row in dataset:
                        access_token = row[0]
                    options = {}
                    options["access_token"] = access_token
                    strResult = self.baidu_api(self.client, self.vaturl, image, options)

                    if 'error_code' in strResult:
                        # access token expired.
                        if strResult['error_code'] == 111 or strResult['error_code'] == 110:
                            my_bytes_value = self.baidu_gettoken(self.api_key, self.secret_key)
                            print("typeof my_bytes_value:", type(my_bytes_value))
                            data = literal_eval(my_bytes_value.decode('utf8'))
                            print("typeof data:", type(data))
                            print('- ' * 20)

                            # update the info table.
                            cursor = conn.cursor()
                            query_string="update baiduinfo set access_token='{at}' where api_key='{ak}' and secret_key='{sk}'".format(at=data['access_token'], ak=self.api_key, sk=self.secret_key)
                            cursor.execute(query_string)
                            conn.commit()
                            strResult = self.baidu_api(self.client, self.vaturl, image, options)
                        else:
                            raise ValueError("Baidu api met calling error:", strResult['error_code'], strResult['error_msg'])
                    print("strResult=>", strResult)
                    # result is returned back.
                    #strResult=> {'log_id': 782009054849159729, 'words_result': {'TotalAmount': '94339.62', 'SellerRegisterNum': '91110105560400782H', 'SellerAddress': '北京市朝阳区立清路6号院1号楼2单元702室53382829', 'CheckCode': '', 'CommodityTax': [{'row': '1', 'word': '5660.38'}], 'AmountInWords': '壹拾万圆整', 'InvoiceType': '专用发票', 'PurchaserRegisterNum': '91350105077403473T', 'InvoiceNum': '20103389', 'Payee': '', 'InvoiceCode': '1100162130', 'Password': '64*-3*570>/2365<92/4-24516/28>94<2>/0538651-35516+827034*1-179/66142>17310/3>>>1807416<0>/7<*76/46>0-726438', 'CommodityName': [{'row': '1', 'word': '信息服务费'}], 'Remarks': '如技术有', 'PurchaserBank': '中国民生银行股份有限公司福州金山36369881', 'NoteDrawer': '管理7a', 'CommodityAmount': [{'row': '1', 'word': '94339.'}], 'PurchaserName': '福州靠谱网络有限公司', 'TotalTax': '5660.38', 'CommodityNum': [{'row': '1', 'word': ''}], 'CommodityTaxRate': [{'row': '1', 'word': '6%'}], 'PurchaserAddress': '福州市马尾区快安路8号5-2K楼房0591-87867769', 'AmountInFiguers': '100000.00', 'SellerBank': '工商银行北京南中园0200096000', 'CommodityUnit': [{'row': '1', 'word': ''}], 'CommodityType': [{'row': '1', 'word': ''}], 'SellerName': '北京久如技术有限公司', 'InvoiceDate': '2017年06月21日', 'CommodityPrice': [{'row': '1', 'word': '94339.622642'}], 'Checker': ''}, 'words_result_num': 30}
                    print("strResult index=>", strResult['words_result']['TotalAmount'])

                    response_data = strResult['words_result']    

                    with open(baidu_response_file, 'w') as outfile:
                        json_data=json.dumps(response_data)
                        outfile.write(json_data)

                    return response_data

            else:
                raise ValueError("invalid task_id and user_id info:", task_id , user_id )
        except ValueError as err:
            print(err.args)
            response_data = ""
            return response_data


    def get(self):
        parse = reqparse.RequestParser()

        parse.add_argument('user_id', type=int, required=True)
        parse.add_argument('task_id', type=str, required=True)
        parse.add_argument('file_type', type=str, required=True)
        args = parse.parse_args()
        user_id = args['user_id']
        task_id = args['task_id']
        file_type = args['file_type']

        response_data = self.getInternal(user_id, task_id, file_type) 
        if response_data == "":
            response_packet = {
                "msg": 'bad request.',
                "ret": HTTP_400_BAD_REQUEST,
                "data": {}
            }
            return make_response(jsonify(response_packet), HTTP_400_BAD_REQUEST) # <- the status_code displayed code on console
        else:
            response_packet = {
                "msg": 'Access webpage success.',
                "ret": HTTP_200_SUCCESS,
                "data" : response_data,
            }
            return make_response(jsonify(response_packet), HTTP_200_SUCCESS) # <- the status_code displayed code on console
