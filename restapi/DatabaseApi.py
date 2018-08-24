#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import request , jsonify, make_response
from flask_restful import Resource, reqparse, Api

import MySQLdb
import gc
import json
import os

HTTP_202_ACCEPTED = 202
HTTP_400_BAD_REQUEST = 400
HTTP_405_NO_DATA = 405
RESULT_FOLDER = 'tmp'


class InsertResultApi(Resource):
    def __init__(self, DB_HOST, DB_USER, DB_PASSWD, DB_NAME):
        self.db_host = DB_HOST
        self.db_user = DB_USER
        self.db_passwd = DB_PASSWD
        self.db_name = DB_NAME
        self.ocr_type = "baidu"

    def post(self):
        try:
            json_data = request.get_json(force=True)
            task_id = json_data['task_id'].strip()
            user_id = json_data['user_id'].strip()
            words_result = json_data['words_result']

            if user_id and task_id:

                sdir = os.path.join(RESULT_FOLDER, task_id)
                response_file_path = os.path.join(sdir, 'response.json')
                print("response_file_path=>", response_file_path)

                if os.path.exists(response_file_path):
                    with open(response_file_path, 'r+') as file:
                        json_string = json.loads(file.read())
                        for k, v in words_result.items():
                            json_string['words_result'][k] = v
                        file.seek(0)
                        file.write(json.dumps(json_string))
                        file.truncate()
                else:
                    raise ValueError("response.json file can't find", sdir)
    
                response_packet = {
                        "msg": "Success.",
                        "ret": HTTP_202_ACCEPTED,
                        "data": {}
                }
                return make_response(jsonify(response_packet), HTTP_202_ACCEPTED) # <- the status_code displayed code on console
            else:
                raise ValueError("invalid user_id or task_id", user_id, task_id)

        except ValueError as err:
            print(err.args)
            response_packet = {
                "msg": 'bad request.',
                "ret": HTTP_400_BAD_REQUEST,
                "data": {}
            }
            return make_response(jsonify(response_packet), HTTP_400_BAD_REQUEST) # <- the status_code displayed code on console

class InsertRecordApi(Resource):
    def __init__(self, DB_HOST, DB_USER, DB_PASSWD, DB_NAME):
        self.db_host = DB_HOST
        self.db_user = DB_USER
        self.db_passwd = DB_PASSWD
        self.db_name = DB_NAME

    def post(self):
        try:
            parse = reqparse.RequestParser()
            parse.add_argument('user_id', type=int, required=True)
            parse.add_argument('task_id', type=str, required=True)
            parse.add_argument('file_type', type=str, required=True)
            args = parse.parse_args()
            user_id = args['user_id']
            task_id = args['task_id']
            file_type = args['file_type']
            print("user_id=>", user_id, ",task_id=>", task_id, ", file_type=>", file_type)

            if user_id and task_id:
                conn = MySQLdb.connect(self.db_host, self.db_user, self.db_passwd, self.db_name)
                with conn:
                    cursor = conn.cursor() 
                    cursor.execute('INSERT INTO tasks (task_id, file_type) values(%s, %s)', 
                                    [task_id, file_type])
                    conn.commit()

                    cursor.execute('INSERT INTO records (user_id, task_id ) values(%s, %s)',
                                    [user_id, task_id])
                    conn.commit()
                    print(cursor.rowcount, " record inserted.")
                    if cursor.rowcount == 0 :
                        raise ValueError("No record found.", user_id, task_id)
                    cursor.close()
                    
                    gc.collect()
                    response_packet = {
                        "msg": 'Success.',
                        "ret": HTTP_202_ACCEPTED,
                        "data": {}
                    }
                    return make_response(jsonify(response_packet), HTTP_202_ACCEPTED) # <- the status_code displayed code on console

        except ValueError as err:
            print(err.args)
            response_packet = {
                "msg": 'bad request.',
                "ret": HTTP_400_BAD_REQUEST,
                "data": {}
            }
            return make_response(jsonify(response_packet), HTTP_400_BAD_REQUEST) # <- the status_code displayed code on console

        finally:
            cursor.close()
            
            gc.collect()



class FetchRecordsApi(Resource):
    def __init__(self, DB_HOST, DB_USER, DB_PASSWD, DB_NAME):
        self.db_host = DB_HOST
        self.db_user = DB_USER
        self.db_passwd = DB_PASSWD
        self.db_name = DB_NAME

    def get(self):
        try:
            parse = reqparse.RequestParser()
            parse.add_argument('user_id', type=int, required=True)
            args = parse.parse_args()
            user_id = args['user_id']

            print("user_id =>", user_id)

            if user_id is None:
                raise ValueError("user_id is Null") 
            else:
                conn = MySQLdb.connect(self.db_host, self.db_user, self.db_passwd, self.db_name)
                with conn:
                    cursor = conn.cursor()

                    query_string = "SELECT * FROM records WHERE user_id = '{userid}'".format(userid=user_id,)
                    cursor.execute(query_string)
                    conn.commit()

                    dataset = cursor.fetchall()
                    print('Total Row(s) fetched:', cursor.rowcount)

                    if cursor.rowcount == 0:
                        raise IOError("no record found, ", user_id)

                    result=[]

                    for row in dataset:
                        record_id = row[0]
                        task_id = row[1]
                        user_id = row[2]
                        result.append(task_id)

                        print ("record_id=%s,task_id=%s,user_id=%d" % (record_id, task_id, user_id))

                    j_res = json.dumps(result)              
                    gc.collect()

                    response_data = {
                            "msg": 'Success',
                            "ret": HTTP_202_ACCEPTED,
                            "data": {
                                "task_id_list": j_res,
                                }
                            }
                    response_json = make_response(jsonify(response_data), HTTP_202_ACCEPTED)
                    response_json.headers['Access-Control-Allow-Origin'] = '*'
                    return response_json
                    
        except ValueError as err:
            print(err.args)
            response_packet = {
                "msg": 'bad request.',
                "ret": HTTP_400_BAD_REQUEST,
                "data": {}
            }
            return make_response(jsonify(response_packet), HTTP_400_BAD_REQUEST) # <- the status_code displayed code on console
        except IOError as ioe:
            print(err.args)
            response_packet = {
                "msg": 'bad request.',
                "ret": HTTP_405_NO_DATA,
                "data": {}
            }
            return make_response(jsonify(response_packet), HTTP_405_NO_DATA) # <- the status_code displayed code on console

                
    
