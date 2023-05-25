# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb.

# %% auto 0
__all__ = ['JAVA_MIN_VERSION', 'NLP_URL', 'NLP_DIR_NAME', 'CURR_DIR', 'NLP_DIR_PATH', 'JAVA_DOWNLOADER', 'INSTALLATION_PATH',
           'STANFORD_ZIP_GOOGLE_DRIVE_ID', 'STANFORD_ZIP_NAME', 'STANFORD_ZIP_PATH', 'logger', 'CoreNLPEngine',
           'Tokenize', 'SSplit', 'POS', 'Lemma', 'NER', 'EntityMentions', 'RGXNer', 'TokensRegex', 'CleanXML', 'Parse',
           'DepParse', 'Coref', 'OpenIE', 'KBP', 'Quote', 'Sentiment', 'TrueCase', 'UDFeats', 'tokenize_wrapper',
           'ssplit_wrapper', 'pos_wrapper', 'lemma_wrapper', 'ner_wrapper', 'entitymentions_wrapper',
           'regexner_wrapper', 'tokensregex_wrapper', 'cleanxml_wrapper', 'parse_wrapper', 'dependency_parse_wrapper',
           'coref_wrapper', 'openie_wrapper', 'kbp_wrapper', 'quote_wrapper', 'sentiment_wrapper', 'truecase_wrapper',
           'udfeats_wrapper']

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 4
import json
import logging
from io import BytesIO
from os import popen
from pathlib import Path
from typing import Iterator
from zipfile import ZipFile
import os

import jdk
from spanner_nlp.StanfordCoreNLP import StanfordCoreNLP

from spanner_workbench.src.rgxlog_interpreter.src.rgxlog.engine.datatypes.primitive_types import DataTypes
from spanner_workbench.src.rgxlog_interpreter.src.rgxlog.stdlib.utils import download_file_from_google_drive

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 5
JAVA_MIN_VERSION = 1.8

NLP_URL = "https://drive.google.com/u/0/uc?export=download&id=1QixGiHD2mHKuJtB69GHDQA0wTyXtHzjl"
NLP_DIR_NAME = 'stanford-corenlp-4.1.0'
# jupyter issue solve
# CURR_DIR = Path(__file__).parent
CURR_DIR = os.getcwd()
NLP_DIR_PATH = str(Path(CURR_DIR) / NLP_DIR_NAME)

JAVA_DOWNLOADER = "install-jdk"
_USER_DIR = Path.home()
INSTALLATION_PATH = _USER_DIR / ".jre"

STANFORD_ZIP_GOOGLE_DRIVE_ID = "1QixGiHD2mHKuJtB69GHDQA0wTyXtHzjl"
STANFORD_ZIP_NAME = "stanford-corenlp-4.1.0.zip"
STANFORD_ZIP_PATH = Path(CURR_DIR) / STANFORD_ZIP_NAME

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 6
logger = logging.getLogger(__name__)

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 7
def _is_installed_nlp() -> bool:
    return Path(NLP_DIR_PATH).is_dir()

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 8
def _install_nlp() -> None:
    logger.info(f"Installing {NLP_DIR_NAME} into {CURR_DIR}.")

    if not STANFORD_ZIP_PATH.is_file():
        logger.info(f"downloading {STANFORD_ZIP_NAME}...")
        download_file_from_google_drive(STANFORD_ZIP_GOOGLE_DRIVE_ID, STANFORD_ZIP_PATH)
    print(STANFORD_ZIP_PATH)
    with open(STANFORD_ZIP_PATH, "rb") as zipresp:
        with ZipFile(BytesIO(zipresp.read())) as zfile:
            logging.info(f"Extracting files from the zip folder...")
            zfile.extractall(CURR_DIR)

    logging.info("installation completed.")

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 9
def _is_installed_java() -> bool:
    version = popen(
        "java -version 2>&1 | grep 'version' 2>&1 | awk -F\\\" '{ split($2,a,\".\"); print a[1]\".\"a[2]}'").read()

    if len(version) != 0 and float(version) >= JAVA_MIN_VERSION:
        return True

    return Path(INSTALLATION_PATH).is_dir()

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 10
def _run_installation() -> None:
    if not _is_installed_nlp():
        print("HERE")
        _install_nlp()
        assert _is_installed_nlp()
    if not _is_installed_java():
        print("THERE")
        logging.info(f"Installing JRE into {INSTALLATION_PATH}.")
        jdk.install('8', jre=True)
        if _is_installed_java():
            logging.info("installation completed.")
        else:
            raise IOError("installation failed")

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 11
_run_installation()
CoreNLPEngine = StanfordCoreNLP(NLP_DIR_PATH)

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 12
def tokenize_wrapper(sentence: str) -> Iterator:
    for token in CoreNLPEngine.tokenize(sentence):
        yield token["token"], token["span"]

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 13
Tokenize = dict(ie_function=tokenize_wrapper,
                ie_function_name='Tokenize',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.span])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 14
