from setuptools import setup, find_packages

setup(
    name = 'pyvi',
    version = 0.1,
    packages = find_packages()+find_packages('pyqtgraph', exclude=['examples*']),
    package_dir = {'pyqtgraph':'pyqtgraph/pyqtgraph'},
    install_requires = [
        'click >= 6.7',
        'pyopengl >= 3.1.0',
        'numpy >= 1.12.0',
        ],
    entry_points = '''
        [console_scripts]
        flowchart=pyvi.scripts.flowchart:cli
    '''
)