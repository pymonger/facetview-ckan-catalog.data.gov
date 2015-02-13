class Config(object):
    SECRET_KEY = 'secret key'
    #CKAN_REST_URL = 'http://127.0.0.1:3000'
    CKAN_REST_URL = 'http://catalog.data.gov/api/3'
    ELASTICSEARCH_URL = 'http://127.0.0.1:9200'

    # for CKAN app
    CKAN_ELASTICSEARCH_INDEX = 'ckan-stage'
    CKAN_ELASTICSEARCH_SETTINGS = '../config/es_settings-ckan.json'
    CKAN_ELASTICSEARCH_MAPPING = '../config/es_mapping-ckan.json'


class ProdConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///../database.db'

    CACHE_TYPE = 'simple'


class DevConfig(Config):
    DEBUG = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False

    SQLALCHEMY_DATABASE_URI = 'sqlite:///../database.db'
    SQLALCHEMY_ECHO = True

    CACHE_TYPE = 'null'

    # This allows us to test the forms from WTForm
    WTF_CSRF_ENABLED = False