def ssplit_wrapper(sentence: str) -> Iterator:
    for s in CoreNLPEngine.ssplit(sentence):
        yield s,

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 15
SSplit = dict(ie_function=ssplit_wrapper,
              ie_function_name='SSplit',
              in_rel=[DataTypes.string],
              out_rel=[DataTypes.string])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 16
def pos_wrapper(sentence: str) -> Iterator:
    for res in CoreNLPEngine.pos(sentence):
        yield res["token"], res["pos"], res["span"]

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 17
POS = dict(ie_function=pos_wrapper,
           ie_function_name='POS',
           in_rel=[DataTypes.string],
           out_rel=[DataTypes.string, DataTypes.string, DataTypes.span])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 18
def lemma_wrapper(sentence: str) -> Iterator:
    for res in CoreNLPEngine.lemma(sentence):
        yield res["token"], res["lemma"], res["span"]

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 19
Lemma = dict(ie_function=lemma_wrapper,
             ie_function_name='Lemma',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.string, DataTypes.string, DataTypes.span])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 20
def ner_wrapper(sentence: str) -> Iterator:
    for res in CoreNLPEngine.ner(sentence):
        if res["ner"] != 'O':
            yield res["token"], res["ner"], res["span"]

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 21
NER = dict(ie_function=ner_wrapper,
           ie_function_name='NER',
           in_rel=[DataTypes.string],
           out_rel=[DataTypes.string, DataTypes.string, DataTypes.span])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 22
def entitymentions_wrapper(sentence: str) -> Iterator:
    for res in CoreNLPEngine.entitymentions(sentence):
        confidence = json.dumps(res["nerConfidences"]).replace("\"", "'")
        yield (res["docTokenBegin"], res["docTokenEnd"], res["tokenBegin"], res["tokenEnd"], res["text"],
               res["characterOffsetBegin"], res["characterOffsetEnd"], res["ner"], confidence)

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 23
EntityMentions = dict(ie_function=entitymentions_wrapper,
                      ie_function_name='EntityMentions',
                      in_rel=[DataTypes.string],
                      out_rel=[DataTypes.integer, DataTypes.integer, DataTypes.integer, DataTypes.integer,
                               DataTypes.string, DataTypes.integer, DataTypes.integer, DataTypes.string,
                               DataTypes.string])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 24
def regexner_wrapper(sentence: str, pattern: str) -> Iterator:
    # for res in CoreNLPEngine.regexner(sentence, pattern):
    raise NotImplementedError()

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 25
RGXNer = dict(ie_function=regexner_wrapper,
              ie_function_name='RGXNer',
              in_rel=[DataTypes.string, DataTypes.string],
              out_rel=None)

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 26
def tokensregex_wrapper(sentence: str, pattern: str) -> Iterator:
    # for res in CoreNLPEngine.tokensregex(sentence, pattern):
    raise NotImplementedError()

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 27
TokensRegex = dict(ie_function=tokensregex_wrapper,
                   ie_function_name='TokensRegex',
                   in_rel=[DataTypes.string, DataTypes.string],
                   out_rel=None)

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 28
def cleanxml_wrapper(sentence: str) -> Iterator:
    for res in CoreNLPEngine.cleanxml(sentence)["tokens"]:
        yield res['index'], res['word'], res['originalText'], res['characterOffsetBegin'], res['characterOffsetEnd']

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 29
CleanXML = dict(ie_function=cleanxml_wrapper,
                ie_function_name='CleanXML',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.integer, DataTypes.string, DataTypes.string, DataTypes.integer, DataTypes.integer])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 30
def parse_wrapper(sentence: str) -> Iterator:
    for res in CoreNLPEngine.parse(sentence):
        # note #1: this yields a tuple
        # note #2: we replace the newlines with `<nl> because it is difficult to tell the results apart otherwise
        yield res.replace("\n", "<nl>").replace("\r", ""),

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 31
Parse = dict(ie_function=parse_wrapper,
             ie_function_name='Parse',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.string])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 32
