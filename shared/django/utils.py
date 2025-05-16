from collections import OrderedDict

from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response


class CustomPagination(LimitOffsetPagination):
    default_limit = 25

    def get_paginated_response(self, data):
        next_offset = self.offset + self.limit
        previous_offset = self.offset - self.limit
        return Response(OrderedDict([
            ('count', self.count),
            ('next', self.get_next_link()),
            ('next_offset', next_offset if next_offset < self.count else self.count),
            ('previous_offset', previous_offset if previous_offset > 0 else 0),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'count': {
                    'type': 'integer',
                    'example': 123,
                },
                'next': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'example': 'https://api.example.org/accounts/?limit=10&offset=30'
                },
                'previous': {
                    'type': 'string',
                    'nullable': True,
                    'format': 'uri',
                    'example': 'https://api.example.org/accounts/?limit=10&offset=10'
                },
                'next_offset': {
                    'type': 'integer',
                    'example': 30
                },
                'previous_offset': {
                    'type': 'integer',
                    'example': 10,
                },
                'results': schema,
            },
        }
