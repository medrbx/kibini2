from elasticsearch5 import Elasticsearch, helpers
from elasticsearch5.exceptions import NotFoundError

import pandas as pd

class Pd2Es():
    """
    Writing pandas DataFrames to ElasticSearch
    cf https://github.com/dashaub/espandas/blob/master/espandas/espandas.py
    """

    def __init__(self, **kwargs):
        """
        Construct an espandas reader/writer
        :params **kwargs: arguments to pass for establishing the connection to ElasticSearch
        """
        self.client = Elasticsearch(**kwargs)
        self.successful_ = None
        self.failed_ = None
        self.uid_name = None

    def es_write(self, df, index, doc_type, uid_name='indexId'):
        """
        Insert a Pandas DataFrame into ElasticSearch
        :param df: the DataFrame, must contain the column 'indexId' for a unique identifier
        :param index: the ElasticSearch index
        :param doc_type: the ElasticSearch doc_type
        """
        if not isinstance(df, pd.DataFrame):
            raise ValueError('df must be a pandas DataFrame')

        if not self.client.indices.exists(index=index):
            print('index does not exist, creating index')
            self.client.indices.create(index)

        if uid_name not in df.columns:
            raise ValueError('the uid_name must be a column in the DataFrame')

        if len(df[uid_name]) != len(set(df[uid_name])):
            message = 'the values in uid_name must be unique to use as an ElasticSearch _id'
            raise ValueError(message)
        self.uid_name = uid_name

        def generate_dict(df):
            """
            Generator for creating a dict to be inserted into ElasticSearch
            for each row of a pd.DataFrame
            :param df: the input pd.DataFrame to use, must contain an '_id' column
            """
            records = df.to_dict(orient='records')
            for record in records:
                for key, value in dict(record).items():
                    if value == 'None' or value == 'nan' or value == 'NaT':
                        del record[key]
                yield record
                #print(record)

        # The dataframe should be sorted by column name
    #    df = df.reindex_axis(sorted(df.columns), axis=1)
        df = df.astype('str')

        data = ({'_index': index,
                 '_type': doc_type,
                 '_id': record[uid_name],
                 '_source': record}
                for record in generate_dict(df))
        helpers.bulk(self.client, data)
