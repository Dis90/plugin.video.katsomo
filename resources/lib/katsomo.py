# -*- coding: utf-8 -*-
"""
A Kodi-agnostic library for Katsomo
"""
import os
import json
import codecs
import cookielib
import time
import xml.etree.ElementTree as ET
from datetime import datetime

import requests


class Katsomo(object):
    def __init__(self, settings_folder, debug=False):
        self.debug = debug
        self.http_session = requests.Session()
        self.settings_folder = settings_folder
        self.cookie_jar = cookielib.LWPCookieJar(os.path.join(self.settings_folder, 'cookie_file'))
        self.credentials_file = os.path.join(settings_folder, 'credentials')
        try:
            self.cookie_jar.load(ignore_discard=True, ignore_expires=True)
        except IOError:
            pass
        self.http_session.cookies = self.cookie_jar

    class KatsomoError(Exception):
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return repr(self.value)

    def log(self, string):
        if self.debug:
            try:
                print '[Katsomo]: %s' % string
            except UnicodeEncodeError:
                # we can't anticipate everything in unicode they might throw at
                # us, but we can handle a simple BOM
                bom = unicode(codecs.BOM_UTF8, 'utf8')
                print '[Katsomo]: %s' % string.replace(bom, '')
            except:
                pass

    def make_request(self, url, method, params=None, payload=None, headers=None):
        """Make an HTTP request. Return the response."""
        self.log('Request URL: %s' % url)
        self.log('Method: %s' % method)
        self.log('Params: %s' % params)
        self.log('Payload: %s' % payload)
        self.log('Headers: %s' % headers)
        try:
            if method == 'get':
                req = self.http_session.get(url, params=params, headers=headers)
            elif method == 'put':
                req = self.http_session.put(url, params=params, data=payload, headers=headers)
            else:  # post
                req = self.http_session.post(url, params=params, data=payload, headers=headers)
            self.log('Response code: %s' % req.status_code)
            self.log('Response: %s' % req.content)
            self.cookie_jar.save(ignore_discard=True, ignore_expires=False)
            self.raise_katsomo_error(req.content)
            return req.content

        except requests.exceptions.ConnectionError as error:
            self.log('Connection Error: - %s' % error.message)
            raise
        except requests.exceptions.RequestException as error:
            self.log('Error: - %s' % error.value)
            raise

    def raise_katsomo_error(self, response):
        try:
            error = json.loads(response)['error']
            if isinstance(error, dict):
                if 'message' in error.keys():
                    raise self.KatsomoError(error['message'])
                elif 'code' in error.keys():
                    raise self.KatsomoError(error['code'])
            elif isinstance(error, str):
                raise self.KatsomoError(error)

            raise self.KatsomoError('Error')  # generic error message

        except KeyError:
            pass
        except ValueError:  # when response is not in json
            pass

    def save_credentials(self, credentials):
        credentials_dict = json.loads(credentials)

        if self.get_credentials().get('remember_me'):
            credentials_dict['remember_me'] = {}
            credentials_dict['remember_me']['token'] = self.get_credentials()['remember_me']['token']  # resave token
        with open(self.credentials_file, 'w') as fh_credentials:
            fh_credentials.write(json.dumps(credentials_dict))

    def reset_credentials(self):
        credentials = {}
        with open(self.credentials_file, 'w') as fh_credentials:
            fh_credentials.write(json.dumps(credentials))

    def get_credentials(self):
        try:
            with open(self.credentials_file, 'r') as fh_credentials:
                credentials_dict = json.loads(fh_credentials.read())
                return credentials_dict
        except IOError:
            self.reset_credentials()
            with open(self.credentials_file, 'r') as fh_credentials:
                return json.loads(fh_credentials.read())

    def login(self, username=None, password=None):
        url = 'https://api.katsomo.fi/api/authentication/user/login.json'

        if self.get_credentials().get('remember_me'):  # TODO: find out when token expires
            method = 'put'
            payload = {
                'remember_me': self.get_credentials()['remember_me']['token']
            }
        else:
            method = 'post'
            payload = {
                'username': username,
                'password': password,
                'rememberMe': 'true'
            }


        credentials = self.make_request(url, method, payload=payload) 
        self.save_credentials(credentials)

    def get_search_data(self, query):
        url = 'https://api.katsomo.fi/api/web/search/categories/33/assets.json'
        params = {
            'text': query,
            'size': 15
        }

        data = self.make_request(url, 'get', params=params)

        return json.loads(data)['assets']

    def get_programs(self):
    
        url = 'https://static.katsomo.fi/cms_prod/all-programs-subcats.json'

        data = json.loads(self.make_request(url, 'get'))['categories']
        return data

    def get_favorites(self):
        url = 'https://www.katsomo.fi/api/katsomo/private/user/favorites?site=katsomo'

        data = json.loads(self.make_request(url, 'get'))
        return data

    def get_subcats(self, program_id):
        url = 'https://api.katsomo.fi/api/web/search/categories/{0}.json'.format(program_id)

        data = json.loads(self.make_request(url, 'get'))['categories']
        return data

    def get_videos(self, program_id, subcat_id):
        if subcat_id:
            url = 'https://api.katsomo.fi/api/web/search/categories/{0}/assets.json'.format(subcat_id)
        else:
            url = 'https://api.katsomo.fi/api/web/search/categories/{0}/assets.json'.format(program_id)
        
        data = json.loads(self.make_request(url, 'get'))['assets']
        return data

    def get_program_name_by_id(self, program_id):
        url = 'https://static.katsomo.fi/cms_prod/all-programs-subcats.json'

        data = json.loads(self.make_request(url, 'get'))['categories']

        for program in data:
            if program['id'] == program_id:
                title = program['title'].encode('utf-8')
                return title

    def get_program_fanart(self, program_id):
        url = 'https://static.katsomo.fi/cms_prod/series/{0}.json'.format(program_id)

        data = json.loads(self.make_request(url, 'get'))['serie']['mainImage']['src']
        data = data.replace('http://', '')
        return 'http://{0}'.format(data)

    def get_stream(self, video_id):
        stream = {}
        allowed_formats = ['ismusp', 'mpd']
        url = 'https://api.katsomo.fi/api/web/asset/{0}/play.json'.format(video_id)
        params = {'protocol': 'MPD'}
        data_dict = json.loads(self.make_request(url, 'get', params=params, headers=None))['playback']

        stream['drm_protected'] = data_dict['drmProtected']

        if isinstance(data_dict['items']['item'], list):
            for i in data_dict['items']['item']:
                if i['mediaFormat'] in allowed_formats:
                    stream['mpd_url'] = i['url']
                    if stream['drm_protected']:
                        stream['license_url'] = i['license']['@uri']
                        stream['drm_type'] = i['license']['@name']
                    break
        else:
            stream['mpd_url'] = data_dict['items']['item']['url']
            if stream['drm_protected']:
                stream['license_url'] = data_dict['items']['item']['license']['@uri']
                stream['drm_type'] = data_dict['items']['item']['license']['@name']
        return stream

