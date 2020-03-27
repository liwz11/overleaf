# !/usr/bin/env python3
# Author: liwz11


import os, re, time, math, getpass, json, pickle
import requests, websocket

from bs4 import BeautifulSoup
from argparse import ArgumentParser


class OverleafClient(object):
    def __init__(self):
        self.homepage = 'https://www.overleaf.com'
        self.project_url = self.homepage + '/project'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.122 Safari/537.36',
            }
        self.cookies_file = '.ov.cookies.cache'
        self.csrf_file = '.ov.csrf.cache'
        try:
            self._load_session()
        except (FileNotFoundError, EOFError, TypeError):
            self.cookies = requests.cookies.RequestsCookieJar()
            self.csrf_token = ''

        if 'overleaf_session2' not in self.cookies.keys() or self.csrf_token == '':
            self.login(input('Email: '), getpass.getpass())
            self._dump_session()

    def _load_session(self):
        with open(self.cookies_file, 'rb') as f:
            self.cookies = pickle.load(f)
        self.cookies.clear_expired_cookies()

        with open(self.csrf_file, 'r') as f:
            self.csrf_token = f.read()

    def _dump_session(self):
        with open(self.cookies_file, 'wb') as f:
            pickle.dump(self.cookies, f)

        with open(self.csrf_file, 'w') as f:
            f.write(self.csrf_token)

    def logout(self):
        os.remove(self.cookies_file)
        os.remove(self.csrf_file)
        print("Logout!\n")

    def login(self, email, password):
        print('[+] login\n')

        url = self.homepage + '/login'
        signin_get = requests.get(url, headers=self.headers)
        if signin_get.status_code != 200:
            err_msg = 'Status code %d when GET %s.' % (signin_get.status_code, url)
            raise Exception(err_msg)
        
        self.cookies.update(signin_get.cookies)

        html_doc = signin_get.text
        soup = BeautifulSoup(html_doc, 'html.parser')
        for tag in soup.find_all('input'):
            if tag.get('name', None) == '_csrf':
                self.csrf_token = tag.get('value', None)
                break

        if len(self.csrf_token) == 0:
            raise Exception('CSRF token is empty.')

        # send login form
        data = {'_csrf': self.csrf_token, 'email': email, 'password': password }
        signin_post = requests.post(self.homepage+'/login', headers=self.headers, data=data, cookies=signin_get.cookies, timeout=5)
        if signin_post.status_code != 200:
            err_msg = 'Status code %d when POST %s.' % (signin_post.status_code, url)
            raise Exception(err_msg)

        try:
            response = json.loads(signin_post.text)
            if response['message']['type'] == 'error':
                err_msg = 'Login failed: ' + response['message']['text']
                raise ValueError(err_msg)
        except json.JSONDecodeError:
            # this happens when the login is successful
            pass

        self.cookies.update(signin_post.cookies)

    def get_projects(self):
        print('[+] loading the project list...\n')

        url = self.homepage + '/project'
        projects_get = requests.get(url, headers=self.headers, cookies=self.cookies)
        if projects_get.status_code != 200:
            err_msg = 'Status code %d when GET %s.' % (projects_get.status_code, url)
            raise Exception(err_msg)
        
        html_doc = projects_get.text
        soup = BeautifulSoup(html_doc, 'html.parser')
        for tag in soup.find_all('script'):
            if tag.get('id', None) == 'data':
                self.projects = json.loads(tag.get_text().strip())['projects']
                break

    def get_documents(self, project_id):
        print('[+] loading the document list...\n')

        t = str(time.time()).replace('.', '')[:13]
        url = self.homepage + '/socket.io/1/?t=' + t
        r = requests.get(url, headers=self.headers, cookies=self.cookies)
        websocket_token = r.text.split(':')[0]

        url = 'wss://www.overleaf.com/socket.io/1/websocket/' + websocket_token
        headers = {}
        headers['User-Agent'] = self.headers['User-Agent']
        headers['Cookie'] = 'gke-route=' + self.cookies.get('gke-route')
        
        # websocket.enableTrace(True)
        ws = websocket.WebSocket()
        ws.connect(url, header=headers)
        ws.recv() # 1::
        ws.recv() # 5:::{"name":"connectionAccepted"}
        ws.send('5:1+::{"name":"joinProject","args":[{"project_id":"%s"}]}' % project_id)
        msg = ws.recv() # 6:::1+[null,{"_id","name","rootDoc_id", "rootFolder"},"owner",2]
        ws.close()

        project_info = json.loads(msg.split('6:::1+')[1])
        self.docs = project_info[1]['rootFolder'][0]['docs']        

    def compile(self, project_id, document_id):
        '''
        print('[+] loading the project...')

        url = '%s/project/%s' % (self.homepage, project_id)
        project_get = requests.get(url, headers=self.headers, cookies=self.cookies)
        if project_get.status_code != 200:
            err_msg = 'Status code %d when GET %s.' % (project_get.status_code, url)
            raise Exception(err_msg)

        html_doc = project_get.text
        csrf_token = html_doc.split('window.csrfToken = "')[1].split('";')[0]
        '''
        
        print('[+] compiling the project...\n')

        url = '%s/project/%s/compile' % (self.homepage, project_id)
        headers = {}
        headers['User-Agent'] = self.headers['User-Agent']
        headers['Referer'] = '%s/project/%s' % (self.homepage, project_id)
        data = { 'rootDoc_id': document_id, 'draft': False, 'check': 'silent', 'incrementalCompilesEnabled': True, '_csrf': self.csrf_token }
        r = requests.post(url, headers=self.headers, data=data, cookies=self.cookies)
        if r.status_code != 200:
            err_msg = 'Status code %d when POST %s.' % (r.status_code, url)
            raise Exception(err_msg)

        res = json.loads(r.text)
        if res['status'] != 'success':
            raise Exception('Compiling failed - ' + res['status'])
        
        self.output_files = {}
        for output in res['outputFiles']:
            self.output_files[output['type']] = output['url']
        # print(self.output_files)

    def download(self, project_id, down_filetype, url=''):
        print('[+] downloading the target file...\n')
       
        if url != '':
            down_filetype = url.split('?')[0].split('/')[-1].split('.')[1]
            pass
        elif down_filetype == 'zip':
            url = '%s/project/%s/download/zip' % (self.homepage, project_id)
        else:
            url = '%s%s' % (self.homepage, self.output_files[down_filetype])
        
        r = requests.get(url, headers=self.headers, cookies=self.cookies, stream=True)
        
        if r.status_code == 200:
            with open('output.' + down_filetype, 'wb') as f:
                count = 0
                nbyte = 0
                for chunk in r:
                    f.write(chunk)
                    
                    count += 1
                    nbyte += len(chunk)
                    print('\r' + '▇' * round(math.log(count,2)) + " " + str(round(nbyte/1048576,2)) + 'MB    ', end="")
        print('\n')

        r.close()