def dependency_parse_wrapper(sentence: str) -> Iterator:
    for res in CoreNLPEngine.dependency_parse(sentence):
        yield res['dep'], res['governor'], res['governorGloss'], res['dependent'], res['dependentGloss']

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 33
DepParse = dict(ie_function=dependency_parse_wrapper,
                ie_function_name='DepParse',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.integer, DataTypes.string, DataTypes.integer, DataTypes.string])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 34
def coref_wrapper(sentence: str) -> Iterator:
    for res in CoreNLPEngine.coref(sentence):
        yield (res['id'], res['text'], res['type'], res['number'], res['gender'], res['animacy'], res['startIndex'],
               res['endIndex'], res['headIndex'], res['sentNum'],
               tuple(res['position']), str(res['isRepresentativeMention']))

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 35
Coref = dict(ie_function=coref_wrapper,
             ie_function_name='Coref',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.integer, DataTypes.string, DataTypes.string, DataTypes.string, DataTypes.string,
                      DataTypes.string, DataTypes.integer, DataTypes.integer, DataTypes.integer, DataTypes.integer,
                      DataTypes.span, DataTypes.string])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 36
def openie_wrapper(sentence: str) -> Iterator:
    for lst in CoreNLPEngine.openie(sentence):
        for res in lst:
            yield (res['subject'], tuple(res['subjectSpan']), res['relation'], tuple(res['relationSpan']),
                   res['object'], tuple(res['objectSpan']))

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 37
OpenIE = dict(ie_function=openie_wrapper,
              ie_function_name='OpenIE',
              in_rel=[DataTypes.string],
              out_rel=[DataTypes.string, DataTypes.span, DataTypes.string, DataTypes.span, DataTypes.string,
                       DataTypes.span])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 38
def kbp_wrapper(sentence: str) -> Iterator:
    for lst in CoreNLPEngine.kbp(sentence):
        for res in lst:
            yield (res['subject'], tuple(res['subjectSpan']), res['relation'], tuple(res['relationSpan']),
                   res['object'], tuple(res['objectSpan']))

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 39
KBP = dict(ie_function=kbp_wrapper,
           ie_function_name='KBP',
           in_rel=[DataTypes.string],
           out_rel=[DataTypes.string, DataTypes.span, DataTypes.string, DataTypes.span, DataTypes.string,
                    DataTypes.span])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 40
def quote_wrapper(sentence: str) -> Iterator:
    for res in CoreNLPEngine.quote(sentence):
        yield (res['id'], res['text'], res['beginIndex'], res['endIndex'], res['beginToken'], res['endToken'],
               res['beginSentence'], res['endSentence'], res['speaker'], res['canonicalSpeaker'])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 41
Quote = dict(ie_function=quote_wrapper,
             ie_function_name='Quote',
             in_rel=[DataTypes.string],
             out_rel=[DataTypes.integer, DataTypes.string, DataTypes.integer, DataTypes.integer, DataTypes.integer,
                      DataTypes.integer, DataTypes.integer, DataTypes.integer, DataTypes.string, DataTypes.string])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 42
# currently ignoring sentimentTree
def sentiment_wrapper(sentence: str) -> Iterator:
    for res in CoreNLPEngine.sentiment(sentence):
        yield int(res['sentimentValue']), res['sentiment'], json.dumps(res['sentimentDistribution'])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 43
Sentiment = dict(ie_function=sentiment_wrapper,
                 ie_function_name='Sentiment',
                 in_rel=[DataTypes.string],
                 out_rel=[DataTypes.integer, DataTypes.string, DataTypes.string])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 44
def truecase_wrapper(sentence: str) -> Iterator:
    for res in CoreNLPEngine.truecase(sentence):
        yield res['token'], res['span'], res['truecase'], res['truecaseText']

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 45
TrueCase = dict(ie_function=truecase_wrapper,
                ie_function_name='TrueCase',
                in_rel=[DataTypes.string],
                out_rel=[DataTypes.string, DataTypes.span, DataTypes.string, DataTypes.string])

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 46
def udfeats_wrapper(sentence: str) -> Iterator:
    # for token in CoreNLPEngine.udfeats(sentence):
    raise NotImplementedError()

# %% ../../../../../../nbs/15_src.rgxlog_interpreter.src.rgxlog.stdlib.nlp.ipynb 47
UDFeats = dict(ie_function=udfeats_wrapper,
               ie_function_name='UDFeats',
               in_rel=[DataTypes.string],
               out_rel=None)
