import re
from pathlib import Path
from collections import Counter
import parsivar
from string import punctuation
from tqdm import tqdm
import copy



class DataNormalizer:
    def __init__(self):
        # pattern for matching mi in start of token
        self.mi_patterns = r"\bن?می[آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی]+"
        
        # punctuation marks
        self.punc_after = r"\.:!،؛؟»\]\)\}"
        self.punc_before = r"«\[\(\{"
        self.all_punc_marks = r"[\.:!،؛؟»\'\]\)\}|«\[\(\/\{><+\-?!=_]"

        self.number_not_persian = "0123456789%٠١٢٣٤٥٦٧٨٩"
        self.number_persian = "۰۱۲۳۴۵۶۷۸۹٪۰۱۲۳۴۵۶۷۸۹"
        
        # fathe kasre ,....
        self.arabic_patterns = [
                    ("[\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652]", ""),
                    ("[ك]",'ک'),
                    ("[ي]","ی"),
                    ("[هٔ]","ه"),
                    ("[أ]","ا"),
            
                ]
        self.punctuation_spacing_patterns = [
                # remove space before and after quotation
                ('" ([^\n"]+) "', r'"\1"'),
                (" ([" + self.punc_after + "])", r"\1"),  # remove space before
                ("([" + self.punc_before + "]) ", r"\1"),  # remove space after
                # put space after . and :
                (
                    "([" + self.punc_after[:3] + "])([^ " + self.punc_after + r"\d۰۱۲۳۴۵۶۷۸۹])",
                    r"\1 \2",
                ),
                (
                    "([" + self.punc_after[3:] + "])([^ " + self.punc_after + "])",
                    r"\1 \2",
                ),  # put space after
                (
                    "([^ " + self.punc_before + "])([" + self.punc_before + "])",
                    r"\1 \2",
                ),  # put space before
                # put space after number
                (r"(\d)([آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی])", r"\1 \2"),
                # put space after number
                (r"([آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهی])(\d)", r"\1 \2"),
            ]

        # some special unicodes which should be replaced by persian terms
        self.unicode_replacements = [
                    ("﷽"," بسم الله الرحمن الرحیم "),(" ﷼", " ریال"),
                    ("(ﷰ|ﷹ)", " صلی "),
                    (" ﷲ", " الله"),
                    (" ﷳ", " اکبر"),
                    (" ﷴ", " محمد"),
                    (" ﷵ", " صلعم"),
                    (" ﷶ", " رسول"),
                    (" ﷷ", " علیه"),
                    (" ﷸ", " وسلم"),
                    (" ﻵ|ﻶ|ﻷ|ﻸ|ﻹ|ﻺ|ﻻ|ﻼ", " لا"),
                ]
        # extra space patterns
        self.extra_space_patterns = [
            (r" {2,}", " "),           # remove extra spaces
            (r"\n{3,}", "\n\n"),       # remove extra newlines
            (r"\u200c{2,}", "\u200c"), # remove extra ZWNJs
            (r"\u200c{1,} ", " "),     # remove unneeded ZWNJs before space
            (r" \u200c{1,}", " "),     # remove unneeded ZWNJs after space
            (r"\b\u200c*\B", " "),      # remove unneeded ZWNJs at the beginning of words
            (r"\B\u200c*\b", " "),      # remove unneeded ZWNJs at the end of words
            (r"[ـ\r]", " "),           # remove keshide, carriage returns
        ]

        # space patterns for nimfasele
        self.spacing_patterns = [
            (r"\xa0"," "),  # remove no-break char
            (r"([^ ]) ی ", r"\1‌ی "),          # fix 'ی' space
            (r"(^| )(ن?می) ", r"\1\2‌"),        # fix 'می' and 'نمی' space
            (r"(?<=[^\n\d" + self.punc_after + self.punc_before + r"]{2}) (تر(ین?)?|گری?|های?)(?=[ \n" + self.punc_after + self.punc_before + r"]|$)", r"‌\1"),
            # fix suffix spacing
            (r"([^ ]ه) (ا(م|یم|ش|ند|ی|ید|ت))(?=[ \n" + self.punc_after + r"]|$)", r"\1‌\2"),  # fix verb conjugation spacing
            (r"(ه)(ها)", r"\1‌\2"),  
        ]

        # bons of verbs
        with Path('verbs.dat').open(encoding="utf8") as verbs_file:
                verbs = list(
                    reversed([verb.strip() for verb in verbs_file if verb]),
                )
                self.present_bons = {verb[1:].split("#")[0].strip() for verb in verbs[1:]}
                self.past_bons = {verb.split("#")[1] for verb in verbs}


    @staticmethod
    def regex_replace(patterns: list, text: str) -> str:
        for pattern, repl in patterns:
            text = re.sub(pattern, repl, text)
        return text

    # fix spacings
    def spacing_correction(self, text: str) -> str:
        text = self.regex_replace(self.extra_space_patterns, text)
        text = self.regex_replace(self.punctuation_spacing_patterns, text)
        text = self.regex_replace(self.spacing_patterns, text)
        return text

    # repplace special charaters
    def unicode_replacement(cls, text: str) -> str:
        for old, new in cls.unicode_replacements:
            text = re.sub(old, new, text)
        return text
        
    # convert numbers to persian numbers
    def persian_number(cls, text: str) -> str:
        translation_table = str.maketrans(
            cls.number_not_persian,
            cls.number_persian )
        translated_text = text.translate(translation_table)
        return translated_text
     
    # remove puctuation marks and arabic chars
    def remove_special_chars(cls, text: str) -> str:
        text = cls.remove_punc_marks(text)
        text = cls.remove_arabic_chars(text)
        return text

    # remove some arabic chars
    def remove_arabic_chars(cls, text: str) -> str:
        return cls.regex_replace(cls.arabic_patterns, text)

    # remove puctuation marks
    def remove_punc_marks(cls, text: str) -> str:
        return re.sub(cls.all_punc_marks, "", text)

    # seperate mi in start of verbs
    def seperate_mi(cls, text:str) -> str:
        matches = re.findall(cls.mi_patterns, text)
        for m in matches:
            r = re.sub("^(ن?می)", r"\1‌", m)
            # remove mi from token to check it contains the bon of a verb or not
            x = re.sub("^(ن?می)", "", m)
            for verb in cls.present_bons:
                if verb in x:
                    text = text.replace(m, r)
            for verb in cls.past_bons:
                if verb in x:
                    text = text.replace(m, r)
        return text

    # general normalization method to perform all above functions
    def normalize(cls, text:str) -> str:
        text = cls.remove_special_chars(text)
        text = cls.seperate_mi(text)
        text = cls.persian_number(text)
        text = cls.unicode_replacement(text)
        text = cls.spacing_correction(text)
        return text

    


