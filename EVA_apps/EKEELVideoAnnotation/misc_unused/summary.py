from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lex_rank import LexRankSummarizer
from text_processor.words import rake_top
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, BartTokenizer, BartForConditionalGeneration, BartConfig
#pip install bert-extractive-summarizer
from summarizer import Summarizer

#from summary import LectureEnsembler

def sumy_summary(clusters, num_sentences):
    print("SUMY")
    for i, c in enumerate(clusters):
        text = ""
        for sentence in c.sentences:
            text += sentence + " \n\n"

        print("Keywords estratte sul segmento", i)
        print(rake_top(3,text))


        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = LexRankSummarizer()

        summary = summarizer(parser.document, num_sentences)

        summary_text = ""
        for s in summary:
            summary_text += " " + str(s)

        print("Segmento ", i)
        print("Summary:")
        print(summary_text)

        print("Keywords estratte sulla summary")
        print(rake_top(3,summary_text))
        print()
        #c.summary = summary


def bert_summary(clusters):
    print("\n\n BERT")
    for i, c in enumerate(clusters):
        text = ""
        for sentence in c.sentences:
            text += sentence + " "

        print("Keywords estratte sul segmento", i)
        print(rake_top(3, text))

        model = Summarizer()
        result = model(text, min_length=60)
        summary_text = ''.join(result)

        print("Segmento ", i)
        print("Summary:")
        print(summary_text)

        print("Keywords estratte sulla summary")
        print(rake_top(3, summary_text))
        print()



# def bert_summary(clusters):
#     for c in clusters:
#
#         text = []
#         for sentence in c.sentences:
#             text.append(sentence)
#
#         # content = [c for c in text if len(c) > 50 and not c.lower().startswith('but') and
#         #            not c.lower().startswith('and')
#         #            and not c.lower().__contains__('quiz') and
#         #            not c.lower().startswith('or')]
#
#         res = LectureEnsembler(text).run_clusters(0.2)
#
#         results = []
#         for j in res:
#             # results.append(content[j-1])
#             results.append(text[j])
#
#         print("RIASSUNTO")
#         print(results)



