#!/usr/bin/env python3
import asyncio
import csv
import json
import logging
import pkgutil
import sys
from pprint import pprint

import peewee_async
from peewee import SQL
from tqdm import tqdm

import cfg
import migrations
from managers.accesscode import AccessCodeManager
from migrations import migration001_example
from misc.functions import Synthesizer, PictureUploader, BingPictureUploader
from models import Schema, ACTUAL_VERSION, Word, WordTheme, Exercise, Sentence, connection, Rule, GrammarProficiency, \
    Goal, GoalRules


def migrate():
    """
    Функция для проверки и применения миграций.
    """
    # migration001_example.Migration()
    current_version = int(Schema.get(key="version").value)
    if current_version < ACTUAL_VERSION:
        logging.info("Schema needs to be updated {} -> {}".format(current_version, ACTUAL_VERSION))
        for loader, name, _ in pkgutil.walk_packages(migrations.__path__):
            Migration = loader.find_module(name).load_module(name).Migration

            # separate migration
            version = Schema.get(key="version")
            version.value = int(version.value)
            if version.value == Migration.version - 1 and version.value < ACTUAL_VERSION:
                connection.execute_sql("SET STATEMENT_TIMEOUT TO 60000;")
                with connection.atomic():
                    try:
                        logging.info("Updating to version {}: {}".format(Migration.version, name))
                        Migration()
                    except Exception as e:
                        logging.error("Failed on step {}: {}. "
                                      "Rolling back because of error: {}".format(Migration.version, name, e))
                        connection.rollback()
                        exit(1)
                    else:
                        version.value = Migration.version
                        version.save()

    current_version = Schema.get(key="version").value
    logging.info("Schema version is: {}".format(current_version))


def themes_fixtures():
    WordTheme.drop_table(cascade=True)
    WordTheme.create_table()
    WordTheme.create(id=1, name="General English")
    WordTheme.create(id=2, name="Travel and Tourism")
    WordTheme.create(id=3, name="Food and Drink")


def words_fixtures(filename):
    """
    Загрузить слова из csv filename
    :param filename: имя csv-файла
    """
    Word.drop_table(fail_silently=True)
    Word.create_table()
    reader = csv.reader(open(filename), delimiter=";")
    for i, line in enumerate(reader):
        if i == 0:
            continue  # заголовки
        d = {
            "text": line[0],
            "theme": line[1],
            "translation": line[2],
            "pair": line[3],
            "level": line[4],
        }
        logging.info("Word adding: {}".format(d))
        Word.create(**d)


def exercise_fixtures(filename):
    """
    Загрузить упражнения из csv filename
    :param filename: имя csv-файла
    """
    Exercise.drop_table(fail_silently=True)
    Exercise.create_table()
    reader = csv.reader(open(filename), delimiter=",")
    for i, line in enumerate(reader):
        if i == 0:
            continue  # заголовки
        d = {
            "level": line[1],
            "input": line[2],
            "output": line[3],
            "type": line[4],
            "duration": line[5],
        }
        logging.info("Exercise adding: {}".format(d))
        Exercise.create(**d)


def grammar_fixtures(filename):
    """
    Загрузить грамматические упражнения из файла
    :param filename: имя файла
    """
    Sentence.drop_table(fail_silently=True)
    Sentence.create_table()
    reader = csv.reader(open(filename), delimiter=";")
    for i, line in enumerate(reader):
        if i == 0:
            continue
        d = {
            "text": line[0],
            "translation": line[1],
            "tag": line[2],
            "rule_name": line[3],
            "pair": line[4],
        }
        if i % 1000 == 0:
            logging.info("Grammar adding: {}".format(d["text"]))
        Sentence.create(**d)


def collect_rules():
    """
    Собрать правила из таблицы грамматических упражнений и создать связи
    """
    Rule.drop_table(fail_silently=True, cascade=True)
    Rule.create_table()
    sql = """
        INSERT INTO "rule"
        ("name")
        SELECT DISTINCT("rule_name")
        from grammar
        ORDER BY "rule_name"
    """
    connection.execute_sql(sql)

    sql = """
        UPDATE "grammar"
        Set rule_id = "rule"."id"
        FROM "rule"
        WHERE rule_name = "rule"."name"
    """
    connection.execute_sql(sql)


