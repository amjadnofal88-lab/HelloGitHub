#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
Tests for make_content.py
"""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, mock_open, MagicMock

sys.path.insert(0, os.path.dirname(__file__))

import make_content as mc_module


class TestInputError(unittest.TestCase):
    def test_message_attribute(self):
        err = mc_module.InputError('bad input')
        self.assertEqual(err.message, 'bad input')

    def test_str_representation(self):
        err = mc_module.InputError('something wrong')
        self.assertIn('something wrong', str(err))

    def test_is_exception(self):
        with self.assertRaises(mc_module.InputError):
            raise mc_module.InputError('test')


class TestCheckPath(unittest.TestCase):
    def test_existing_path_returns_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertTrue(mc_module.check_path(tmpdir))

    def test_nonexistent_path_returns_false(self):
        self.assertFalse(mc_module.check_path('/nonexistent/path/abc123'))

    def test_existing_file_returns_true(self):
        with tempfile.NamedTemporaryFile() as tmp:
            self.assertTrue(mc_module.check_path(tmp.name))

    def test_nonexistent_file_returns_false(self):
        self.assertFalse(mc_module.check_path('/tmp/nonexistent_file_xyz.txt'))


class TestReadWriteFile(unittest.TestCase):
    def test_read_file_returns_content(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as tmp:
            tmp.write('hello world')
            tmp_path = tmp.name
        try:
            result = mc_module.read_file(tmp_path)
            self.assertEqual(result, 'hello world')
        finally:
            os.unlink(tmp_path)

    def test_write_file_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'out.txt')
            mc_module.write_file(output_path, 'test content')
            with open(output_path, 'r') as f:
                content = f.read()
            self.assertEqual(content, 'test content')

    def test_write_then_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'roundtrip.txt')
            mc_module.write_file(path, 'round trip data')
            result = mc_module.read_file(path)
            self.assertEqual(result, 'round trip data')

    def test_write_file_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, 'file.txt')
            mc_module.write_file(path, 'original')
            mc_module.write_file(path, 'updated')
            self.assertEqual(mc_module.read_file(path), 'updated')


class TestMakeContent(unittest.TestCase):
    def _setup_dir(self, tmpdir, num, template_content, content_data):
        """Helper: create template.md and content<num>.md in a numbered subdir."""
        # Template at cwd level
        template_path = os.path.join(tmpdir, 'template.md')
        with open(template_path, 'w') as f:
            f.write(template_content)

        # Content in subdirectory named <num>
        num_dir = os.path.join(tmpdir, num)
        os.makedirs(num_dir, exist_ok=True)
        content_path = os.path.join(num_dir, 'content{}.md'.format(num))
        with open(content_path, 'w') as f:
            f.write(content_data)

        return tmpdir

    def test_generates_output_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._setup_dir(
                tmpdir, '01',
                '# Issue {{ hello_github_num }}\n{{ hello_github_content }}',
                'Hello World Content',
            )
            with patch('os.path.abspath') as mock_abs:
                mock_abs.return_value = tmpdir
                mc_module.make_content('01')

            output_path = os.path.join(tmpdir, '01', 'HelloGitHub01.md')
            self.assertTrue(os.path.exists(output_path))

    def test_substitutes_num_and_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._setup_dir(
                tmpdir, '42',
                'Num={{ hello_github_num }} Content={{ hello_github_content }}',
                'MY CONTENT',
            )
            with patch('os.path.abspath') as mock_abs:
                mock_abs.return_value = tmpdir
                mc_module.make_content('42')

            output_path = os.path.join(tmpdir, '42', 'HelloGitHub42.md')
            with open(output_path) as f:
                data = f.read()
            self.assertIn('Num=42', data)
            self.assertIn('Content=MY CONTENT', data)

    def test_returns_none_when_content_file_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Only create template, no content subdir
            template_path = os.path.join(tmpdir, 'template.md')
            with open(template_path, 'w') as f:
                f.write('template')
            with patch('os.path.abspath') as mock_abs:
                mock_abs.return_value = tmpdir
                result = mc_module.make_content('99')
            self.assertIsNone(result)

    def test_returns_none_when_template_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create content dir but no template
            num_dir = os.path.join(tmpdir, '05')
            os.makedirs(num_dir)
            with open(os.path.join(num_dir, 'content05.md'), 'w') as f:
                f.write('content')
            with patch('os.path.abspath') as mock_abs:
                mock_abs.return_value = tmpdir
                result = mc_module.make_content('05')
            self.assertIsNone(result)

    def test_multiple_flag_replacements(self):
        """Both flags should be replaced, even if they appear multiple times."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._setup_dir(
                tmpdir, '10',
                '{{ hello_github_num }} and {{ hello_github_num }} = {{ hello_github_content }}',
                'DATA',
            )
            with patch('os.path.abspath') as mock_abs:
                mock_abs.return_value = tmpdir
                mc_module.make_content('10')

            output_path = os.path.join(tmpdir, '10', 'HelloGitHub10.md')
            with open(output_path) as f:
                data = f.read()
            self.assertIn('10 and 10', data)
            self.assertIn('DATA', data)


