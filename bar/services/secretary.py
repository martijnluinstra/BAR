import json
import requests

TOKEN_DUMP_LOCATION = 'data/'


class SecretaryAPIException(Exception):
    pass


class SecretaryTokenException(SecretaryAPIException):
    pass


class SecretaryPerson:
    def __init__(self, person):
        self.id = person['id']
        if person['family_name_preposition']:
            self.name = '{} {} {}'.format(person['first_name'], person['family_name_preposition'], person['family_name'])
        else:
            self.name = '{} {}'.format(person['first_name'], person['family_name'])
        self.address = person['street_name']
        self.city = person['place']
        self.email = person['email_address']
        self.phone = person['phone_number']
        self.iban = person['iban']
        self.bic = person['bic']
        self.birthday = person['birth_date']

    def to_dict(self):
        fields = ['id', 'name', 'address', 'city', 'email', 'phone', 'bic', 'iban', 'birthday']
        return {field: getattr(self, field) for field in fields}


class SecretaryAPI:
    def __init__(self, app):
        self.base_url = app.config.get('SECRETARY_URL')

        user = app.config.get('SECRETARY_USER')
        password = app.config.get('SECRETARY_PASSWORD')

        token_file = "{}/secretary_token".format(app.config.get('SECRETARY_TOKEN_DUMP_LOCATION', TOKEN_DUMP_LOCATION))

        try:
            with open(token_file, 'r') as f:
                self.token = json.load(f)
        except (IOError, ValueError):
            self.token = {}

        if not self._is_valid_token(self.token):
            self.token = self._request_token(user, password)
            with open(token_file, 'w+') as f:
                json.dump(self.token, f)


    def find_persons_by_id(self, *ids):
        if not ids:
            return []

        if not all(isinstance(x, int) for x in ids):
            raise TypeError('Cover ID needs to be an integer')
        
        result = self._get_json('persons/all.json', send_token=True, params={'id': ','.join([str(x) for x in ids])})
        
        return _interpret_result(result)


    def find_members_by_name(self, name):
        result = self._get_json('persons/members.json', send_token=True, params={'full_name': name})
        return _interpret_result(result)


    def _request_token(self, user, password):
        response = self._post_json('token/new.json', data={'username': user, 'password': password})
        if not response['success']:
            raise SecretaryTokenException('Could not request new token: ' + response['errors'])
        return { 'user': response['user'], 'token': response['token'] }


    def _is_valid_token(self, token):
        if not 'user' in token or not 'token' in token:
            return False
        response = self._get_json('token/{token}/{user}.json'.format(**token))
        return response['success']


    def _get_json(self, url, **kwargs):
        return self._request_json('GET', url, **kwargs)


    def _post_json(self, url, **kwargs):
        return self._request_json('POST', url, **kwargs)


    def _request_json(self, method, url, send_token=False, params={}, **kwargs):
        if send_token:
            params.update(self.token)
        response = requests.request(method, self.base_url + url, params=params, **kwargs)
        response.raise_for_status()
        return response.json()


def _interpret_result(result):
    return {id: SecretaryPerson(details) for id, details in result.items()}