class DataPreprocessor:
    top_k = {}
    pattern = re.compile(r'([؟!?]+|[\d.:]+|[:.،؛»\])}"«\[({/\\])')
    after_verbs = {
                "ام",
                "ای",
                "است",
                "ایم",
                "اید",
                "اند",
                "بودم",
                "بودی",
                "بود",
                "بودیم",
                "بودید",
                "بودند",
                "باشم",
                "باشی",
                "باشد",
                "باشیم",
                "باشید",
                "باشند",
                   "شده",
            "نشده",
                "شوم",
                "شوی",
                "شود",
                "شویم",
                "شوید",
                "شوند",
                "شدم",
                "شدی",
                "شد",
                "شدیم",
                "شدید",
                "شدند",
                "نشوم",
                "نشوی",
                "نشود",
                "نشویم",
                "نشوید",
                "نشوند",
                "نشدم",
                "نشدی",
                "نشد",
                "نشدیم",
                "نشدید",
                "نشدند",
                "می‌شوم",
                "می‌شوی",
                "می‌شود",
                "می‌شویم",
                "می‌شوید",
                "می‌شوند",
                "می‌شدم",
                "می‌شدی",
                "می‌شد",
                "می‌شدیم",
                "می‌شدید",
                "می‌شدند",
                "نمی‌شوم",
                "نمی‌شوی",
                "نمی‌شود",
                "نمی‌شویم",
                "نمی‌شوید",
                "نمی‌شوند",
                "نمی‌شدم",
                "نمی‌شدی",
                "نمی‌شد",
                "نمی‌شدیم",
                "نمی‌شدید",
                "نمی‌شدند",
               
            }

    before_verbs = {
                "خواهم",
                "خواهی",
                "خواهد",
                "خواهیم",
                "خواهید",
                "خواهند",
                "نخواهم",
                "نخواهی",
                "نخواهد",
                "نخواهیم",
                "نخواهید",
                "نخواهند",
            }
    vere = {}
    def __init__(self):
        # save terms like گفته ، خورده which are bon mazi + ه
        with Path('verbs.dat').open(encoding="utf8") as verbs_file:
                verbs = list(
                    reversed([verb.strip() for verb in verbs_file if verb]),
                )
                DataPreprocessor.verbe = {(verb.split("#")[0] + 'ه') for verb in verbs}
     
    #Tokenization
    @staticmethod
    def Tokenization(text):
        text = DataPreprocessor.pattern.sub(r" \1 ", text.replace("\n", " ").replace("\t", " "))
        tokens = [word for word in text.split(" ") if word]
        tokens_cleaned = [token.strip('\xa0') for token in tokens if len(token.strip()) != 0]

        result = [""]
        # merge multi term verbs like خواهم رفت to خواهم_رفت
        for token in reversed(tokens_cleaned):
            if token in DataPreprocessor.before_verbs or (
                result[-1] in DataPreprocessor.after_verbs and token in DataPreprocessor.verbe
            ):
                result[-1] = token + "_" + result[-1]
            else:
                result.append(token)
        return list(reversed(result[1:]))
    
    #Normalization
    @staticmethod
    def Normalization(text):
        my_normalizer = DataNormalizer()
        return my_normalizer.normalize(text)
    
    #Stop_Words
    @staticmethod
    def Top_K_Frequent(tokens,k):
        token_counts = Counter(tokens)
        sorted_tokens = sorted(token_counts.items(), key=lambda x: x[1], reverse=True)
        stopwords_to_remove = [token for token, count in sorted_tokens[:k]]
        report = {token: count for token, count in sorted_tokens[:k]}
        return report
        
    # print top k frequent terms
    def print_top_k(self):
        for token, count in self.top_k.items():
            print(f"Token: {token}, Count: {count}")
            
    #Stemming
    @staticmethod
    def Stemming(tokens):
        stemmed = []
        my_stemmer = parsivar.FindStems()
        for token in tokens:
            stemmed.append(my_stemmer.convert_to_stem(token))
        return stemmed
    
    #Remove Punctuations
    @staticmethod
    def Remove_Punctuations(text):
        return re.sub(f'[{punctuation}؟،٪×÷»«]+', '', text)

    # preprocess a text and return final tokens
    def simple_preprocess(self, content, remove_punctuations=True, normalizatin=True, stemming=True, remove_frequent_words=False):
        tmp = copy.deepcopy(content)
        tokens = []
        if remove_punctuations:
            tmp = self.Remove_Punctuations(tmp)
        if normalizatin:
            tmp = self.Normalization(tmp)
        tmp = self.Tokenization(tmp)
        if stemming:
            tmp = self.Stemming(tmp)
        tokens += tmp
        if remove_frequent_words:
            tokens = [token for token in tmp if token not in self.top_k]
        return tokens
        

    # method to tokenize a text
    def tokenize(self, text):
        return self.Tokenization(text)

    # preprocess all given docs
    def preprocess(self, articles, remove_punctuations=True, normalizatin=True, stemming=True, remove_frequent_words=True):
        tokens = []
        for doc in tqdm(articles.values(), desc="Processing documents"):
            tmp = copy.deepcopy(doc.original_content)
            if remove_punctuations:
                tmp = self.Remove_Punctuations(tmp)
            if normalizatin:
                tmp = self.Normalization(tmp)
            
            tmp = self.Tokenization(tmp)
            if stemming:
                tmp = self.Stemming(tmp)
            doc.tokens = tmp
            tokens += tmp
        
        # save top k frequent
        self.top_k = self.Top_K_Frequent(tokens, 50)
        # remove stop words from doc tokens
        if remove_frequent_words:
            for doc in articles.values():
                doc.preprocessed_content = [token for token in doc.tokens if token not in self.top_k]
        return articles