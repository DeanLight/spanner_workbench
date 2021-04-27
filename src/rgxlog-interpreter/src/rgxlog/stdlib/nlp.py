import json
from io import BytesIO
from os import path
from os import popen
from urllib.request import urlopen
from zipfile import ZipFile

import jdk
import spacy

from rgxlog.engine.datatypes.primitive_types import DataTypes
from rgxlog.stdlib.StanfordCoreNLP import StanfordCoreNLP

sp = spacy.load('en_core_web_sm')

MIN_VERSION = 1.8

NLP_URL = "http://nlp.stanford.edu/software/stanford-corenlp-4.1.0.zip"

NLP_DIR_NAME = 'stanford-corenlp-4.1.0'
CURR_DIR = path.dirname(__file__)
NLP_DIR_PATH = f"{CURR_DIR}/{NLP_DIR_NAME}"

JAVA_DOWNLOADER = "install-jdk"
_USER_DIR = path.expanduser("~")
ISTALLATION_PATH = f"{_USER_DIR}/.jre"


def _is_installed_nlp():
    return path.isdir(NLP_DIR_PATH)


def _install_nlp():
    with urlopen(NLP_URL) as zipresp:
        with ZipFile(BytesIO(zipresp.read())) as zfile:
            zfile.extractall(CURR_DIR)


def _is_installed_java():
    version = popen(
        "java -version 2>&1 | grep 'version' 2>&1 | awk -F\\\" '{ split($2,a,\".\"); print a[1]\".\"a[2]}'").read()

    if len(version) != 0 and float(version) >= MIN_VERSION:
        return True

    return path.isdir(ISTALLATION_PATH)


def _run_installation():
    if not _is_installed_nlp():
        _install_nlp()
        assert _is_installed_nlp()
    if not _is_installed_java():
        jdk.install('8', jre=True)
        assert _is_installed_java()


_run_installation()

# you were instantiating and killing a java runtime at each run of the function
CoreNLPEngine = StanfordCoreNLP(NLP_DIR_PATH)
" ******************************************************************************************************************** "


def tokenize_wrapper(sentence: str):
    _run_installation()
    with CoreNLPEngine as nlp:
        for token in nlp.tokenize(sentence):
            yield token["token"], token["span"]


Tokenize = dict(ie_function=tokenize_wrapper,
                ie_function_name='Tokenize',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.span],
                )

" ******************************************************************************************************************** "


def ssplit_wrapper(sentence):
    _run_installation()
    with CoreNLPEngine as nlp:
        for s in nlp.ssplit(sentence):
            yield s,


SSplit = dict(ie_function=ssplit_wrapper,
              ie_function_name='SSplit',
              in_rel=[DataTypes.string],
              out_rel=[DataTypes.string],
              )

" ******************************************************************************************************************** "


def pos_wrapper(sentence):
    _run_installation()
    with CoreNLPEngine as nlp:
        for res in nlp.pos(sentence):
            yield res["token"], res["pos"], res["span"]


POS = dict(ie_function=pos_wrapper,
           ie_function_name='POS',
           in_rel=[DataTypes.string],
           out_rel=[DataTypes.string, DataTypes.string, DataTypes.span],
           )

" ******************************************************************************************************************** "


def lemma_wrapper(sentence):
    with CoreNLPEngine as nlp:
        for res in nlp.lemma(sentence):
            yield res["token"], res["lemma"], res["span"]


Lemma = dict(ie_function=lemma_wrapper,
             ie_function_name='Lemma',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.string, DataTypes.string, DataTypes.span],
             )

" ******************************************************************************************************************** "


def ner_wrapper(sentence):
    with CoreNLPEngine as nlp:
        for res in nlp.ner(sentence):
            if res["ner"] != 'O':
                yield res["token"], res["ner"], res["span"]


NER = dict(ie_function=ner_wrapper,
           ie_function_name='NER',
           in_rel=[DataTypes.string],
           out_rel=[DataTypes.string, DataTypes.string, DataTypes.span],
           )

