#!/opt/homebrew/bin/python3
import datetime
import time
import json
import os
import re

from loguru import logger
import requests
from typing import List

from bs4 import BeautifulSoup

from ServerJiang import ServerJiang

class PriceChecker:
    def __init__(self, sku_ids: List[str], proxy: str, pusher: ServerJiang):
        self.sku_ids = sku_ids
        self.pusher = pusher

        os.makedirs('data', exist_ok=True)

        self.session = requests.Session()

        if proxy != '':
            self.session.proxies = {
                'http': proxy,
                'https': proxy
            }

        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/101.0.4951.64 Safari/537.36 Edg/101.0.1210.47 '
        })

    def _get_item_name(self, sku_id: int) -> str:
        res = self.session.get('https://item.jd.com/{}.html'.format(sku_id))
        soup = BeautifulSoup(res.text, 'html.parser')

        item_name = soup.find('div', class_='sku-name').text.strip()

        return item_name

    def _get_item_info(self, sku_id: int) -> dict:
        res = self.session.get('https://item-soa.jd.com/getWareBusiness?skuId={}'.format(sku_id))
        return res.json()

    @staticmethod
    def _get_old_item_info(sku_id: int) -> dict:
        with open('data/{}.json'.format(sku_id), 'r') as f:
            old_item_info = json.load(f)

        return old_item_info

    @staticmethod
    def _save_old_item_info(sku_id: int, item_info: dict) -> None:
        with open('data/{}.json'.format(sku_id), 'w') as f:
            json.dump(item_info, f)
    
    @staticmethod
    def _get_histrory_low_info() -> dict:
        with open('data/history.json', 'r') as f:
            history_low_info = json.load(f)

        return history_low_info

    @staticmethod
    def _save_history_low_info(history_low_info: dict) -> None:
        with open('data/history.json', 'w') as f:
            json.dump(history_low_info, f)

    @staticmethod
    def _get_real_price(item_info: dict):
        price = float(item_info['price']['p'])
        
        for activity in item_info['promotion']['activity']:
            if activity['text'] == '满减':
                str = activity['value']

                # match pattern: 满{}元减{}元
                result = re.search('^\u6ee1([\d.]+)\u5143\u51cf([\d.]+)\u5143$', str)
                if not result:
                    continue

                (base, promotion) = result.groups()
                if price < float(base):
                    continue
                price -= float(promotion)
                break
        return price
    
    def send(self, title, message):
        r = self.pusher.send(title, message)
        if (r.status_code != 200):
            logger.info('ios消息推送失败 {}, {}'.format(r.status_code, r.text))
        

    def check_infos_update(self) -> None:
        history_low_info = self._get_histrory_low_info()

        for sku_id in self.sku_ids:
            item_name = self._get_item_name(sku_id)

            if not os.path.exists('data/{}.json'.format(sku_id)):
                item_info = self._get_item_info(sku_id)
                self._save_old_item_info(sku_id, item_info)
                logger.info('{} 首次加入, 创建data文件'.format(item_name))
            if sku_id not in history_low_info:
                item_info = self._get_item_info(sku_id)
                price = self._get_real_price(item_info)
                history_low_info[sku_id] = price
                logger.info('{} 首次加入, 当前价格{}加入史低数据'.format(item_name, price))

            old_item_info     = self._get_old_item_info(sku_id)
            new_item_info     = self._get_item_info(sku_id)
            old_price         = self._get_real_price(old_item_info)
            new_price         = self._get_real_price(new_item_info)
            history_low_price = float(history_low_info[sku_id])

            if old_price != new_price:
                if new_price == history_low_price:
                    self.send(
                        '京东价格追平史低', '{} 价格变动，原价：{}，现价：{}, 史低：{}'.format(
                            item_name, old_price, new_price, history_low_price))
                elif new_price < history_low_price:
                    self.send(
                        '！！！京东价格再创史低', '{} 价格变动，原价：{}，现价：{}, 史低：{}'.format(
                            item_name, old_price, new_price, history_low_price))
                    history_low_info[sku_id] = str(new_price)
                else:
                    self.send(
                        '京东价格变动', '{} 价格变动，原价：{}，现价：{}, 史低：{}'.format(
                            item_name, old_price, new_price, history_low_price))
                    
                logger.info(
                    '{} - {} 价格变动，原价：{}，现价：{}, 史低：{}'.format(sku_id, item_name,
                                                 old_price,
                                                             new_price, history_low_price))

            for old_activity, new_activity in zip(old_item_info['promotion']['activity'],
                                                  new_item_info['promotion']['activity']):
                if old_activity['value'] != new_activity['value']:
                    logger.info('{} 促销信息变动，原促销信息：{}，现促销信息：{}'.format(item_name,
                                                                     old_activity['value'],
                                                                     new_activity['value']))
                    self.send(
                        '京东促销信息变动',
                        '{} 促销信息变动，原促销信息：{}，现促销信息：{}'.format(
                            item_name,
                            old_activity['value'],
                            new_activity['value']))

            self._save_old_item_info(sku_id, new_item_info)
            time.sleep(1)
        self._save_history_low_info(history_low_info)

def main():
    os.makedirs('logs', exist_ok=True)
    logger.add('logs/{time:YYYY-MM-DD}.log',
               rotation='0:00',
               retention='30 days',
               level='DEBUG')

    with open('config.json', 'r') as f:
        config = json.load(f)

    price_checker = PriceChecker(
        config['items'], config['proxy'], ServerJiang(config['push']['sendKey']))

    price_checker.check_infos_update()
    logger.info('{} 时完成检查'.format(datetime.datetime.now()))


if __name__ == '__main__':
    main()
