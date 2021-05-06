import glob
import logging
import os
import re
import socket
import subprocess
import sys
import time
import psutil
import requests

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


class StanfordCoreNLP(object):
    def __init__(self, localDirOrURLServer, port=None, memory='2g', lang='en', timeout=1500, quiet=True,
                 loggingLevel=logging.WARNING, maxRetries=5):
        """
        The Constructor for StanfordCoreNLP class.

        Parameters
        ----------
        localDirOrURLServer : string
            The path for the CoreNLP Information.
            The localDirOrURLServer can be local files or existing server.
            For example:
            Local files can be the latest version that downloaded from from the StanfordCoreNLP
            website as a folder - "stanford-corenlp-4.1.0"
            Existing server can be - "http://corenlp.run"
        port : int
            The port used in for the CoreNLP Java server that communicates with the python client.
            The port is an integer value between 9000 to 65535. In case this value is none, then
            an available value will be selected automatically.
            default value is None.
            When using local files a port number will be selected in order to communicate with
            the CoreNLP Java server.
            When using existing server such as - "http://corenlp.run", the port number must be 80.
        memory : string
            The memory requirements of the CoreNLP server.
            This is a string that represents the memory allocation value.
            default value is 4g.
            The values can be '4g', '8g' etc.
        lang : string
            A string that represents the Language type.
            default value is en (English).
            The Languages available are English(en), Chinese(zh), Arabic(ar),
            French(fr), German(de) and Spanish(es).
        timeout : int
            An integer that represents the Run time of the server.
            default value is 1500.
        quiet : Boolean
            A Boolean that Checks where to redirect the standard output
            (if True to a file (/dev/null) (hide output) or if False to regular stdout).
            default value is True.
        loggingLevel : logging
            A value that represents the logging level in the system (used for debug).
            default value is logging.debug.
        maxRetries : int
            An integer that represents the Maximum amount of retries to wait for a server.
            default value is 5.
        """

        self.localDirOrURLServer = localDirOrURLServer  # The path for the CoreNLP in formation. Can be local files or server.
        self.port = port  # Port value
        self.memory = memory  # Memory allocation value
        self.lang = lang  # Language type
        self.timeout = timeout  # Run time of the server
        self.quiet = quiet  # Checks where to redirect the standard output (file (/dev/null) or regular stdout)
        self.loggingLevel = loggingLevel  # Logging level for debug
        self.maxRetries = maxRetries  # Maximum amount of retries to wait for a server
        self.pathDir = None  # Path directory
        # Create CoreNLP
        logging.basicConfig(level=self.loggingLevel)  # Get logging level for debug
        self.checkLanguage()  # Check if Language is valid
        self.checkMemory()  # Check if Memory is valid
        # In case we use a server
        if urlparse(self.localDirOrURLServer).netloc:
            self.url = f"{self.localDirOrURLServer}:{self.port}"
            logging.debug('Using an existing server {}'.format(self.url))
        else:  # In case we use local files
            # Check if Java available
            if not subprocess.call(['java', '-version'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT) == 0:
                raise RuntimeError('Java not found.')
            self.checkLocalDirValue()  # Check if localDirOrURLServer is valid
            self.checkPort()  # Check if Port is valid
            self.createLocalServer()  # Create Native Server
        self.startServer()  # start Server

    def checkMemory(self):
        """
        Check if the Memory allocation is supported in the StanfordCoreNLPServer.
        """

        if not re.match('\dg', self.memory):
            raise ValueError('memory = ' + self.memory + ' not supported. Use 4g, 6g, 8g and etc. ')

    def checkLanguage(self):
        """
        Check if the Language is supported in the StanfordCoreNLPServer.
        """

        if self.lang not in ['en', 'zh', 'ar', 'fr', 'de', 'es']:
            raise ValueError('lang = ' + lang + ' not supported. Use English(en), Chinese(zh), Arabic(ar), '
                                                'French(fr), German(de) or Spanish(es).')

    def checkLocalDirValue(self):
        """
        Check if the local directory and files exist.
        """

        # Check if the local directory exists
        if not os.path.isdir(self.localDirOrURLServer):
            raise IOError(str(self.localDirOrURLServer) + ' is not a directory.')
        directory = os.path.normpath(self.localDirOrURLServer) + os.sep
        self.pathDir = directory
        # Language information
        languageFiles = {
            'en': 'stanford-corenlp-[0-9].[0-9].[0-9]-models.jar',
            'zh': 'stanford-chinese-corenlp-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-models.jar',
            'ar': 'stanford-arabic-corenlp-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-models.jar',
            'fr': 'stanford-french-corenlp-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-models.jar',
            'de': 'stanford-german-corenlp-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-models.jar',
            'es': 'stanford-spanish-corenlp-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-models.jar'
        }
        jars = {
            'en': 'stanford-corenlp-x.x.x-models.jar',
            'zh': 'stanford-chinese-corenlp-yyyy-MM-dd-models.jar',
            'ar': 'stanford-arabic-corenlp-yyyy-MM-dd-models.jar',
            'fr': 'stanford-french-corenlp-yyyy-MM-dd-models.jar',
            'de': 'stanford-german-corenlp-yyyy-MM-dd-models.jar',
            'es': 'stanford-spanish-corenlp-yyyy-MM-dd-models.jar'
        }
        # Check if the current language specific model file exists
        if len(glob.glob(directory + languageFiles.get(self.lang))) <= 0:
            raise IOError(
                jars.get(self.lang) + ' not exists. You should download and place it in the ' + directory + ' first.')

    def checkPort(self):
        """
        Check the port information and allocates new port value in case of need.
        """

        # Auto select new port value, In case port was not allocated
        if self.port is None:
            for newPortValue in range(9000, 65535):
                if newPortValue not in [conn.laddr[1] for conn in psutil.net_connections()]:
                    self.port = newPortValue
                    break
        # If the port already selected, we check if the port is in use
        if self.port in [conn.laddr[1] for conn in psutil.net_connections()]:
            raise IOError('Port ' + str(self.port) + ' is already in use.')

    def createLocalServer(self):
        """
        Creates new server in order to communicate with the CoreNLP.
        """

        logging.debug('Initializing native server...')  # Used for debug
        # Gets the information to create the server
        cmd = "java"
        javaArgs = "-Xmx{}".format(self.memory)
        javaClass = "edu.stanford.nlp.pipeline.StanfordCoreNLPServer"
        classPath = '"{}*"'.format(self.pathDir)
        args = f"{cmd} {javaArgs} -cp {classPath} {javaClass} -port {str(self.port)} timeout {str(self.timeout)}"
        logging.debug(args)  # Used for debug
        # Checks where to redirect the standard output (file (/dev/null) or regular stdout)
        with open(os.devnull, 'w') as nullFile:
            outFile = None
            if self.quiet:
                outFile = nullFile
            # Create the sub process that run the Java server
            self.p = subprocess.Popen(args, shell=True, stdout=outFile, stderr=subprocess.STDOUT)
            logging.debug('Server shell PID: {}'.format(self.p.pid))  # Used for debug
        self.url = 'http://localhost:' + str(self.port)

    def startServer(self):
        """
        Creates a communicate with the StanfordCoreNLPServer.
        """

        # Create server connection using socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        hostName = urlparse(self.url).hostname
        time.sleep(1)
        trial = 1
        # Tries to connect to the server
        while sock.connect_ex((hostName, self.port)):
            # In case connection fails
            if trial > self.maxRetries:
                raise ValueError('Corenlp server is not available')
            logging.debug('Waiting until the server is available.')  # Used for debug
            trial += 1
            time.sleep(1)
        logging.debug('The server is available.')  # Used for debug

    def __enter__(self):
        """
        This method allow to implement objects which can be used easily with the with statement.
        """

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        This method allow to implement objects which can be used easily with the with statement.
        pass
        """
    
    def __del__(self, exc_type, exc_val, exc_tb):
        """
        This method allow to implement objects which can be used easily with the with statement.
        """

        self.close()

    def close(self):
        """
        This method kills all the child process that created during the run in order
        to cleanup unnecessary values at the end of the run.
        """

        logging.debug('Cleanup...')  # Used for debug
        if hasattr(self, 'p'):
            try:
                parent = psutil.Process(self.p.pid)
            except psutil.NoSuchProcess:
                logging.debug('No process: {}'.format(self.p.pid))
                return
            if self.pathDir not in ' '.join(parent.cmdline()):
                logging.debug('Process not in: {}'.format(parent.cmdline()))
                return
            children = parent.children(recursive=True)
            # Killing all the child process that created during the run
            for process in children:
                # Used for debug
                logging.debug('Killing pid: {}, cmdline: {}'.format(process.pid, process.cmdline()))
                process.kill()
            # Used for debug
            logging.debug('Killing shell pid: {}, cmdline: {}'.format(parent.pid, parent.cmdline()))
            parent.kill()

    def getDataForAnnotatorsWrapper(self, url, annotators, textValue, *args, **kwargs):
        """
        This is a wrapper for the fixed Annotators.

        Parameters
        ----------
        url : string
            A string value that represents the url for the local files or the sever.
        annotators : string
            A string value that represents the annotators we want to see.
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).
        *args : argument list
            Used to send a non-keyworded variable length argument list to the function.
        **kwargs : argument list
            Allows you to pass keyworded variable length of arguments to a function.

        Returns
        -------
        JSON
            A value that represents every value propertie in the given textValue.
        """

        # In case we need to encode text
        if sys.version_info.major >= 3:
            textValue = textValue.encode('utf-8')
        properties = {'annotators': annotators, 'outputFormat': 'JSON'}
        params = {'properties': str(properties), 'pipelineLanguage': self.lang}
        # Check to see if we need to look for a pattern in a certain annotator
        # Used for TokensRegexNER, TokensRegex, Tregex and Semgrex Annotators
        if 'patternValue' in kwargs:
            params = {'pattern': kwargs['patternValue'], 'properties': str(properties),
                      'pipelineLanguage': self.lang, 'filter': kwargs['filterValue']}
        logging.debug(params)  # Add information to debug
        # Get requested value from server
        requestedDictValue = requests.post(url, params=params, data=textValue,
                                           headers={'Connection': 'close'}, timeout=self.timeout)
        requestedDictValue.raise_for_status()
        return requestedDictValue.json()

    def annotate(self, textValue, properties, multiAnnotator=False):
        """
        This is a wrapper for the Manual Annotators.
        Can be used in order to get mixed information from the textValue.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).
        properties : dict
            A value in the format:
            {'annotators' : value, 'pinelineLanguage' : value, 'outputFormat' : value}
        multiAnnotator : boolean
            If True, the return value will be separated for each annotator.
            default is False.

        Returns
        -------
        Dictionary List
            A value that represents every value propertie in the given textValue.
            If multiAnnotator is True, the return value will be separated for
            each annotator.
        """

        # In case we need to encode text
        if sys.version_info.major >= 3:
            textValue = textValue.encode('utf-8')
        annotatorsType = properties['annotators']
        if multiAnnotator:
            properties['annotators'] = annotatorsType + ' ,ssplit'  # Add 'ssplit' to rearrange the data for output
        # Get requested value from server
        requestedDictValue = requests.post(self.url, params={'properties': str(properties)}, data=textValue,
                                           headers={'Connection': 'close'}, timeout=self.timeout)
        requestedDictValue.raise_for_status()
        if multiAnnotator:  # Get a list of separated Annotators Value
            return self.getAnnotatorsValueDict(requestedDictValue.json(), annotatorsType)
        else:  # Get the full data of the Annotators
            return requestedDictValue.text

    def getAnnotatorsValueDict(self, requestedDictValue, annotatorsType):
        """
        This is a wrapper for the Manual Annotators.
        Can be used in order to get mixed information from the textValue.

        Parameters
        ----------
        requestedDictValue : JSON
            A value that represents every value propertie in the given text
            that filtered by the annotators.
        annotatorsType : string
            A string that represents every annotators used to create requestedDictValue.

        Returns
        -------
        Dictionary
            A value that represents every value propertie that will be separated for
            each annotator.
        """

        dictValue = {}
        if 'tokenize' in annotatorsType:
            returnDictList = []
            # Go through all the tokens in each sentence in order to get the tokens
            for s in requestedDictValue['sentences']:
                for token in s['tokens']:
                    returnDict = {}
                    returnDict['token'] = token['originalText']
                    returnDict['span'] = (token['characterOffsetBegin'], token['characterOffsetEnd'])
                    returnDictList.append(returnDict)
            dictValue['tokenize'] = returnDictList
        if 'cleanxml' in annotatorsType:
            dictValue['cleanxml'] = requestedDictValue
        if 'ssplit' in annotatorsType:
            # Get all the tokens for each sentence
            tokens = [s for s in requestedDictValue['sentences']]
            sentences = []
            # Go through all the tokens in each sentence and combine them
            for s in range(len(tokens)):
                sentences.append(' '.join([token['originalText'] for token in tokens[s]['tokens']]))
            dictValue['ssplit'] = sentences
        if 'pos' in annotatorsType:
            returnDictList = []
            # Go through all the tokens in each sentence in order to get the tokens Part Of Speech
            for s in requestedDictValue['sentences']:
                for token in s['tokens']:
                    returnDict = {}
                    returnDict['token'] = token['originalText']
                    returnDict['pos'] = token['pos']
                    returnDict['span'] = (token['characterOffsetBegin'], token['characterOffsetEnd'])
                    returnDictList.append(returnDict)
            dictValue['pos'] = returnDictList
        if 'lemma' in annotatorsType:
            returnDictList = []
            # Go through all the tokens in each sentence in order to get the tokens lemma
            for s in requestedDictValue['sentences']:
                for token in s['tokens']:
                    returnDict = {}
                    returnDict['token'] = token['originalText']
                    returnDict['lemma'] = token['lemma']
                    returnDict['span'] = (token['characterOffsetBegin'], token['characterOffsetEnd'])
                    returnDictList.append(returnDict)
            dictValue['lemma'] = returnDictList
        if 'ner' in annotatorsType:
            returnDictList = []
            # Go through all the tokens in each sentence in order to get the tokens lemma
            for s in requestedDictValue['sentences']:
                for token in s['tokens']:
                    returnDict = {}
                    returnDict['token'] = token['originalText']
                    returnDict['ner'] = token['ner']
                    returnDict['span'] = (token['characterOffsetBegin'], token['characterOffsetEnd'])
                    returnDictList.append(returnDict)
            dictValue['ner'] = returnDictList
        if 'entitymentions' in annotatorsType:
            returnDictList = []
            # Go through all the Entity Mentions in each sentence in order to get the Entity Mentions information
            for s in requestedDictValue['sentences']:
                for entity in s['entitymentions']:
                    returnDictList.append(entity)
            dictValue['entitymentions'] = returnDictList
        if 'parse' in annotatorsType:
            returnDictList = []
            # Go through all the Constituency Parsing in each sentence in order to get the Constituency Parsing information
            for s in requestedDictValue['sentences']:
                returnDictList.append(s['parse'])
            dictValue['parse'] = returnDictList
        if 'depparse' in annotatorsType:
            returnDictList = []
            # Go through all the Dependency Parsing in each sentence in order to get the Dependency Parsing information
            for s in requestedDictValue['sentences']:
                for dependency in s['basicDependencies']:
                    returnDictList.append(dependency)
            dictValue['depparse'] = returnDictList
        if 'coref' in annotatorsType:
            returnDictList = []
            # Go through all the Coreference Resolution in order to get the correct information
            for key, corefsValue in requestedDictValue['corefs'].items():
                for value in corefsValue:
                    returnDictList.append(value)
            dictValue['coref'] = returnDictList
        if 'openie' in annotatorsType:
            returnDictList = []
            # Go through all the Constituency Parsing in each sentence in order to get the Constituency Parsing information
            for s in requestedDictValue['sentences']:
                returnDictList.append(s['openie'])
            dictValue['openie'] = returnDictList
        if 'kbp' in annotatorsType:
            returnDictList = []
            # Go through all the Knowledge Base Population in each sentence in order to get the Knowledge Base Population information
            for s in requestedDictValue['sentences']:
                returnDictList.append(s['kbp'])
            dictValue['kbp'] = returnDictList
        if 'quote' in annotatorsType:
            returnDictList = []
            # Go through all the Knowledge Base Population in each sentence in order to get the Knowledge Base Population information
            for quote in requestedDictValue['quote']:
                returnDictList.append(quote)
            dictValue['quote'] = returnDictList
        if 'sentiment' in annotatorsType:
            returnDictList = []
            # Go through all the sentiment in the text in order to rearrange them in the Dictionary List
            for s in requestedDictValue['sentences']:
                returnDict = {}
                returnDict['sentimentValue'] = s['sentimentValue']
                returnDict['sentiment'] = s['sentiment']
                returnDict['sentimentDistribution'] = s['sentimentDistribution']
                returnDict['sentimentTree'] = s['sentimentTree']
                returnDictList.append(returnDict)
            dictValue['sentiment'] = returnDictList
        if 'truecase' in annotatorsType:
            returnDictList = []
            # Go through all the tokens, span and their truecase in the text
            # In order to rearrange them in the Dictionary List
            for s in requestedDictValue['sentences']:
                for token in s['tokens']:
                    returnDict = {}
                    returnDict['token'] = token['originalText']
                    returnDict['span'] = (token['characterOffsetBegin'], token['characterOffsetEnd'])
                    returnDict['truecase'] = token['truecase']
                    returnDict['truecaseText'] = token['truecaseText']
                    returnDictList.append(returnDict)
            dictValue['truecase'] = returnDictList
        if 'udfeats' in annotatorsType:
            returnDictList = []
            # Go through all the Dependencies in the text in order to rearrange them in the Dictionary List
            for s in requestedDictValue['sentences']:
                returnDict = {}
                returnDict['basicDependencies'] = s['basicDependencies']
                returnDict['enhancedDependencies'] = s['enhancedDependencies']
                returnDict['enhancedPlusPlusDependencies'] = s['enhancedPlusPlusDependencies']
                returnDictList.append(returnDict)
            dictValue['udfeats'] = returnDictList
        return dictValue

    # ************************************************List Of Annotators************************************************#
    # Tokenization
    def tokenize(self, textValue):
        """
        Tokenizes the text. This splits the text into roughly “words”, using rules or methods suitable
        for the language being processed. Sometimes the tokens split up surface words in ways suitable
        for further NLP-processing, for example “isn’t” becomes “is” and “n’t”.
        The tokenizer saves the beginning and end character offsets of each token in the input text.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every token and its span in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url, 'tokenize', textValue)
        returnDictList = []
        # Go through all the tokens and their span in the text
        # In order to rearrange them in the Dictionary List
        for token in requestedDictValue['tokens']:
            returnDict = {}
            returnDict['token'] = token['originalText']
            returnDict['span'] = (token['characterOffsetBegin'], token['characterOffsetEnd'])
            returnDictList.append(returnDict)
        return returnDictList

    # CleanXML
    def cleanxml(self, textValue):
        """
        This annotator removes XML tags from an input text.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        JSON
            A value that represents the textValue with clean xml.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url, 'cleanxml', textValue)
        return requestedDictValue

    # Sentence Splitting
    def ssplit(self, textValue):
        """
        Sentence splitting is the process of dividing text into sentences.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        List
            A value that represents every sentence in the text.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url, 'tokenize, ssplit', textValue)
        # Get all the tokens for each sentence
        tokens = [s for s in requestedDictValue['sentences']]
        sentences = []
        # Go through all the tokens in each sentence and combine them
        for s in range(len(tokens)):
            sentences.append(' '.join([token['originalText'] for token in tokens[s]['tokens']]))
        return sentences

    # Part Of Speech
    def pos(self, textValue):
        """
        Part of speech tagging assigns part of speech labels to tokens, such as whether they are verbs or nouns.
        Every token in a sentence is applied a tag.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every token and its Part Of Speech in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url, 'pos', textValue)
        returnDictList = []
        # Go through all the tokens in each sentence in order to get the tokens Part Of Speech
        for s in requestedDictValue['sentences']:
            for token in s['tokens']:
                returnDict = {}
                returnDict['token'] = token['originalText']
                returnDict['pos'] = token['pos']
                returnDict['span'] = (token['characterOffsetBegin'], token['characterOffsetEnd'])
                returnDictList.append(returnDict)
        return returnDictList

    # Lemmatization
    def lemma(self, textValue):
        """
        Lemmatization maps a word to its lemma (dictionary form).

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every token and its lemma in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url, 'lemma', textValue)
        returnDictList = []
        # Go through all the tokens in each sentence in order to get the tokens lemma
        for s in requestedDictValue['sentences']:
            for token in s['tokens']:
                returnDict = {}
                returnDict['token'] = token['originalText']
                returnDict['lemma'] = token['lemma']
                returnDict['span'] = (token['characterOffsetBegin'], token['characterOffsetEnd'])
                returnDictList.append(returnDict)
        return returnDictList

    # Named Entity Recognition
    def ner(self, textValue):
        """
        Recognizes named entities (person and company names, etc.) in text.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every toekn and its Named Entity Recognition in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url, 'ner', textValue)
        returnDictList = []
        # Go through all the tokens in each sentence in order to get the tokens Named Entity
        for s in requestedDictValue['sentences']:
            for token in s['tokens']:
                returnDict = {}
                returnDict['token'] = token['originalText']
                returnDict['ner'] = token['ner']
                returnDict['span'] = (token['characterOffsetBegin'], token['characterOffsetEnd'])
                returnDictList.append(returnDict)
        return returnDictList

    # Entity Mentions
    def entitymentions(self, textValue):
        """
        This annotator generates a list of the mentions, identified by NER, found in each sentence of a document.
        Rather than per-token labeling, it produces whole entity mentions.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every Entity Mentions in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url, 'entitymentions', textValue)
        returnDictList = []
        # Go through all the Entity Mentions in each sentence in order to get the Entity Mentions information
        for s in requestedDictValue['sentences']:
            for entity in s['entitymentions']:
                returnDictList.append(entity)
        return returnDictList

    # TokensRegexNERAnnotator
    def regexner(self, textValue, patternValue, filterValue=False):
        """
        The original goal of this Annotator was to provide a simple framework to incorporate
        named entities and named entity labels that are not annotated in traditional NER corpora,
        and hence not recoginized by our statistical NER classifiers.
        However, you can also use this annotator to simply do rule-based NER.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).
        patternValue : string
            A string value that represents a the pattern to look for in the given textValue.
        filterValue : boolean
            If true, entire sentences must match the pattern, rather than the API finding matching sections.
            default is False.

        Returns
        -------
        JSON
            A value that represents the textValue filtered by pattern.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url + '/regexner', 'regexner', textValue,
                                                              patternValue=patternValue, filterValue=filterValue)
        return requestedDictValue

    # TokensRegex
    def tokensregex(self, textValue, patternValue, filterValue=False):
        """
        StanfordCoreNLP includes TokensRegex, a framework for defining regular expressions
        over text and tokens, and mapping matched text to semantic objects.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).
        patternValue : string
            A string value that represents a the pattern to look for in the given textValue.
        filterValue : boolean
            If true, entire sentences must match the pattern, rather than the API finding matching sections.
            default is False.

        Returns
        -------
        JSON
            A value that represents the textValue filtered by pattern.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url + '/tokensregex', 'tokenize, ssplit, depparse',
                                                              textValue, patternValue=patternValue,
                                                              filterValue=filterValue)
        return requestedDictValue

    # Tregex
    def tregex(self, textValue, patternValue, filterValue=False):
        """
        The original goal of this Annotator was to provide a simple framework to incorporate
        named entities and named entity labels that are not annotated in traditional NER corpora,
        and hence not recoginized by our statistical NER classifiers.
        However, you can also use this annotator to simply do rule-based NER.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).
        patternValue : string
            A string value that represents a the pattern to look for in the given textValue.
        filterValue : boolean
            If true, entire sentences must match the pattern, rather than the API finding matching sections.
            default is False.

        Returns
        -------
        JSON
            A value that represents the textValue filtered by pattern.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url + '/tregex', 'tokenize, ssplit, depparse, parse',
                                                              textValue, patternValue=patternValue,
                                                              filterValue=filterValue)
        return requestedDictValue

    # Semgrex
    def semgrex(self, textValue, patternValue, filterValue=False):
        """
        Similar to the CoreNLP target, and nearly identical to TokensRegex, semgrex takes a block of data
        (e.g., text) as POST data, and a series of url parameters. Currently, only plain-text POST data is supported.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).
        patternValue : string
            A string value that represents a the pattern to look for in the given textValue.
        filterValue : boolean
            If true, entire sentences must match the pattern, rather than the API finding matching sections.
            default is False.

        Returns
        -------
        JSON
            A value that represents the textValue filtered by pattern.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url + '/semgrex', 'tokenize, ssplit, depparse',
                                                              textValue, patternValue=patternValue,
                                                              filterValue=filterValue)
        return requestedDictValue

    # Constituency Parsing
    def parse(self, textValue):
        """
        Provides full syntactic analysis, minimally a constituency (phrase-structure tree) parse of sentences.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every Constituency Parsing in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url, 'parse', textValue)
        returnDictList = []
        # Go through all the Constituency Parsing in each sentence in order to get the Constituency Parsing information
        for s in requestedDictValue['sentences']:
            returnDictList.append(s['parse'])
        return returnDictList

    # Dependency Parsing
    def dependency_parse(self, textValue):
        """
        Provides a fast syntactic dependency parser.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every Dependency Parsing in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url, 'depparse', textValue)
        returnDictList = []
        # Go through all the Dependency Parsing in each sentence in order to get the Dependency Parsing information
        for s in requestedDictValue['sentences']:
            for dependency in s['basicDependencies']:
                returnDictList.append(dependency)
        return returnDictList

    # Coreference Resolution
    def coref(self, textValue):
        """
        The CorefAnnotator finds mentions of the same entity in a text,
        such as when “Theresa May” and “she” refer to the same person.
        The annotator implements both pronominal and nominal coreference resolution.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every Coreference Resolution in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url, 'coref', textValue)
        returnDictList = []
        # Go through all the Coreference Resolution in order to get the correct information
        for key, corefsValue in requestedDictValue['corefs'].items():
            for value in corefsValue:
                returnDictList.append(value)
        return returnDictList

    # Open Information Extraction
    def openie(self, textValue):
        """
        The Open Information Extraction (OpenIE) annotator extracts open-domain relation triples,
        representing a subject, a relation, and the object of the relation.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every Open Information Extraction in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url,
                                                              'tokenize, ssplit, pos, lemma, depparse, natlog, openie',
                                                              textValue)
        returnDictList = []
        # Go through all the Constituency Parsing in each sentence in order to get the Constituency Parsing information
        for s in requestedDictValue['sentences']:
            returnDictList.append(s['openie'])
        return returnDictList

    # Knowledge Base Population
    def kbp(self, textValue):
        """
        Extracts relation triples meeting the TAC-KBP competition specifications.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every Knowledge Base Population in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url,
                                                              'tokenize, ssplit, pos, lemma, ner, parse, coref, kbp',
                                                              textValue)
        returnDictList = []
        # Go through all the Knowledge Base Population in each sentence in order to get the Knowledge Base Population information
        for s in requestedDictValue['sentences']:
            returnDictList.append(s['kbp'])
        return returnDictList

    # Quote Extraction And Attribution
    def quote(self, textValue):
        """
        Deterministically picks out quotes from a text.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every Quote Extraction And Attribution in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url,
                                                              'tokenize, ssplit, pos, lemma, ner, depparse, coref, quote',
                                                              textValue)
        returnDictList = []
        # Go through all the Knowledge Base Population in each sentence in order to get the Knowledge Base Population information
        for quote in requestedDictValue['quotes']:
            returnDictList.append(quote)
        return returnDictList

    # Sentiment
    def sentiment(self, textValue):
        """
        StanfordCoreNLP includes the sentiment tool and various programs which support it.
        The model can be used to analyze text.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every Sentiment in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url, 'sentiment', textValue)
        returnDictList = []
        # Go through all the sentiment in the text in order to rearrange them in the Dictionary List
        for s in requestedDictValue['sentences']:
            returnDict = {}
            returnDict['sentimentValue'] = s['sentimentValue']
            returnDict['sentiment'] = s['sentiment']
            returnDict['sentimentDistribution'] = s['sentimentDistribution']
            returnDict['sentimentTree'] = s['sentimentTree']
            returnDictList.append(returnDict)
        return returnDictList

    # TrueCaseAnnotator
    def truecase(self, textValue):
        """
        Recognizes the “true” case of tokens (how it would be capitalized in well-edited text)
        where this information was lost, e.g., all upper case text.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every token, span and its truecase in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url, 'tokenize, ssplit, truecase, pos, lemma, ner',
                                                              textValue)
        returnDictList = []
        # Go through all the tokens, span and their truecase in the text
        # In order to rearrange them in the Dictionary List
        for s in requestedDictValue['sentences']:
            for token in s['tokens']:
                returnDict = {}
                returnDict['token'] = token['originalText']
                returnDict['span'] = (token['characterOffsetBegin'], token['characterOffsetEnd'])
                returnDict['truecase'] = token['truecase']
                returnDict['truecaseText'] = token['truecaseText']
                returnDictList.append(returnDict)
        return returnDictList

    # Universal Dependencies
    def udfeats(self, textValue):
        """
        Labels tokens with their Universal Dependencies universal part of speech (UPOS) and features.
        This is a highly specialist annotator. At the moment it only works for English.

        Parameters
        ----------
        textValue : string
            A string value that represents a sentence or a number of sentences
            in English(en), Chinese(zh), Arabic(ar), French(fr), German(de) or Spanish(es).

        Returns
        -------
        Dictionary List
            A value that represents every Dependencies in the given textValue.
        """

        # Get the currect Annotator data from the server
        requestedDictValue = self.getDataForAnnotatorsWrapper(self.url, 'udfeats', textValue)
        returnDictList = []
        # Go through all the Dependencies in the text in order to rearrange them in the Dictionary List
        for s in requestedDictValue['sentences']:
            returnDict = {}
            returnDict['basicDependencies'] = s['basicDependencies']
            returnDict['enhancedDependencies'] = s['enhancedDependencies']
            returnDict['enhancedPlusPlusDependencies'] = s['enhancedPlusPlusDependencies']
            returnDictList.append(returnDict)
        return returnDictList

