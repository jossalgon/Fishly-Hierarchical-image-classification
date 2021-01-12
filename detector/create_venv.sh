VENV_NAME="venv-fishly2"
PYTHON_VERSION=3.6

# Create venv
virtualenv --python=/usr/bin/python$PYTHON_VERSION $VENV_NAME

# Activate venv
source $VENV_NAME/bin/activate

# Install jupyter in venv
#pip install jupyter
pip install ipykernel
python -m ipykernel install --user --name $VENV_NAME --display-name $VENV_NAME
