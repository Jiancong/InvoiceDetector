#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import request , jsonify, make_response
from flask_restful import Resource, reqparse, Api
import cv2
import numpy as np
import json, codecs
import logging
from restapi import FetchBaiduApi
import datetime
import os
import base64

import MySQLdb
import gc

import urllib.request
import urllib.parse

HTTP_400_BAD_REQUEST = 400
HTTP_407_INTERNAL_ERROR = 407
HTTP_201_CREATED = 201
HTTP_200_SUCCESS = 200

TESS_CMD='tesseract'
RESULT_FOLDER = "./tmp"
ENCODING='ascii' 
UPLOAD_FOLDER = './images'
OCR_POLICY = 'try_out'

class GetTaskImageApi(Resource):
    def __init__(self, DB_HOST, DB_USER, DB_PASSWD, DB_NAME):
        self.db_host = DB_HOST
        self.db_user = DB_USER
        self.db_passwd = DB_PASSWD
        self.db_name = DB_NAME

    def get(self):
        parse = reqparse.RequestParser()
        parse.add_argument('task_id', type=str, required=True)

        args = parse.parse_args()

        task_id = args['task_id']

        # retrieve file type
        conn= MySQLdb.connect(self.db_host, self.db_user, self.db_passwd, self.db_name)
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_type from tasks where task_id =%s", (task_id, ))
            conn.commit()
            dataset = cursor.fetchall()

            # this task_id is not existed.
            if cursor.rowcount == 0:
                response_packet = {
                    "msg": 'Bad request.',
                    "ret": HTTP_400_BAD_REQUEST,
                    "data":{}
                }
                return make_response(jsonify(response_packet), HTTP_400_BAD_REQUEST)

            print('Total Row(s) fetched:', cursor.rowcount)

            for row in dataset:
                file_type = row[0]

        self.mFileType = file_type

        # return thumbnail picture for specific task_id
        filepath = UPLOAD_FOLDER+"/" + task_id + "_thumbnail." + self.mFileType
        print(filepath)

        with open(filepath, "rb") as image:
            image_b64encode_string = base64.b64encode(image.read())

        # result here: dict obj
        response_packet = {
            "msg": 'Access webpage success.',
            "ret": HTTP_200_SUCCESS,
            "data" : {
                "task_id": task_id,
                "file_type": self.mFileType,
                "imageb64": image_b64encode_string,
            }
        }

        return make_response(jsonify(response_packet), HTTP_200_SUCCESS) # <- the status_code displayed code on console



class DetectType3Api(Resource):
    def __init__(self, DB_HOST, DB_USER, DB_PASSWD, DB_NAME):
        self.db_host = DB_HOST
        self.db_user = DB_USER
        self.db_passwd = DB_PASSWD
        self.db_name = DB_NAME
        self.ocr_type = 'baidu' #'baidu':baidu AIyun
        self.ocr_policy = 'tryout' # 'tryout' always try to use specific method almost 3 times.
                                   
    def get(self):
        try:
            parse = reqparse.RequestParser()
            parse.add_argument('task_id', type=str, required=True)
            parse.add_argument('user_id', type=int, required=True)
            args = parse.parse_args()

            task_id = args['task_id']
            user_id = args['user_id']

            # retrieve file type from task_id
            conn= MySQLdb.connect(self.db_host, self.db_user, self.db_passwd, self.db_name)
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id from users where id = %s", (user_id, ))
                conn.commit()
                dataset = cursor.fetchall()
                if cursor.rowcount == 0:
                    raise ValueError("invalid user_id:", user_id)

                cursor.execute("SELECT file_type from tasks where task_id =%s ", (task_id, ))
                conn.commit()
                dataset = cursor.fetchall()
                # this task_id is not existed.
                if cursor.rowcount == 0:
                   raise ValueError("task_id is not existed.") 
                print('Total Row(s) fetched:', cursor.rowcount)

                for row in dataset:
                    file_type = row[0]

            self.mFileType = file_type

            if task_id and user_id and file_type:
                # attempt to retrieve info from backend directory.
                # bypass post2 if result exists.
                sdir = os.path.join(RESULT_FOLDER, task_id)
                response_file = os.path.join(sdir, 'response.json')
                if os.path.exists(sdir) and os.path.exists(response_file):
                    with open(response_file, 'r') as file:
                        json_string = json.load(file)
                        response_packet = {
                                "msg": 'Success.',
                                "ret": HTTP_200_SUCCESS,
                                "data": json_string,
                                }
                        return make_response(jsonify(response_packet), HTTP_200_SUCCESS) # <- the status_code displayed code on console

                if self.ocr_type == 'baidu':
                    fba=FetchBaiduApi.FetchBaiduApi(self.db_host, self.db_user, self.db_passwd, self.db_name)
                    responseBaiduData = fba.getInternal(user_id, task_id, file_type)
                    if responseBaiduData == "":
                        if self.ocr_policy == 'tryout':
                            responseBaiduData = fba.getInternal(user_id, task_id, file_type)
                            if responseBaiduData == "":
                                responseBaiduData = fba.getInternal(user_id, task_id, file_type)
                                if responseBaiduData == "":
                                    print("Internal error happened!")
                                    raise ValueError("Internal server error", HTTP_407_INTERNAL_ERROR )
                    else:
                        print("response=>", responseBaiduData)
                
                    response_data = {
                        "task_id": task_id,
                        "user_id": user_id,
                        "file_type": file_type,
                        "words_result": responseBaiduData,
                    }

                    # store the parse result
                    with open(os.path.join(sdir, "response.json"), 'w') as outfile:
                        # now encoding the data into json
                        # result: string
                        json_data=json.dumps(response_data)
                        outfile.write(json_data)

                    response_packet = {
                        "msg": 'Access webpage success.',
                        "ret": HTTP_200_SUCCESS,
                        "data" : response_data,
                    }
    
                    return make_response(jsonify(response_packet), HTTP_200_SUCCESS) # <- the status_code displayed code on console
                else:
                    raise ValueError("invliad ocr_type setting.")
            else:
                raise ValueError("invalid input setting:", task_id, user_id, file_type)

        except ValueError as err:

            print(err.args)
            if err.args[1] == HTTP_407_INTERNAL_ERROR: 
                response_packet = {
                    "msg": 'Server internal error.',
                    "ret": HTTP_407_INTERNAL_ERROR,
                    "data": {}
                }
                return make_response(jsonify(response_packet), HTTP_400_BAD_REQUEST) # <- the status_code displayed code on console
            else:
                response_packet = {
                    "msg": 'bad request.',
                    "ret": HTTP_400_BAD_REQUEST,
                    "data": {}
                }
                return make_response(jsonify(response_packet), HTTP_400_BAD_REQUEST) # <- the status_code displayed code on console