class TestMakeAllContent(unittest.TestCase):
    @patch('make_content.make_content')
    def test_calls_make_content_for_each_dir(self, mock_make):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, '01'))
            os.makedirs(os.path.join(tmpdir, '02'))
            with patch('os.path.abspath') as mock_abs, \
                 patch('os.listdir') as mock_listdir, \
                 patch('os.path.isdir') as mock_isdir:
                mock_abs.return_value = tmpdir
                mock_listdir.return_value = ['01', '02', 'script', 'README.md']
                mock_isdir.side_effect = lambda p: p in ['01', '02', 'script']
                mc_module.make_all_content()

        # 'script' dir is excluded; '01' and '02' should be called
        called_args = [c[0][0] for c in mock_make.call_args_list]
        self.assertIn('01', called_args)
        self.assertIn('02', called_args)
        self.assertNotIn('script', called_args)

    @patch('make_content.make_content')
    def test_skips_script_directory(self, mock_make):
        with patch('os.path.abspath') as mock_abs, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.isdir') as mock_isdir:
            mock_abs.return_value = '/fake'
            mock_listdir.return_value = ['script_utils', 'my_script', '03']
            mock_isdir.side_effect = lambda p: True
            mc_module.make_all_content()

        called_args = [c[0][0] for c in mock_make.call_args_list]
        # Dirs containing 'script' in name are skipped
        self.assertNotIn('script_utils', called_args)
        self.assertNotIn('my_script', called_args)
        self.assertIn('03', called_args)

    @patch('make_content.make_content')
    def test_skips_non_directories(self, mock_make):
        with patch('os.path.abspath') as mock_abs, \
             patch('os.listdir') as mock_listdir, \
             patch('os.path.isdir') as mock_isdir:
            mock_abs.return_value = '/fake'
            mock_listdir.return_value = ['01', 'README.md', 'template.md']
            mock_isdir.side_effect = lambda p: p == '01'
            mc_module.make_all_content()

        called_args = [c[0][0] for c in mock_make.call_args_list]
        self.assertEqual(called_args, ['01'])


class TestMain(unittest.TestCase):
    @patch('make_content.make_content')
    def test_single_digit_prepends_zero(self, mock_make):
        with patch('sys.argv', ['make_content.py', '5']):
            mc_module.main()
        mock_make.assert_called_once_with('05')

    @patch('make_content.make_content')
    def test_two_digit_number(self, mock_make):
        with patch('sys.argv', ['make_content.py', '42']):
            mc_module.main()
        mock_make.assert_called_once_with('42')

    @patch('make_content.make_all_content')
    def test_all_argument_calls_make_all_content(self, mock_make_all):
        with patch('sys.argv', ['make_content.py', 'all']):
            mc_module.main()
        mock_make_all.assert_called_once()

    def test_no_args_raises_input_error(self):
        with patch('sys.argv', ['make_content.py']):
            with self.assertRaises(mc_module.InputError):
                mc_module.main()

    def test_too_many_args_raises_input_error(self):
        with patch('sys.argv', ['make_content.py', 'arg1', 'arg2']):
            with self.assertRaises(mc_module.InputError):
                mc_module.main()

    @patch('make_content.make_content')
    def test_three_digit_number(self, mock_make):
        with patch('sys.argv', ['make_content.py', '100']):
            mc_module.main()
        mock_make.assert_called_once_with('100')


if __name__ == '__main__':
    unittest.main()
