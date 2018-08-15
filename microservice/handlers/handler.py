import binascii
import gzip
import json
import logging
import re
import traceback
from hashlib import sha1
from base64 import b64decode
from concurrent.futures import ThreadPoolExecutor
from json import JSONDecodeError
from time import perf_counter as pc
from urllib.parse import unquote

from raven.contrib.tornado import SentryMixin
from telebot.apihelper import ApiException
from tornado.escape import json_decode
from tornado.netutil import is_valid_ip
from tornado.web import RequestHandler

import cfg
from microservice.exceptions import ApiError
from microservice.functions import TelegramReporter
from microservice.metrics import Metrics
from microservice.middleware.session import Session
from microservice.middleware.cache import RedisCache


class Answer:
    """
    Ответ, отправляемый клиенту
    """

    def __init__(self):
        """
        Создает ответ на основе словаря data
        """
        self.t = pc() * 1000
        self.answer = {}

    def compose(self, message=None, data=None, error=None, meta=None):
        """
        Необходимо вызвать для составления ответа
        """
        assert message is not None or error is not None
        self.answer = {"message": message, "error": error, "data": data, "meta": meta}

    def dict(self):
        """
        Возвращает словарь с данными
        """
        self.answer["time"] = self.mark_time()
        return self.answer

    def gzip(self):
        """
        gzipped json
        """
        self.answer["time"] = self.mark_time()
        return gzip.compress(json.dumps(self.answer).encode("utf-8"), compresslevel=cfg.app.gzip_output)

    def mark_time(self):
        """
        Замерить время, поставить временную отметку между текущим временем и предыдущей отметкой
        """
        Metrics.latency.set(pc() * 1000 - self.t)
        return round(pc() * 1000 - self.t, 3)


class SentryMixinExt(SentryMixin):
    def get_sentry_user_info(self):
        """
        Data for sentry.interfaces.User

        Default implementation only sends `is_authenticated` by checking if
        `tornado.web.RequestHandler.get_current_user` tests postitively for on
        Truth calue testing
        """
        try:
            user = self.get_current_user()
        except Exception:
            return {}
        return {
            'user': user
        }


