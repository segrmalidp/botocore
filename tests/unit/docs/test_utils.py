# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import mock

from tests import unittest
from tests.unit.docs import BaseDocsTest
from botocore.docs.utils import py_type_name
from botocore.docs.utils import py_default
from botocore.docs.utils import get_official_service_name
from botocore.docs.utils import traverse_and_document_shape
from botocore.docs.utils import AutoPopulatedParam
from botocore.docs.example import ResponseExampleDocumenter
from botocore.docs.example import RequestExampleDocumenter
from botocore.docs.params import RequestParamsDocumenter
from botocore.docs.params import ResponseParamsDocumenter


class TestPythonTypeName(unittest.TestCase):
    def test_structure(self):
        self.assertEqual('dict', py_type_name('structure'))

    def test_list(self):
        self.assertEqual('list', py_type_name('list'))

    def test_map(self):
        self.assertEqual('dict', py_type_name('map'))

    def test_string(self):
        self.assertEqual('string', py_type_name('string'))

    def test_character(self):
        self.assertEqual('string', py_type_name('character'))

    def test_blob(self):
        self.assertEqual('bytes', py_type_name('blob'))

    def test_timestamp(self):
        self.assertEqual('datetime', py_type_name('timestamp'))

    def test_integer(self):
        self.assertEqual('integer', py_type_name('integer'))

    def test_long(self):
        self.assertEqual('integer', py_type_name('long'))

    def test_float(self):
        self.assertEqual('float', py_type_name('float'))

    def test_double(self):
        self.assertEqual('float', py_type_name('double'))


class TestPythonDefault(unittest.TestCase):
    def test_structure(self):
        self.assertEqual('{...}', py_default('structure'))

    def test_list(self):
        self.assertEqual('[...]', py_default('list'))

    def test_map(self):
        self.assertEqual('{...}', py_default('map'))

    def test_string(self):
        self.assertEqual('\'string\'', py_default('string'))

    def test_blob(self):
        self.assertEqual('b\'bytes\'', py_default('blob'))

    def test_timestamp(self):
        self.assertEqual('datetime(2015, 1, 1)', py_default('timestamp'))

    def test_integer(self):
        self.assertEqual('123', py_default('integer'))

    def test_long(self):
        self.assertEqual('123', py_default('long'))

    def test_double(self):
        self.assertEqual('123.0', py_default('double'))


class TestGetOfficialServiceName(BaseDocsTest):
    def setUp(self):
        super(TestGetOfficialServiceName, self).setUp()
        self.service_model.metadata = {
            'serviceFullName': 'Official Name'
        }

    def test_no_short_name(self):
        self.assertEqual('Official Name',
                         get_official_service_name(self.service_model))

    def test_aws_short_name(self):
        self.service_model.metadata['serviceAbbreviation'] = 'AWS Foo'
        self.assertEqual('Official Name (Foo)',
                         get_official_service_name(self.service_model))

    def test_amazon_short_name(self):
        self.service_model.metadata['serviceAbbreviation'] = 'Amazon Foo'
        self.assertEqual('Official Name (Foo)',
                         get_official_service_name(self.service_model))

    def test_short_name_in_official_name(self):
        self.service_model.metadata['serviceFullName'] = 'The Foo Service'
        self.service_model.metadata['serviceAbbreviation'] = 'Amazon Foo'
        self.assertEqual('The Foo Service',
                         get_official_service_name(self.service_model))