if __name__ == '__main__':
    parser = ArgumentParser(description='A script tool to access www.overleaf.com.')
    parser.add_argument('--logout', action='store_true', help='clear cookies and remove csrf token')
    parser.add_argument('--projects', action='store_true', help='list all available projects')
    parser.add_argument('--project', type=str, default='', help='specify a project id, default \'\'')
    parser.add_argument('--docs', action='store_true', help='list all .tex documents in the specified project')
    parser.add_argument('--doc', type=str, default=None, help='specify a document id, default null(the main document)')
    parser.add_argument('--down', type=str, default='pdf', help='specify a file type and download the file, default \'pdf\', options: \'pdf\', \'zip\', \'bbl\'')
    parser.add_argument('--url', type=str, default='', help='specify a url to directly download the target file, default \'\'')
    args = parser.parse_args()

    logout = args.logout
    list_projects = args.projects
    project_id = args.project
    list_docs = args.docs
    document_id = args.doc
    down_filetype = args.down
    down_url = args.url

    client = OverleafClient()
    print('')

    if logout:
        client.logout()
        os._exit(0)
    
    if down_url != '':
        client.download('', '', url=down_url)
        os._exit(0)

    if list_projects:
        client.get_projects()
        for project in client.projects:
            if not project['trashed']:
                print(project['id'], project['name'])
        print('\n')
        os._exit(0)

    if project_id == '':
        print('Please use the option --project to specify a project id.')
        print('Try "python3 overleaf.py --projects" to list all available projects.\n')
        os._exit(0)

    if list_docs:
        client.get_documents(project_id)
        for doc in client.docs:
            if doc['name'].endswith('.tex'):
                print(doc['_id'], doc['name'])
        print('\n')
        os._exit(0)
    
    if down_filetype != 'zip':
        client.compile(project_id, document_id)

    client.download(project_id, down_filetype)

