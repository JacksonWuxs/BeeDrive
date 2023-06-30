pip uninstall BeeDrive -y
pip install -U wheel
pip install -U twine
python setup.py sdist bdist_wheel
twine upload dist/* -u JacksonWoo --skip-existing