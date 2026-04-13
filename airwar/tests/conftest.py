import pytest
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix='.json')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def clean_imports():
    if 'airwar.config' in sys.modules:
        del sys.modules['airwar.config']
    if 'airwar.utils.database' in sys.modules:
        del sys.modules['airwar.utils.database']
    if 'airwar.entities.base' in sys.modules:
        del sys.modules['airwar.entities.base']
    yield