def generate_audio():
    synthesizer = Synthesizer(voice="Penelope", rate="-0%")
    words = Word.raw("""
        select * from word
        where pair = 'en-es'
        order by text
    """).execute()
    loop = asyncio.get_event_loop()
    for word in tqdm(words, unit="words"):
        audio = loop.run_until_complete(synthesizer.synthesize(word.text))
        print(word.text, audio)
        Word.update(audio=audio).where(Word.id == word.id).execute()


def test_voices():
    synthesizer = Synthesizer(lang="es")
    words = [
        "sí",
    ]
    loop = asyncio.get_event_loop()
    for word in words:
        audio = loop.run_until_complete(synthesizer.synthesize(word))
        print(word, audio)


def generate_pics():
    uploader = PictureUploader()
    words = Word.raw("""
        select distinct on (word.text) word.text, meaning.id from word
        left join meaning on word.text = "meaning"."text"
        where meaning.id is not null and word.picture is null
    """).execute()
    for word in tqdm(words, unit="words"):
        picture = uploader.upload(word.text, word.id)
        Word.update(picture=picture).where(Word.text == word.text).execute()


def generate_pics_bing():
    uploader = BingPictureUploader()
    words = Word.raw("""
        select "text", "text" || ' ' || string_agg(translation, ' ') || ' | ' || "text" query from word where picture is null
        group by "text"
    """)
    for word in tqdm(words, unit="words"):
        picture = uploader.upload(word.text, word.query)
        print(word.query, picture.replace(" ", "%20") if picture else "", sep=", ")
        Word.update(picture=picture).where(Word.text == word.text).execute()


def add_avg_proficiency():
    proficiency = json.load(open("../files/mean_plots_data.json"))
    user_proficiency =  GrammarProficiency.raw("""
        select * from grammarproficiency where user_id = 1571
    """)
    for rule in user_proficiency:
        rule.last_history = proficiency.get(rule.rule, [])
        rule.save()


def generate_codes(count=100, source=None):
    loop = asyncio.get_event_loop()
    obj = peewee_async.Manager(connection, loop=loop)
    codes_manager = AccessCodeManager(obj)
    codes = loop.run_until_complete(codes_manager.create(count=int(count), source=source))
    for code in codes:
        print(code)


def clean_tests():
    connection.execute_sql("""
        delete from "user" where email like '%%test@parla.ai'
    """)
    print("clear")


def extract_rulenames():
    rules = {}
    rules_obj = Rule.select()
    for rule in rules_obj:
        rules[rule.id_str] = rule.name
    pprint(rules)


def generate_audio_sentences():
    logging.getLogger("boto3").setLevel(logging.ERROR)
    loop = asyncio.get_event_loop()
    synthesizer = Synthesizer(voice="Joanna", rate="")
    sentences = Sentence.raw("""
        select distinct array_to_string(translation, ' ') "text" from sentence
        where audio not like '%%Joanna%%'
        order by text
    """).execute()
    for sentence in tqdm(sentences, unit="sentences"):
        audio = loop.run_until_complete(synthesizer.synthesize(sentence.text))
        Sentence.update(audio=audio).where(SQL("array_to_string(translation, ' ') = %s", sentence.text)).execute()
        # print(sentence.text, audio)


def generate_goals(pair):
    lang = pair[-2:]
    with connection.atomic():
        try:
            Goal.raw("""
                insert into goal ("name", "type", "icon", "status", "level", "pair")
                SELECT "name", 'level', "name", 'normal', "level", %s FROM learntable;
            """, pair).execute()

            rules = Rule.raw("""
                INSERT INTO goalrules ("goal_id", "rule_id")
                SELECT goal.id "goal_id", rule.id "rule_id"
                from "rule", "goal"
                where difficulty = goal.level-1 and difficulty >= 0 AND lang = %s
                returning *
            """, lang).execute()
            if len(rules) == 0:
                raise UserWarning("No rules for this language: {}".format(lang))

            Goal.raw("""
                delete from goal where (name = 'Full Beginner' OR name = 'Native') AND type = 'level';
            """).execute()

            logging.info("Goals created. DO NOT FORGET TO LINK THEMES!")
        except UserWarning as e:
            connection.rollback()
            logging.error("Error: {}".format(e))


if __name__ == '__main__':
    _, func, *args = sys.argv
    globals()[func](*args)
    logging.info("Done")
