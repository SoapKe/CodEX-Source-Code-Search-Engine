import numpy as np
# from scipy.linalg import *
from scipy import spatial
# import matplotlib.pyplot as plt
from scipy.sparse import *
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from search.supportings import FCIConverter as conv
from search.supportings import LogWriter as lg
import os
from CodEX.config import configs
from search.supportings.LSI import Results
import pickle
import time
from scipy.sparse.linalg import svds
import redis

class LSI_TFIDF():
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    lw = lg.LogWriter()
    # get files
    path = configs['paths']['FCI_path'] + '/lsi'  # path name
    index_path = configs['paths']['LSI_indexing_path']
    files = []
    documents = {}
    sortedDocuments = []
    contents = []
    X = None
    re = None
    word = None
    vectorizer = None
    tfidf = None
    s = None
    u = None
    d = None
    idf = None
    lineNo = {}
    expireTime = 600
    end_time = time.clock()
    pageNum=configs['others']['page_num']


    # def __init__(self):
    # self.vectorizer = CountVectorizer()
    # #if there exist the pickle file, read it
    # if os.path.exists(self.index_path):
    #     rfile=open(self.index_path, 'rb')
    #     self.s = pickle.load(rfile)
    #     self.u = pickle.load(rfile)
    #     self.d = pickle.load(rfile)
    #     self.tfidf = pickle.load(rfile)
    #     self.lineNo=pickle.load(rfile)
    #
    #     self.idf = self.tfidf.idf_
    #     self.word=list(self.tfidf.vocabulary_.keys())
    #     self.files=list(self.lineNo.keys())
    #
    # else:#if there is no such pickle file, indexing
    #     self.indexing()


    # indexing
    def indexing(self):
        self.lw.write_info_log("reading files...")
        self.files = os.listdir(self.path)  # get all the file names
        if '.DS_Store' in self.files:
            self.files.remove('.DS_Store')
        fs = len(self.files)
        self.tfidf = TfidfVectorizer()
        i = 0
        while i < fs:  # go through the folder
            file = self.files[i]
            if not os.path.isdir(file):  # judge if it is a folder
                self.documents[file] = conv.to_dic(self.path + "/" + file)
                if len(self.documents[file]['content'].strip()) > 0:
                    self.contents.append(self.documents[file]['content'])
                    # store the line numbers of the term
                    self.lineNo[file] = {}
                    j = 0
                    for line in self.documents[file]['content'].split('\n'):
                        lineList = [line]
                        if len(lineList) > 0:
                            try:
                                self.tfidf.fit_transform(lineList)  # get the unique standard term of this line
                            except ValueError:
                                j += 1
                                continue
                            for term in self.tfidf.vocabulary_:
                                if term in self.lineNo[file]:
                                    self.lineNo[file][term].append(j)
                                else:
                                    self.lineNo[file][term] = [j]
                        j += 1
                    i += 1
                else:
                    self.documents.pop(file)
                    self.files.remove(file)
                    fs -= 1
            else:
                self.files.remove(file)
        print('finish reading')
        # self.files = list(self.documents.keys())
        size = len(self.documents)
        self.lw.write_info_log("get " + str(size) + " documents")
        self.lw.write_info_log("indexing...")
        self.re = self.tfidf.fit_transform(self.contents).toarray().T  # tf-idf values
        self.idf = self.tfidf.idf_
        self.word = self.word = list(self.tfidf.vocabulary_.keys())

        # compression matrix
        self.re = dok_matrix(self.re)
        # self.X=dok_matrix(self.X)
        print("start SVD")
        # svd decomposition
        self.u, self.s, self.d = svds(self.re, k=1000)
        print('start dumping')
        # store the index into the pickle
        with open(self.index_path, 'wb')as f:  # use pickle module to save data into file 'CodexIndex.pik'
            pickle.dump(self.s, f, True)
            pickle.dump(self.u, f, True)
            pickle.dump(self.d, f, True)
            pickle.dump(self.tfidf, f, True)
            pickle.dump(self.lineNo, f, True)
            print('finish')

    def getResult(self, query, page):
        if not self.r.exists(query):  # if the result is not in the redis
            self.vectorizer = CountVectorizer()
            # if there exist the pickle file, read it
            if os.path.exists(self.index_path):
                rfile = open(self.index_path, 'rb')
                self.s = pickle.load(rfile)
                self.u = pickle.load(rfile)
                self.d = pickle.load(rfile)
                self.tfidf = pickle.load(rfile)
                self.lineNo = pickle.load(rfile)

                self.idf = self.tfidf.idf_
                self.word = list(self.tfidf.vocabulary_.keys())
                self.files = list(self.lineNo.keys())

            else:  # if there is no such pickle file, indexing
                self.indexing()

            l = self.MatrixSearching(query, self.s, self.u, self.d.T)
            if l is None:
                return (0, [])

            fullHitLines = l[0]
            hitDocs = l[1]
            matchingLines = l[2]
            numOfResults = l[3]
            fullHitLineskeys = list(fullHitLines.keys())
            hitDocskeys = list(hitDocs.keys())
            matchingLineskeys = list(matchingLines.keys())
            fullHitLineskeys.sort(reverse=True)
            hitDocskeys.sort(reverse=True)
            matchingLineskeys.sort(reverse=True)
            displayList = []  # [(docName,[hit lines])]
            if len(fullHitLineskeys)>0:
                for k in fullHitLineskeys:
                    for t in fullHitLines[k]:
                        displayList.append(t)
            if len(hitDocskeys) > 0:
                # print('================')
                for k in hitDocskeys:
                    for t in hitDocs[k]:
                        displayList.append(t)
            if len(matchingLines) > 0:
                for k in matchingLineskeys:
                    for t in matchingLines[k]:
                        displayList.append(t)

            self.lw.write_info_log("storing results into redis in form of list")
            self.r.rpush(query, numOfResults)
            self.r.rpush(query, displayList)

        else:
            self.lw.write_info_log("geting results from redis")
            numOfResults = eval(self.r.lindex(query, 0))
            displayList = eval(self.r.lindex(query, 1))

        self.r.expire(query, self.expireTime)
        currentDisplay = displayList[(page - 1) * self.pageNum: page * self.pageNum]
        return (numOfResults, currentDisplay)



    def MatrixSearching(self, query, s, u, d):

        qFreq = self.vectorizer.fit_transform([query]).toarray().T  # make the vectorizer fit the query
        qWord = self.vectorizer.get_feature_names()  # the unique terms after preprocessing
        qArr = np.zeros([1, len(self.word)])

        # fill in the tf-idf into the empty Xq matrix
        ifEmpty = True
        j = 0
        for w in qWord:
            i = qWord.index(w)
            if w in self.word:
                j = self.word.index(w)
                qArr[0][j] = qFreq[i] * self.idf[j]
                ifEmpty = False

        # give the warning and stop searching if no terms found
        if ifEmpty:
            self.lw.write_warning_log("Nothing found!")
            return None

        # similarities from Dq=X.T * T * S-1.
        sDiagno = np.diag(np.array(s))
        sInv = np.linalg.inv(sDiagno)
        Dq = np.dot(qArr, u)
        Dq = np.dot(Dq, sInv)

        matchingLines = {}  # {similarity:[(docName, [hit lines])] }
        hitDocs = {}  # {lengthHits:[(docName,[hit lines])]}
        fullHitLines = {}  # {fullHitNum:[(docName,[hit lines])]}
        length = 0
        for i in range(len(d)):
            k = self.files[i]
            similarity = ((np.dot(Dq, d[i])) / ((np.linalg.norm(Dq)) * (np.linalg.norm(d[i]))))[0]
            length += 1
            hitLines = []
            hitWords = 0
            ifMiss=False
            commonLines = []
            for t in qWord:
                if t in self.lineNo[k]:
                    hitWords += 1
                    hitLines = list(set(hitLines).union(set(self.lineNo[k][t])))
                    if not ifMiss:
                        if hitWords == 1:
                            commonLines = self.lineNo[k][t]
                        else:
                            commonLines = list(set(commonLines).intersection(set(self.lineNo[k][t])))
                else:
                    ifMiss=True
            lengthHit = len(hitLines) * hitWords
            if hitWords > 1 and not ifMiss:
                fullHit = len(commonLines)
            else:
                fullHit = 0
            if fullHit > 0:
                if fullHit in fullHitLines:
                    fullHitLines[fullHit].append((k, hitLines))
                else:
                    fullHitLines[fullHit] = [(k, hitLines)]
            elif lengthHit > 0 and len(qWord)==1:
                # print('-----------')
                if lengthHit in hitDocs:
                    hitDocs[lengthHit].append((k, hitLines))
                else:
                    hitDocs[lengthHit] = [(k, hitLines)]
            else:
                if similarity > 0:
                    if similarity not in matchingLines:
                        matchingLines[similarity] = [(k, [])]
                    else:
                        matchingLines[similarity].append((k, []))
                else:
                    # don't store it
                    length -= 1
        # print(hitDocs)
        return (fullHitLines, hitDocs, matchingLines, length)



if __name__ == '__main__':
    lsi = LSI_TFIDF()
    currentDisplay = lsi.getResult('merge sort',1)
    print(currentDisplay)
