from sparknlp.annotator import DistilBertForQuestionAnswering


class SpanDistilBertClassifier:
    @staticmethod
    def get_default_model():
        return DistilBertForQuestionAnswering.pretrained() \
            .setInputCols(["document_question", "context"]) \
            .setOutputCol("answer")

    @staticmethod
    def get_pretrained_model(name, language, bucket=None):
        return DistilBertForQuestionAnswering.pretrained(name, language, bucket) \
            .setInputCols(["document_question", "context"]) \
            .setOutputCol("answer")