class TestAutopopulatedParam(BaseDocsTest):
    def setUp(self):
        super(TestAutopopulatedParam, self).setUp()
        self.name = 'MyMember'
        self.param = AutoPopulatedParam(self.name)

    def test_request_param_not_required(self):
        section = self.doc_structure.add_new_section(self.name)
        section.add_new_section('param-documentation')
        self.param.document_auto_populated_param(
            'docs.request-params', self.doc_structure)
        self.assert_contains_line(
            ('Note this parameter is autopopulated. There is no need '
             'to include in method call'))

    def test_request_param_required(self):
        section = self.doc_structure.add_new_section(self.name)
        is_required_section = section.add_new_section('is-required')
        section.add_new_section('param-documentation')
        is_required_section.write('**[REQUIRED]**')
        self.param.document_auto_populated_param(
            'docs.request-params', self.doc_structure)
        self.assert_not_contains_line('**[REQUIRED]**')
        self.assert_contains_line(
            ('Note this parameter is autopopulated. There is no need '
             'to include in method call'))

    def test_non_default_param_description(self):
        description = 'This is a custom description'
        self.param = AutoPopulatedParam(self.name, description)
        section = self.doc_structure.add_new_section(self.name)
        section.add_new_section('param-documentation')
        self.param.document_auto_populated_param(
            'docs.request-params', self.doc_structure)
        self.assert_contains_line(description)

    def test_request_example(self):
        top_section = self.doc_structure.add_new_section('structure-value')
        section = top_section.add_new_section(self.name)
        example = 'MyMember: \'string\''
        section.write(example)
        self.assert_contains_line(example)
        self.param.document_auto_populated_param(
            'docs.request-example', self.doc_structure)
        self.assert_not_contains_line(example)

    def test_param_not_in_section_request_param(self):
        self.doc_structure.add_new_section('Foo')
        self.param.document_auto_populated_param(
            'docs.request-params', self.doc_structure)
        self.assertEqual(
            '', self.doc_structure.flush_structure().decode('utf-8'))

    def test_param_not_in_section_request_example(self):
        top_section = self.doc_structure.add_new_section('structure-value')
        section = top_section.add_new_section('Foo')
        example = 'Foo: \'string\''
        section.write(example)
        self.assert_contains_line(example)
        self.param.document_auto_populated_param(
            'docs.request-example', self.doc_structure)
        self.assert_contains_line(example)


class TestTraverseAndDocumentShape(BaseDocsTest):
    def setUp(self):
        super(TestTraverseAndDocumentShape, self).setUp()
        self.event_emitter = mock.Mock()
        self.service = 'myservice'
        self.operation = 'SampleOperation'
        self.response_example_doc = ResponseExampleDocumenter(
            service=self.service, operation=self.operation,
            event_emitter=self.event_emitter)
        self.request_example_doc = RequestExampleDocumenter(
            service=self.service, operation=self.operation,
            event_emitter=self.event_emitter)
        self.response_params_doc = ResponseParamsDocumenter(
            service=self.service, operation=self.operation,
            event_emitter=self.event_emitter)
        self.request_params_doc = RequestParamsDocumenter(
            service=self.service, operation=self.operation,
            event_emitter=self.event_emitter)
        self.add_shape_to_params('Foo', 'String', 'This describes foo.')

    def test_events_emitted_response_example(self):
        traverse_and_document_shape(
            documenter=self.response_example_doc, section=self.doc_structure,
            shape=self.operation_model.input_shape, history=[]
        )
        structure_section = self.doc_structure.get_section('structure-value')
        self.assertEqual(
            self.event_emitter.emit.call_args_list,
            [mock.call('docs.response-example.myservice.SampleOperation.Foo',
                       section=structure_section.get_section('Foo')),
             mock.call(('docs.response-example.myservice.SampleOperation'
                        '.complete-section'), section=self.doc_structure)]
        )

    def test_events_emitted_request_example(self):
        traverse_and_document_shape(
            documenter=self.request_example_doc, section=self.doc_structure,
            shape=self.operation_model.input_shape, history=[]
        )
        structure_section = self.doc_structure.get_section('structure-value')
        self.assertEqual(
            self.event_emitter.emit.call_args_list,
            [mock.call('docs.request-example.myservice.SampleOperation.Foo',
                       section=structure_section.get_section('Foo')),
             mock.call(('docs.request-example.myservice.SampleOperation'
                        '.complete-section'), section=self.doc_structure)]
        )

    def test_events_emitted_response_params(self):
        traverse_and_document_shape(
            documenter=self.response_params_doc, section=self.doc_structure,
            shape=self.operation_model.input_shape, history=[]
        )
        self.assertEqual(
            self.event_emitter.emit.call_args_list,
            [mock.call('docs.response-params.myservice.SampleOperation.Foo',
                       section=self.doc_structure.get_section('Foo')),
             mock.call(('docs.response-params.myservice.SampleOperation'
                        '.complete-section'), section=self.doc_structure)]
        )

    def test_events_emitted_request_params(self):
        traverse_and_document_shape(
            documenter=self.request_params_doc, section=self.doc_structure,
            shape=self.operation_model.input_shape, history=[]
        )
        self.assertEqual(
            self.event_emitter.emit.call_args_list,
            [mock.call('docs.request-params.myservice.SampleOperation.Foo',
                       section=self.doc_structure.get_section('Foo')),
             mock.call(('docs.request-params.myservice.SampleOperation'
                        '.complete-section'), section=self.doc_structure)]
        )
