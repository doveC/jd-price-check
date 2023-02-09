import requests

class ServerJiang:
    def __init__(self, sendKey):
        self.sendKey = sendKey
        self.url = 'https://sctapi.ftqq.com/{}.send'.format(sendKey)
    
    def send(self, title, message):
        r = requests.post(self.url, {'title': title, 'desp': message})
        return r
