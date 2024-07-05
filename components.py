from sortedcontainers import SortedDict
import math
from preprocessing import DataPreprocessor
import collections
from tqdm import tqdm
import numpy as np
from collections import Counter



class NewsArticle:
    def __init__(self, id, title, original_content, url, preprocessed_content=[]):
        self.id = id
        self.title = title
        self.original_content = original_content
        self.url = url
        self.preprocessed_content = preprocessed_content

    
    def calculate_length(self):
        token_counts = Counter(self.preprocessed_content)
        
        tf_values = np.array([calculate_tf(freq) for freq in token_counts.values()])
        
        return np.linalg.norm(tf_values)
    
        
        
    


    def __repr__(self):
        return f"id= {self.id}\ttitle= {self.title}\ncontent= {self.original_content}"







class DocData:

    def __init__(self):
        self.tf = 0
        self.frequency = 0
        self.positions = []
    




class TermData:
    
    def __init__(self):
        self.df = 0
        self.idf = 0
        self.total_frequency = 0
        self.champions_list = {}
        self.postings_list = {}

    
    def calculate_jaccard_score(self, scores):
        for doc_id in self.postings_list.keys():
            if doc_id not in scores.keys():
                scores[doc_id] = 0
            scores[doc_id] += 1


    def calculate_cosine_score(self, scores, w_tq, champion=False):
        if champion:
            for doc_id, tf in self.champions_list.items():
                if doc_id not in scores.keys():
                    scores[doc_id] = 0
                scores[doc_id] += w_tq * tf
        else:
            for doc_id, doc_data in self.postings_list.items():
                if doc_id not in scores.keys():
                    scores[doc_id] = 0
                scores[doc_id] += w_tq * doc_data.tf
    
                

def calculate_tf(x):
        return 1 + np.log10(x)
    
    
def calculate_idf(x, N):
        return np.log10(N / x)



class SearchEngine:
    


    def __init__(self, articles, champions_size=0):
        self.index = SortedDict()
        self.articles = articles
        self.N = len(self.articles)
        self.champion_size = champions_size
        self.__build_index()
        


    
    


    def __build_index(self):
        for doc in tqdm(self.articles.values(), desc="adding documents"):
            self.__add_document(doc)
        for term_data in tqdm(self.index.values(), desc='computing weights'):
            term_data.df = len(term_data.postings_list)
            # computing idf for each term
            term_data.idf = calculate_idf(term_data.df, self.N)
            for doc_id, doc_data in term_data.postings_list.items():
                # computing tf for each doc in the postings list
                doc_data.tf = calculate_tf(doc_data.frequency)
                if len(term_data.champions_list) < self.champion_size:
                    term_data.champions_list[doc_id] = doc_data.tf
                else:
                    min_key = min(term_data.champions_list, key=term_data.champions_list.get) # type: ignore
                    if doc_data.tf > term_data.champions_list[min_key]:
                        del term_data.champions_list[min_key]
                        term_data.champions_list[doc_id] = doc_data.tf
            term_data.champions_list = dict(sorted(term_data.champions_list.items(), key= lambda item: item[1], reverse=True))



            
            






    def __add_document(self, doc):
        doc_id = doc.id
        tokens = doc.preprocessed_content
        
        for position, token in enumerate(tokens):
            if token not in self.index:
                    self.index[token] = TermData()

            if doc_id not in self.index[token].postings_list:
                self.index[token].postings_list[doc_id] = DocData()
            
            self.index[token].total_frequency += 1
            self.index[token].postings_list[doc_id].frequency += 1
            self.index[token].postings_list[doc_id].positions.append(position)




    def __return_top_k_results(self, scores, k):
        # Sort the dictionary items by value in descending order
        sorted_items = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        
        # Extract keys from the sorted items up to the k-th element
        top_k_keys = [item[0] for item in sorted_items[:k]]
        
        return top_k_keys



    

    def search(self, query, k, similarity='cosine', champion=False):
        preprocessor = DataPreprocessor()
        query_tokens = preprocessor.simple_preprocess(query)
        scores = {}
        if similarity == 'jaccard':
            union = {}
            for token in query_tokens:
                if token in self.index.keys():
                    self.index[token].calculate_jaccard_score(scores)
            # normalization
            for doc_id in scores.keys():
                union[doc_id] = len(set(self.articles[doc_id].preprocessed_content).union(set(query_tokens)))
                scores[doc_id] /= union[doc_id]

        elif similarity == 'cosine':
            query_dict = dict(collections.Counter(query_tokens))
            if champion:
                chmp_docs = set()
                for token in query_dict.keys():
                    if token in self.index.keys():
                        chmp_docs.update(self.index[token].champions_list.keys())
                if len(chmp_docs) < k:
                    champion = False
            for token, count in query_dict.items():
                if token in self.index.keys():
                    w_tq = calculate_tf(count) * self.index[token].idf
                    self.index[token].calculate_cosine_score(scores, w_tq, champion)
            # normalizing
            for doc_id in scores.keys():
                scores[doc_id] /= self.articles[doc_id].calculate_length()
                        

            
        top_k_results = self.__return_top_k_results(scores, k)

        for i, doc_id in enumerate(top_k_results):
            print(f'Rank {i}\tScore: {scores[doc_id]}')
            print(self.articles[doc_id])
            print()

            

            














    def display_index(self,):
        for term, term_data in self.index.items():
            print(f"Term: {term}")
            print(f'Champions list: {term_data.champions_list}')
            print(f"  Total Frequency: {term_data.total_frequency}")
            print(f'  idf: {term_data.idf}')
            for doc_id, doc_data in term_data.postings_list.items():
                print(f"    Doc ID: {doc_id}")
                print(f"      Frequency: {doc_data.frequency}")
                print(f'      tf: {doc_data.tf}')
                print(f"      Positions: {doc_data.positions}")
                
            print()

