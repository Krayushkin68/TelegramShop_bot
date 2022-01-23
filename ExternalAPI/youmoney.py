import json
import random
from string import ascii_letters, digits

import requests


def generate_label():
    label = random.choices(ascii_letters + digits, k=20)
    return ''.join(label)


class YouMoneyPayment:
    def __init__(self, bot_url, config_file='config.json'):
        self.bot_url = bot_url
        self.config_file = config_file

        config = json.load(open(config_file))
        if not config.get('youmoney_token'):
            print('Start authorizing YouMoney')
            client_id = config.get('client_id')
            client_secret = config.get('client_secret')
            if client_id and client_secret:
                self.token = self.authorize(client_id, client_secret)
                print('YouMoney authorized succesfully')
            else:
                print('Not found client_id or client_secret in config file')
                raise Exception('Not found client_id or client_secret in config file')
        else:
            self.token = config['youmoney_token']
            print('YouMoney activated succesfully')

    def authorize(self, client_id, client_secret):
        data = {'client_id': client_id,
                'response_type': 'code',
                'redirect_uri': self.bot_url,
                'scope': "account-info operation-history operation-details incoming-transfers payment-p2p"}
        auth = requests.post(r'https://yoomoney.ru/oauth/authorize', data=data)
        print(f'Enter Auth URL to accept: {auth.url}')

        code = input('Paste code from redirected URL')

        data = {'code': code,
                'client_id': client_id,
                'grant_type': 'authorization_code',
                'redirect_uri': self.bot_url,
                'client_secret': client_secret}
        token_request = requests.post(r'https://yoomoney.ru/oauth/token', data=data)
        new_token = token_request.json().get('access_token')
        if new_token:
            print('Your token: ', new_token)
            config = json.load(open(self.config_file))
            config["youmoney_token"] = new_token
            json.dump(config, open(self.config_file, 'wt'))
            print('Token saved to config file')
            return new_token
        else:
            raise Exception('Error authorizing')

    def account_info(self):
        """
        EXAMPLE
        {'account': '123456789',
        'balance': 1.95,
        'currency': '643',
        'account_type': 'personal',
        'identified': False,
        'account_status': 'named',
        'balance_details': {'total': 1.95, 'available': 1.95}}
        """

        headers = {'Authorization': f'Bearer {self.token}',
                   'Content-Type': 'application/x-www-form-urlencoded'}
        youmoney_account = requests.post(r'https://yoomoney.ru/api/account-info', headers=headers)
        if youmoney_account.status_code == 200:
            return youmoney_account.json()
        else:
            return False

    def create_payment_form(self, amount):
        account_name = self.account_info()['account']
        label = generate_label()
        data = {'receiver': account_name,
                'quickpay-form': 'shop',
                'targets': 'Оплата товара',
                'paymentType': 'SB',
                'sum': amount,
                'label': label}
        quickpay = requests.post(r'https://yoomoney.ru/quickpay/confirm.xml', data=data)
        if quickpay.status_code == 200:
            return label, quickpay.url
        else:
            raise Exception('Connection error')

    def check_payment(self, label):
        """
        EXAMPLE
        {'operations':[{'group_id': 'type_history_non_p2p_deposit', 'operation_id': '687787868535002204',
                       'title': 'Пополнение с карты ****1409', 'amount': 4.9, 'direction': 'in',
                       'datetime': '2021-10-17T12:11:08Z', 'label': '12345678', 'status': 'success',
                       'type': 'deposition',
                       'spendingCategories': [{'name': 'Deposition', 'sum': 4.9}], 'amount_currency': 'RUB',
                       'is_sbp_operation': False}]}
        """

        headers = {'Authorization': f'Bearer {self.token}',
                   'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'label': label,
                'direction': 'in'}
        payment_details = requests.post(r'https://yoomoney.ru/api/operation-history', headers=headers, data=data)
        if payment_details.status_code == 200:
            details = payment_details.json()
            if details.get('operations'):
                status = details['operations'][-1].get('status')
                return status
            else:
                return 'no_info'
        else:
            return False


if __name__ == '__main__':
    bot_url = input('Enter url, default: http://t.me/Andrey_shop_bot\nLeft empty and press enter for default\n')
    if not bot_url:
        bot_url = 'http://t.me/Andrey_shop_bot'
    config_file = input('Enter config file name, default: config.json\nLeft empty and press enter for default\n')
    if not config_file:
        config_file = '../config.json'
    payer = YouMoneyPayment(bot_url=bot_url, config_file=config_file)
    print(payer.account_info())
