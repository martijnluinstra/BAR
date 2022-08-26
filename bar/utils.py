from datetime import datetime
from urllib.parse import urlparse, urljoin

from dateutil.relativedelta import relativedelta
from flask import request, g, current_app, Markup
from flask_login import current_user
from schwifty import IBAN, BIC
from schwifty.exceptions import InvalidChecksumDigits, InvalidCountryCode, InvalidLength, InvalidStructure 

from .services.secretary import SecretaryAPI

import bleach
import markdown


def render_markdown(content):
    clean = bleach.clean(content)
    return markdown.markdown(
        clean,
        extensions=(
            'sane_lists',
            'smarty',
            'pymdownx.magiclink',
            'pymdownx.saneheaders',
            'pymdownx.betterem',
            'pymdownx.tilde',
        ),
        extension_configs={
            'pymdownx.tilde': {
                'subscript': False,
            },
        },
        output_format='html5',
    )


def markdown_filter(content):
    return Markup(render_markdown(content))


def format_price(amount, currency='€'):
    return '{1} {0:.2f}'.format(amount, currency)


def format_exchange(amount):
    if not amount:
        amount = 0
    return format_price(amount/100)


def is_eligible(participant, product):
    if not participant.birthday:
        return True
    age = relativedelta(datetime.now(), participant.birthday).years
    return not (product.age_limit and age<current_user.age_limit)


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc


def init_app(app):
    app.add_template_filter(format_exchange)
    app.add_template_filter(format_price)
    app.add_template_filter(is_eligible)
    app.add_template_filter(markdown_filter, name='markdown')
    app.add_template_global(datetime.now, name='now')


def get_secretary_api():
    if not g.get('_secretary_api'):
        g._secretary_api = SecretaryAPI(current_app)
    return g.get('_secretary_api')


def validate_iban(value):
    try:
        if value != current_app.config.get('NO_IBAN_STRING', 'OUTSIDE_SEPA_AREA'):
            return IBAN(value, validate_bban=True)
    except InvalidLength:
        raise Exception("Invalid IBAN: length doesn't match country-specific requirements.")
    except InvalidChecksumDigits:
        raise Exception("Invalid IBAN: invalid checksum, probably caused by a typo.")
    except InvalidStructure:
        raise Exception("Invalid IBAN: contains unexpected characters or invalid bank ID.")
    except Exception:
        raise Exception('Invalid IBAN.')

def validate_bic(value):
    try:
        return BIC(value)
    except InvalidLength:
        raise Exception("Invalid BIC: length must be 8 or 11.")
    except InvalidCountryCode:
        raise Exception("Invalid BIC: unknown country code.")
    except InvalidStructure:
        raise Exception("Invalid BIC: contains unexpected characters.")
    except Exception:
        raise Exception('Invalid BIC.')
