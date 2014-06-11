# coding: utf-8
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from flask import Flask, render_template, request
from redis import Redis
import requests


app = Flask(__name__)
redis = Redis()

XML_URL = 'http://www.cbr.ru/scripts/XML_daily.asp'


@app.route('/')
def index():
    currencies = redis.hgetall('currencies')
    if not currencies:
        currencies = load_currencies()
    error = result = None
    if request.args:
        try:
            amount = Decimal(request.args['amount'])
            v_from, v_to = [Decimal(currencies[request.args[field]]) for field in ('from', 'to')]
        except (InvalidOperation, KeyError):
            error = u'Форма заполнена некорректно'
        else:
            result = amount * (v_from / v_to)
    return render_template('index.html', currencies=currencies, result=result,
                           args=request.args, error=error)


def load_currencies():
    response = requests.get(XML_URL)
    response.raise_for_status()
    assert response.headers['Content-Type'] == 'text/xml'

    tree = ElementTree.fromstring(response.content)
    currencies = {}
    for currency in tree.iter('Valute'):
        data = {child.tag: child.text for child in currency}
        data['Nominal']
        nominal, value = [Decimal(data[field].replace(',', '.')) for field in ('Nominal', 'Value')]
        value /= nominal
        currencies[data['CharCode']] = value

    redis.hmset('currencies', currencies)
    redis.expire('currencies', 3600)
    return currencies


if __name__ == '__main__':
    app.run()
