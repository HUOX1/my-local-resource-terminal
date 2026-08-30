from pathlib import Path
import tomllib


def test_setuptools_only_discovers_runtime_packages():
    config=tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8')); find=config['tool']['setuptools']['packages']['find']
    assert find['include']==['g3_core*','g3_launcher*']; assert 'g3_frontend*' in find['exclude']; assert find['namespaces'] is False


def test_v06_dependencies_do_not_pull_legacy_qt_runtime():
    config=tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8')); dependencies=config['project']['dependencies']
    assert all('pyside' not in item.casefold() for item in dependencies)
    assert all('pytest-qt' not in item.casefold() for item in config['project']['optional-dependencies']['test'])
