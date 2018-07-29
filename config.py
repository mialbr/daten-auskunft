SECRET_KEY = 'enter secret key for csrf protection'

RECAPTCHA_PUBLIC_KEY ='enter key here'
RECAPTCHA_PRIVATE_KEY ='enter key here'

SALTX ='enter salt for hashing mail adresses'

MAIL_SERVER = 'enter url'
MAIL_PORT = # might be 465
MAIL_USE_TLS = False
MAIL_USE_SSL = True
MAIL_USERNAME = 'enter mail adress that is used for sending inquiries'
MAIL_PASSWORD = 'enter password for mail'
MAIL_DEFAULT_SENDER = 'enter mail adress that is used for sending inquiries'

MAX_CONTENT_LENGTH = 30 * 1024 * 1024 #accept highdef pictures for upload

SQLALCHEMY_DATABASE_URI = 'enter your db uri'
SQLALCHEMY_TRACK_MODIFICATIONS  = False
SQLALCHEMY_POOL_RECYCLE = 280
SQLALCHEMY_POOL_TIMEOUT = 20

BLUEPRINT1='template.jpg' #provide path to template for GDPR inquiries
BLUEPRINT2='template2.jpg' #provide path to template for GDPR inquiries

#### Collection of companies that are activated for inquiries.
#### Follow the syntax to add more - also update index.html with the new entry
#### Set 'api':'csv' if a .csv file with the applicants data should be added to the inquiry 

ADRESSATENSAMMLUNG ={'enter name of corp':
                    {'adresse': '''enter corpname
enter corp street
enter corp zip''',
                    'email': 'enter corp email adress','api': 'set to none or csv (in brackets)',
                    'extrafeld': 'enter name of additionally need identification date or set to FALSE'},                
                
}