" ******************************************************************************************************************** "


def entitymentions_wrapper(sentence):
    _run_installation()
    with CoreNLPEngine as nlp:
        for res in nlp.entitymentions(sentence):
            confidence = json.dumps(res["nerConfidences"]).replace("\"", "'")
            yield res["docTokenBegin"], res["docTokenEnd"], res["tokenBegin"], res["tokenEnd"], res["text"], \
                  res["characterOffsetBegin"], res["characterOffsetEnd"], res["ner"], confidence


EntityMentions = dict(ie_function=entitymentions_wrapper,
                      ie_function_name='EntityMentions',
                      in_rel=[DataTypes.string],
                      out_rel=[DataTypes.integer, DataTypes.integer, DataTypes.integer, DataTypes.integer,
                               DataTypes.string, DataTypes.integer, DataTypes.integer, DataTypes.string,
                               DataTypes.string]
                      )

" ******************************************************************************************************************** "


# TODO: I can't find how pattern should look like
def regexner_wrapper(sentence, pattern):
    _run_installation()
    with CoreNLPEngine as nlp:
        for res in nlp.regexner(sentence, pattern):
            raise NotImplementedError()


RGXNer = dict(ie_function=regexner_wrapper,
              ie_function_name='RGXNer',
              in_rel=[DataTypes.string, DataTypes.string],
              out_rel=None
              )

" ******************************************************************************************************************** "


# TODO: I can't find how pattern should look like
def tokensregex_wrapper(sentence, pattern):
    _run_installation()
    with CoreNLPEngine as nlp:
        for res in nlp.tokensregex(sentence, pattern):
            raise NotImplementedError()


TokensRegex = dict(ie_function=tokensregex_wrapper,
                   ie_function_name='TokensRegex',
                   in_rel=[DataTypes.string, DataTypes.string],
                   out_rel=None
                   )

" ******************************************************************************************************************** "


def cleanxml_wrapper(sentence):
    _run_installation()
    with CoreNLPEngine as nlp:
        for res in nlp.cleanxml(sentence)["tokens"]:
            yield res['index'], res['word'], res['originalText'], res['characterOffsetBegin'], res['characterOffsetEnd']


CleanXML = dict(ie_function=cleanxml_wrapper,
                ie_function_name='CleanXML',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.integer, DataTypes.string, DataTypes.string, DataTypes.integer, DataTypes.integer]
                )

" ******************************************************************************************************************** "


def parse_wrapper(sentence):
    _run_installation()
    with CoreNLPEngine as nlp:
        for res in nlp.parse(sentence):
            yield res.replace("\n", "<nl>").replace("\r",
                                                    ""),  # pyDatalog doesn't allow '\n' inside a string, <nl> represents new-line


Parse = dict(ie_function=parse_wrapper,
             ie_function_name='Parse',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.string]
             )

" ******************************************************************************************************************** "


def dependency_parse_wrapper(sentence):
    _run_installation()
    with CoreNLPEngine as nlp:
        for res in nlp.dependency_parse(sentence):
            yield res['dep'], res['governor'], res['governorGloss'], res['dependent'], res['dependentGloss']


DepParse = dict(ie_function=dependency_parse_wrapper,
                ie_function_name='DepParse',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.integer, DataTypes.string, DataTypes.integer, DataTypes.string]
                )

" ******************************************************************************************************************** "


def coref_wrapper(sentence):
    _run_installation()
    with CoreNLPEngine as nlp:
        for res in nlp.coref(sentence):
            yield res['id'], res['text'], res['type'], res['number'], res['gender'], res['animacy'], res['startIndex'], \
                  res['endIndex'], res['headIndex'], res['sentNum'], \
                  tuple(res['position']), str(res['isRepresentativeMention'])


Coref = dict(ie_function=coref_wrapper,
             ie_function_name='Coref',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.integer, DataTypes.string, DataTypes.string, DataTypes.string, DataTypes.string,
                      DataTypes.string, DataTypes.integer, DataTypes.integer, DataTypes.integer, DataTypes.integer,
                      DataTypes.span, DataTypes.string]
             )

