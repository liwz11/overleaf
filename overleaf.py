# !/usr/bin/env python3
# Author: liwz11


import getpass, json, pickle
import re, time, requests
import ssl, websocket

from bs4 import BeautifulSoup
from argparse import ArgumentParser


def on_message(ws, message):
    print(message)

def on_error(ws, error):
    print(error)

def on_close(ws):
    print("### closed ###")


class OverleafClient(object):
    def __init__(self):
        self.homepage = 'https://www.overleaf.com'
        self.project_url = self.homepage + '/project'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0',
            }
        self.cookies_file = '.ov.cookies.cache'
        self.csrf_file = '.ov.csrf.cache'
        
        try:
            self._load_session()
        except (FileNotFoundError, EOFError, TypeError):
            self.cookies = requests.cookies.RequestsCookieJar()
            self.csrf = ''

        if 'overleaf_session2' not in self.cookies.keys() or self.csrf == '':
            self.login(input('Email: '), getpass.getpass())
            self._dump_session()

    def _load_session(self):
        with open(self.cookies_file, 'rb') as f:
            self.cookies = pickle.load(f)
        self.cookies.clear_expired_cookies()

        with open(self.csrf_file, 'r') as f:
            self.csrf = f.read()

    def _dump_session(self):
        with open(self.cookies_file, 'wb') as f:
            pickle.dump(self.cookies, f)

        with open(self.csrf_file, 'w') as f:
            f.write(self.csrf)

    def login(self, email, password):
        # get sign_in page html and get csrf token
        signin_get = requests.get(self.homepage+'/login', headers=self.headers)
        if signin_get.status_code != 200:
            err_msg = 'Status code {0} when loading {1}'
            err_msg = err_msg.format(signin_get.status_code, self.homepage+'/login')
            raise Exception(err_msg)

        html_doc = signin_get.text
        soup = BeautifulSoup(html_doc, 'html.parser')
        for tag in soup.find_all('input'):
            if tag.get('name', None) == '_csrf':
                self.csrf = tag.get('value', None)
                break

        if len(self.csrf) == 0:
            err_msg = 'CSRF token is empty'
            raise Exception(err_msg)

        # send login form
        data = {'_csrf': self.csrf, 'email': email, 'password': password }
        signin_post = requests.post(self.homepage+'/login', headers=self.headers, data=data, cookies=signin_get.cookies, timeout=5)
        if signin_post.status_code != 200:
            err_msg = 'Status code {0} when signing in {1}/login with user [{2}].'
            err_msg = err_msg.format(signin_post.status_code, self.homepage, email)
            raise Exception(err_msg)

        try:
            response = json.loads(signin_post.text)
            if response['message']['type'] == 'error':
                msg = 'Login failed: {0}'
                msg = msg.format(response['message']['text'])
                raise ValueError(msg)
        except json.JSONDecodeError:
            # this happens when the login is successful
            pass

        self.cookies.update(signin_post.cookies)

    def get_websocket_token(self):
        t = str(time.time()).replace('.', '')[:13]
        url = self.homepage + '/socket.io/1/?t=' + t
        r = requests.get(url, headers=self.headers, cookies=self.cookies)
        token = r.text.split(':')[0]

        url = "wss://www.overleaf.com/socket.io/1/websocket/" + token
        websocket.enableTrace(True)
        #ws = websocket.WebSocketApp(url, on_message=on_message, on_error=on_error, on_close=on_close)
        #ws.run_forever()
        ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
        ws.connect(url)
        ws.send('hello')
        time.sleep(1)
        print(ws.recv())
        time.sleep(1)
        ws.send('{"name":"joinProject","args":[{"project_id":"5e60cbcf1afbd8000150aec4"}]}')
        time.sleep(1)
        print(ws.recv())
        #ws.send('{"name":"joinDoc","args":["5e60cbd11afbd8000150aeee",{"encodeRanges":true}]}')
        #print(ws.recv())
        ws.close()

    def compile(self, project_id):
        url = '{0}/project/{1}/compile'.format(self.homepage, project_id)
        data = { "rootDoc_id":None, "draft":False, "check":"silent", "incrementalCompilesEnabled":True, '_csrf':self.csrf }
        r = requests.post(url, headers=self.headers, data=data, cookies=self.cookies)
        print(r.status_code)
        print(r.text)

    def download_pdf(self, project_id):
        url = 'https://www.overleaf.com/project/{}/download/zip'.format(project_id)
        r = requests.get(url, headers=self.headers, cookies=self.cookies, stream=True)
        print(r.status_code)
        r.close()

        url = 'https://www.overleaf.com/project/{}'.format(project_id)
        r = requests.get(url, headers=self.headers, cookies=self.cookies, stream=True)
        print(r.status_code)
        print('output.pdf' in r.text)
        r.close()

if __name__ == '__main__':
    parser = ArgumentParser(description='A script tool to access overleaf.')
    parser.add_argument('--project', type=str, default='', help='project URL or ID')
    args = parser.parse_args()

    project = args.project
    if project == '':
        raise ValueError('Must specify the project.\n')

    project_id = project
    if project.startswith('http'):
        m = re.match('https?://www\.overleaf\.com/project/([^/]+)', project)
        project_id = m.group(1)
        
    client = OverleafClient()
    client.get_websocket_token()
    #client.compile(project_id)