class BasicHandler(SentryMixinExt, RequestHandler):
    executor = ThreadPoolExecutor(max_workers=cfg.app.max_workers_on_executor)
    session_class = None
    cache_method = "user"  # "all", None
    cache_lifetime = 10

    def get_session_class(self):
        return self.session_class or Session

    def initialize(self):
        if self.application.redis_connection:
            self.cache = RedisCache(self.application.redis_connection)
        else:
            self.cache = None
            self.cache_method = None
        self.cached = False
        self.answer = Answer()
        forwarded_ip = self.request.headers.get("X-Forwarded-For", self.request.remote_ip)
        if is_valid_ip(forwarded_ip):
            self.request.remote_ip = forwarded_ip
        self.loop = self.application.loop
        self.json_body = None
        self.session = self.get_session_class()(self.request, self.body, self.args, self.application.objects)
        self.queue = []
        self.version = self.version if hasattr(self, "version") else 0

    def init(self):
        """Redefine this method instead of self.initialize()"""
        pass

    async def prepare(self, *kwargs):
        """
        Выполняется перед  обработкой запроса
        """
        self.add_header('Access-Control-Allow-Origin', '*')
        self.add_header('Access-Control-Allow-Headers', 'Content-Type, %s, X-Client-Type, Origin, Cache-Control, '
                                                        'X-Requested-With, Accept' % self.get_session_class().auth_header)
        self.add_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, PUT, DELETE, OPTIONS, HEAD')
        self.add_header('Access-Control-Allow-Credentials', 'true')
        self.set_header('Content-Type', 'application/json; charset=UTF-8')
        try:
            self.request.headers["User-Agent"] = b64decode(self.request.headers.get("User-Agent", "")).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            pass
        self.client_platform = self.request.headers.get("X-Platform", "")
        self.client_version = self.request.headers.get("X-Version", "")
        try:
            self.api_version = int(self.request.uri.split("/")[1][1:])
        except ValueError:
            self.api_version = 0
        self.endpoint = re.sub("\d", "", "/".join(self.request.uri.split("?")[0].split("/")[2:])).rstrip("/")

        # Caching: if cache found don't call method, just return cached answer
        if self.cache and self.request.headers.get("Cache-Control") != "no-cache" and self.cache_method:
            hash_exists = await self.cache.check_request(self.request_hash(for_user=self.cache_method == "user"))
            if hash_exists:
                restored_answer = await self.cache.restore_answer(self.request_hash(for_user=self.cache_method == "user"))
                if restored_answer == "":
                    self.compose(error="#duplicate_request Request in progress", send=True)
                else:
                    self.answer.answer = restored_answer
                    self.cached = True
                    self.send_result()
            else:
                await self.cache.store_request(self.request_hash(for_user=self.cache_method == "user"), self.cache_lifetime, "")
        self.init()

    async def get(self, **kwargs):
        self.compose(error="#method_not_allowed", status=405, send=True)

    async def post(self, **kwargs):
        self.compose(error="#method_not_allowed", status=405, send=True)

    async def delete(self, **kwargs):
        self.compose(error="#method_not_allowed", status=405, send=True)

    async def patch(self, **kwargs):
        self.compose(error="#method_not_allowed", status=405, send=True)

    async def put(self, **kwargs):
        self.compose(error="#method_not_allowed", status=405, send=True)

    def head(self, *args, **kwargs):
        self.compose(error="#method_not_allowed", status=405, send=True)

    def options(self, smth=None):
        self.set_status(204)
        self.finish()

    def compose(self, message=None, result=None, error=None, status=None, send=False):
        """
        Сформировать ответ
        :param message: сообщение, которое выводится в случае отсутствия ошибки
        :param result: должен содержать параметры data или error
        :param error: текст ошибки
        :param status: кастомный статус код
        :param send: сразу отправить результат клиенту
        """
        if error or (result and result.error):
            error = str(error) if error else None or result.error
            code, *error_message = error.split(maxsplit=1)
            error_message = "".join(error_message)
            if not code or not code.startswith("#"):
                code = "#error"
                error_message = error
            logging.warning("Error: '{}'. Body: {}".format(error, self.body()))
            # Статус из хештегов
            if not status:
                if code in ("#auth", "#oauth", "#access_denied", "#wrong_password"):
                    status = 401
                elif code == "#not_found":
                    status = 404
                elif code in ("#wrong_format", "#wrong_type", "#api_error"):
                    status = 417
                elif code == "#method_not_allowed":
                    status = 405
            self.set_status(status or 400)
            self.answer.compose(message=None, error={"code": code, "message": error_message})
            Metrics.errors_4xx.inc(1)
            self.captureMessage(error, level=logging.WARNING, extra={
                "cached": self.cached,
                "log": self.make_log()
            })
        else:
            self.set_status(status or 200)
            if result:
                result.meta.update(result.kwargs)
                self.answer.compose(message, data=result.data, meta=result.meta)
            else:
                self.answer.compose(message)
        if send:
            self.send_result()

    def send_result(self):
        if cfg.app.gzip_output > 0:
            self.set_header('Content-Encoding', 'gzip')
            self.finish(self.answer.gzip())
        else:
            self.finish(self.answer.dict())

    def make_log(self):
        log_record = "{}: ({}) {} {} [{}] {} ms".format(
            self.get_status(), self.request.remote_ip, self.request.method, unquote(self.request.uri),
            self.request.headers.get("User-Agent", ""), self.answer.mark_time()
        )
        if self.session.user is not None:
            log_record = "{} (token: {}, {}: {} {})".format(
                log_record, self.request.headers.get("X-Token"),
                self.session.user["id"], self.session.user["first_name"] or self.session.user["email"], self.session.user["last_name"] or "\b",
            )
        elif self.request.headers.get("X-Token"):
            log_record = "{} (token: {} {})".format(
                log_record, self.request.headers.get("X-Token"), "From cache" if self.cached else "\b"
            )
        return log_record

    def on_finish(self):
        """
        Выполняется после отправки ответа
        """
        log_record = self.make_log()
        if str(self.get_status()).startswith("2"):
            logging.info(log_record)
        elif str(self.get_status()).startswith("4"):
            logging.warning(log_record)
        elif str(self.get_status()).startswith("5"):
            logging.error(log_record)
        else:
            logging.info(log_record)
        Metrics.requests_per_node.inc(1)
        Metrics.requests_total.inc(cfg.app.number_of_nodes)

    def get_current_user(self):
        return dict(self.session.user)

    def valid(self, name, value, default=None, coerce=None, check=None, error=""):
        """
        Проверить значение на валидность
        :param error: текст в случае ошибки
        :param value: значение
        :param default: если значение None, то взять default
        :param coerce: привести к типу или применить функцию
        :param check: проверить функцией (должна вернуть True)
        :return: возвращает значение
        """
        if value is None:
            value = default
        if coerce and value is not None:
            try:
                value = coerce(value)
            except ValueError:
                raise ApiError("#wrong_type {}, expected {}. {}".format(name, coerce, error))
        if check and value is not None and not check(value):
            raise ApiError("#wrong_format {}. {}".format(name, error))
        return value

    def body(self, name=None, default=None, required=False, coerce=None, check=None, error=""):
        """
        Получить параметр из тела запроса с проверками
        :param name: имя параметра
        :param default: значение по умолчанию, если не нет в теле
        :param required: является ли обязательным
        :param coerce: привести к типу (можно применить функцию)
        :param check: функция проверки, должна вернуть True
        :return: возвращает значение параметра
        """
        if self.request.body:
            if self.json_body is None:
                try:
                    self.json_body = json_decode(self.request.body)
                    if not isinstance(self.json_body, (dict, list)):
                        raise JSONDecodeError("Body must be dict or list", self.json_body, 0)
                except (JSONDecodeError, UnicodeDecodeError) as e:
                    self.json_body = dict()
                    # raise ApiError("#json #parse {}".format(e))
        else:
            self.json_body = dict()

        if name:
            value = self.json_body.get(name, default)
            if required and value in (None, ""):
                # self.compose(error="#missing #field {}".format(name))
                raise ApiError("#missing #field '{}' {}".format(name, error))
            value = self.valid(name, value, default, coerce, check, error)
            return value
        else:
            return self.json_body

    def args(self, name, default=None, required=False, coerce=None, check=None, error=""):
        value = self.get_query_argument(name, default)
        if required and value in (None, ""):
            # self.compose(error="#missing #argument {}".format(name))
            raise ApiError("#missing #argument '{}' {}".format(name, error))
        value = self.valid(name, value, default, coerce, check, error)
        return value

    def write_error(self, status_code, **kwargs):
        data = dict()
        self.set_header('Content-Type', 'application/json')
        if "exc_info" in kwargs:
            data["traceback"] = list(traceback.format_exception(*kwargs["exc_info"]))
            info = {
                "log": self.make_log(),
                "token": self.request.headers.get(self.get_session_class().auth_header, "none"),
                "body": json.dumps(self.body(), sort_keys=True, indent=4, separators=(',', ': '))
            }
            data["error"] = data["traceback"][-1]
            traceback.print_exc()
            if cfg.app.send_telegram_errors:
                try:
                    TelegramReporter.telegram_error(data["traceback"], info)
                except ApiException as e:
                    try:
                        TelegramReporter.telegram_error(data["traceback"][-5:], info)
                    except ApiException as e:
                        info["body"] = "Too big body (truncated)"
                        logging.warning("Can't send telegram report: {}".format(e))
                        TelegramReporter.telegram_error(data["traceback"][-5:], info)
        if cfg.app.debug:
            self.finish(data)
        else:
            self.finish()

    def filter(self, d, allowed):
        """
        Отфильтровать словарь на допустимые значения
        :param d: словарь входящих значений
        :param allowed: список допустимых полей
        :return: dict
        """
        return {k: v for k, v in d.items() if k in allowed}

    def drop_nones(self, d, required=None):
        return {k: v for k, v in d.items() if v is not None or (required and k in required)}

    def request_hash(self, for_user=False):
        s = "{}.{}.{}.{}.{}".format(
            self.request.method,
            self.request.uri,
            self.request.headers.get("X-Token", "") if for_user else "",
            self.request.body,
            cfg.app.secret_key
        )
        hash = sha1(s.encode("utf-8"))
        return hash.hexdigest()
