import urllib3
import json
import certifi
import random

from enum import Enum

str_delimiter = r'[ ,.;]'
token = None
categories = {
    9: "General Knowledge",
    10: "Entertainment: Books",
    11: "Entertainment: Film",
    12: "Entertainment: Music",
    13: "Entertainment: Musicals & Theatres",
    14: "Entertainment: Television",
    15: "Entertainment: Video Games",
    16: "Entertainment: Board Games",
    17: "Science & Nature",
    18: "Science: Computers",
    19: "Science: Mathematics",
    20: "Mythology",
    21: "Sports",
    22: "Geography",
    23: "History",
    24: "Politics",
    25: "Art",
    26: "Celebrities",
    27: "Animals",
    28: "Vehicles",
    29: "Entertainment: Comics",
    30: "Science: Gadgets",
    31: "Entertainment: Japanese Anime & Manga",
    32: "Entertainment: Cartoon & Animations"
}
get_session_token_url = 'https://opentdb.com/api_token.php?command=request'
get_question_url = 'https://opentdb.com/api.php'


def update_token():
    http = urllib3.PoolManager(
        cert_reqs='CERT_REQUIRED',
        ca_certs=certifi.where()
    )
    r = http.request('GET', get_session_token_url)
    data = json.loads(r.data)
    if 'token' in data:
        global token
        token = data['token']


def get_question(cat_ids=[]):
    global token
    fields = {
        'amount': 1
    }
    if len(cat_ids) > 0:
        fields['category'] = random.choice(cat_ids)
    if token is not None:
        fields['token'] = token
    http = urllib3.PoolManager(
        cert_reqs='CERT_REQUIRED',
        ca_certs=certifi.where()
    )
    r = http.request('GET', get_question_url, fields=fields)
    data = json.loads(r.data)
    if 'response_code' in data:
        if data['response_code'] == 0:
            question = TriviaQuestion(
                category=data['results'][0]['category'],
                type=data['results'][0]['type'],
                difficulty=data['results'][0]['difficulty'],
                question=data['results'][0]['question'],
                answers=data['results'][0]['incorrect_answers'] + [data['results'][0]['correct_answer']],
                correct_answer=data['results'][0]['correct_answer']
            )
            return question
        elif data['response_code'] in [3,4]:
            token = None
    return None


def find_categories(name):
    return word_search(name, categories)


def word_search(needle, haystack):
    if type(haystack) is list:
        haystack = dict(enumerate(haystack))
    matches = {}
    import re
    words = list(filter(None, re.split(str_delimiter, str(needle))))
    for key in haystack:
        item_words = list(filter(None, re.split(str_delimiter, str(haystack[key]))))
        if key not in matches:
            matches[key] = {'words': 0, 'order': 0}
        last_match_position = 0
        if needle.lower() == haystack[key].lower():
            matches[key] = {'words': 1000, 'order': 1000}
            break
        for word in words:
            i = 1
            for item_word in item_words:
                if word.lower() in item_word.lower():
                    matches[key]['words'] += 1
                    if i > last_match_position:
                        matches[key]['order'] += 1
                    last_match_position = i
                    break
                i += 1
    sorted_matches = sorted(matches.items(), key=lambda x: x[1]['words'] + x[1]['order'], reverse=True)
    result = []
    best = sorted_matches[0][1]
    if best['words'] > 0:
        for match in sorted_matches:
            if match[1]['words'] >= best['words']:
                result.append(match[0])
    return result


class QuestionType(Enum):
    unknown = 0
    boolean = 1
    multiple = 2


class QuestionDifficulty(Enum):
    unknown = 0
    easy = 1
    medium = 2
    hard = 3

    def __str__(self):
        return self.name.capitalize()


class TriviaQuestion:
    __slots__ = ['category', 'type', 'difficulty', 'question', 'answers', 'correct_answer']

    def __init__(self, **kwargs):
        self.category = kwargs['category']
        if kwargs['type'] == 'boolean':
            self.type = QuestionType.boolean
        elif kwargs['type'] == 'multiple':
            self.type = QuestionType.multiple
        else:
            self.type = QuestionType.unknown
        if kwargs['difficulty'] == 'easy':
            self.difficulty = QuestionDifficulty.easy
        elif kwargs['difficulty'] == 'medium':
            self.difficulty = QuestionDifficulty.medium
        elif kwargs['difficulty'] == 'hard':
            self.difficulty = QuestionDifficulty.hard
        else:
            self.difficulty = QuestionDifficulty.unknown
        from html import unescape
        self.question = unescape(kwargs['question'])
        random.shuffle(kwargs['answers'])
        self.answers = []
        for answer in kwargs['answers']:
            self.answers.append(unescape(answer))
        self.correct_answer = unescape(kwargs['correct_answer'])

    def is_correct_answer(self, answer):
        answers = word_search(answer, self.answers)
        if len(answers) > 0 and self.answers[answers[0]] == self.correct_answer:
            return True
        else:
            return False

    def __str__(self):
        result = ''
        for slot in self.__slots__:
            result += '%s = ' % slot + str(getattr(self, slot)) + '\n'
        return result

update_token()