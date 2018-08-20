import itertools
import logging
import os
import platform
import socket
from email.mime.text import MIMEText
from hashlib import md5
from smtplib import SMTP_SSL
from time import perf_counter as pc

import requests
from telebot import TeleBot

import cfg


class TelegramReporter:
    last_error = None
    bot = TeleBot(cfg.app.telegram_bot_token)
    host = socket.gethostbyname_ex(socket.gethostname())
    addr = os.environ.get('REMOTE_ADDR', "")

    @staticmethod
    def telegram_error(traceback, info=None):
        """
        Отправляет сообщение в телеграм с ошибкой на сервере
        :param traceback: list of error lines
        """
        config = cfg.app.telegram_reporter.get(platform.node())
        if not config:
            logging.warning("Telegram reporter: Unknown host, can't send message")
        else:
            text = (
                "<b>Error on {name}, node: {host}, {addr}</b>\n"
                "{log}\n"
                "<pre>{body}</pre>\n"
                "<b>Token:</b> {token}\n"
                "<pre>{traceback}</pre>"
            ).format(
                name=config["name"],
                host=TelegramReporter.host,
                addr=TelegramReporter.addr,
                log=info["log"],
                body=info["body"],
                token=info["token"],
                traceback="".join(traceback).replace("<", "").replace(">", ""),
            )
            logging.info("Sending error from node {} to chat {}".format(config["name"], config["chat_id"]))
            if text != TelegramReporter.last_error:
                TelegramReporter.last_error = text
                TelegramReporter.bot.send_message(config["chat_id"], text, parse_mode="html")

    @staticmethod
    def send_message(chat_id, message, only_prod=False, ignore_tests=True, footer=True):
        if ignore_tests and TelegramReporter.host[0].startswith("runner"):
            return
        if only_prod and "Production" not in TelegramReporter.host[0]:
            return
        if footer:
            message = (
                "{}\n"
                "<b>Host:</b> {}, {} "
                "<b>DB:</b> {} "
            ).format(message, TelegramReporter.host, TelegramReporter.addr, cfg.db.host)
        TelegramReporter.bot.send_message(chat_id, message, disable_web_page_preview=True, parse_mode="html")

    @staticmethod
    def send_picture(chat_id, link):
        TelegramReporter.bot.send_photo(chat_id, link)


def send_mail(to, text, subject, type="plain"):
    smtp = SMTP_SSL(cfg.app.smtp_host, port=465)
    smtp.login(cfg.app.smtp_login, cfg.app.smtp_password)

    msg = MIMEText(text or "", _subtype=type)
    msg["Subject"] = subject
    msg["From"] = cfg.app.smtp_from
    msg["To"] = to

    smtp.sendmail(cfg.app.support_email, to, msg.as_string())
    smtp.quit()


def chunks(iterable, n):
    """
    Разделить итератор на куски по n элементов
    :param iterable: итератор
    :param n: количество элементов в куске
    """
    it = iterable
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


# def extract_results(results, *args, **kwargs):
#     """
#     Извлечь список из результатов пиви или эластика
#     :param extra_attrs: аттрибуты из результата, которые надо включить в словарь (peewee)
#     :param results: ответ эластика или пиви
#     :return: list
#     """
#     if len(results) > 0:
#         lst = [x.dict(*args, **kwargs) for x in results]
#     else:
#         lst = []
#     return lst
#
#
# def extract_one(results, *args, **kwargs):
#     for x in results:
#         return x.dict(*args, **kwargs)
#     return None


async def location(ip):
    country = requests.request("GET", "http://api.ipstack.com/{}?access_key={}".format(ip, cfg.app.ipstack_api_key)).json()
    return country


async def gravatar(email):
    digest = md5(email.lower().encode("utf-8")).hexdigest()
    return "https://www.gravatar.com/avatar/{}?d=retro&s={}".format(digest, 500)


class DummyAtomic:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *kwargs):
        pass


def check_atomic(obj):
    if obj:
        return obj.atomic()
    else:
        return DummyAtomic()


class Timer:
    def __init__(self):
        self.start_time = pc()
        self.mark = pc()
        self.counter = 0

    def step(self, step="Step"):
        from_prev = pc() - self.mark
        from_start = pc() - self.start_time
        logging.debug("Step {} {}: {:.3f} from prev step, {:.3f} from start".format(self.counter, step, from_prev*1000, from_start*1000))
        self.mark = pc()
        self.counter += 1