" ******************************************************************************************************************** "


def openie_wrapper(sentence):
    _run_installation()
    with CoreNLPEngine as nlp:
        for lst in nlp.openie(sentence):
            for res in lst:
                yield res['subject'], tuple(res['subjectSpan']), res['relation'], tuple(res['relationSpan']), \
                      res['object'], tuple(res['objectSpan'])


OpenIE = dict(ie_function=openie_wrapper,
              ie_function_name='OpenIE',
              in_rel=[DataTypes.string],
              out_rel=[DataTypes.string, DataTypes.span, DataTypes.string, DataTypes.span, DataTypes.string,
                       DataTypes.span]
              )

" ******************************************************************************************************************** "


def kbp_wrapper(sentence):
    _run_installation()
    with CoreNLPEngine as nlp:
        for lst in nlp.kbp(sentence):
            for res in lst:
                yield res['subject'], tuple(res['subjectSpan']), res['relation'], tuple(res['relationSpan']), \
                      res['object'], tuple(res['objectSpan'])


KBP = dict(ie_function=kbp_wrapper,
           ie_function_name='KBP',
           in_rel=[DataTypes.string],
           out_rel=[DataTypes.string, DataTypes.span, DataTypes.string, DataTypes.span, DataTypes.string,
                    DataTypes.span]
           )

" ******************************************************************************************************************** "


# doesn't works because regexlog parser doesn't support strings such as "\"hello\"" (with escapes)
def quote_wrapper(sentence):
    _run_installation()
    with CoreNLPEngine as nlp:
        for res in nlp.quote(sentence):
            yield res['id'], res['text'], res['beginIndex'], res['endIndex'], res['beginToken'], res['endToken'],
            res['beginSentence'], res['endSentence'], res['speaker'], res['canonicalSpeaker']


Quote = dict(ie_function=quote_wrapper,
             ie_function_name='Quote',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.integer, DataTypes.string, DataTypes.integer, DataTypes.integer, DataTypes.integer,
                      DataTypes.integer, DataTypes.integer, DataTypes.integer, DataTypes.string, DataTypes.string]
             )

" ******************************************************************************************************************** "


# currently ignoring sentimentTree
def sentiment_wrapper(sentence):
    _run_installation()
    with CoreNLPEngine as nlp:
        for res in nlp.sentiment(sentence):
            yield int(res['sentimentValue']), res['sentiment'], json.dumps(res['sentimentDistribution'])


Sentiment = dict(ie_function=sentiment_wrapper,
                 ie_function_name='Sentiment',
                 in_rel=[DataTypes.string],
                 out_rel=[DataTypes.integer, DataTypes.string, DataTypes.string]
                 )

" ******************************************************************************************************************** "


def truecase_wrapper(sentence):
    _run_installation()
    with CoreNLPEngine as nlp:
        for res in nlp.truecase(sentence):
            yield res['token'], res['span'], res['truecase'], res['truecaseText']


TrueCase = dict(ie_function=truecase_wrapper,
                ie_function_name='TrueCase',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.span, DataTypes.string, DataTypes.string]
                )

" ******************************************************************************************************************** "


# I don't understand the schema (list of dicts with values of list)
def udfeats_wrapper(sentence: str):
    _run_installation()
    with CoreNLPEngine as nlp:
        for token in nlp.udfeats(sentence):
            raise NotImplementedError()


UDFeats = dict(ie_function=udfeats_wrapper,
               ie_function_name='UDFeats',
               in_rel=[DataTypes.string],
               out_rel=None,
               )

" ******************************************************************************************************************** "


def entities(text):
    ent = sp(text).ents
    return ((entity.text, spacy.explain(entity.label_)) for entity in ent)


Entities = dict(ie_function=entities,
                ie_function_name='Entities',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.string]
                )

" ******************************************************************************************************************** "
