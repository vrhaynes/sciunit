# sciunit
# author Rick Gerkin rgerkin@asu.edu
FROM andrewosh/binder-base

RUN /home/main/anaconda/envs/python3/bin/python setup.py install
