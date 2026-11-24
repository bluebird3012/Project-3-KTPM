import unittest
from pages.picture_picker import classify_picture_source, is_expected_rejection


class PictureChecks(unittest.TestCase):
    def test_generic_moodle_icons(self):
        for url in ('http://localhost/theme/image.php/boost/core/123/f/image',
                    'http://localhost/theme/image.php?theme=boost&component=core&image=f%2Fimage',
                    'http://localhost/pix/f/image.svg'):
            self.assertEqual(classify_picture_source(url), 'icon')

    def test_generated_thumbnail(self):
        for preview in ('thumb', 'tinyicon'):
            self.assertEqual(classify_picture_source(f'http://localhost/draftfile.php/1/user/draft/2/example.png?preview={preview}&oid=3'), 'preview')

    def test_unknown_not_counted_as_icon(self):
        self.assertEqual(classify_picture_source('http://localhost/image.png'), 'unknown')
        self.assertEqual(classify_picture_source('http://localhost/draftfile.php/1/user/draft/2/a.png'), 'unknown')

    def test_explicit_rejections(self):
        self.assertTrue(is_expected_rejection('Text file filetype cannot be accepted.'))
        self.assertTrue(is_expected_rejection('File type not accepted: TXT'))
        self.assertTrue(is_expected_rejection('File is too large.'))
        self.assertTrue(is_expected_rejection('Maximum number of files exceeded', second=True))
        self.assertFalse(is_expected_rejection('Server connection failed'))
        self.assertFalse(is_expected_rejection('No file chosen'))
        self.assertFalse(is_expected_rejection(''))
