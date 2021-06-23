from pgctl import configsearch


class DescribeGlob:

    def it_globs_files(self, tmpdir):
        tmpdir.ensure('a/file.1')
        tmpdir.ensure('d/file.4')
        with tmpdir.as_cwd():
            assert list(configsearch.glob('*/file.*')) == ['a/file.1', 'd/file.4']
