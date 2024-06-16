#!/usr/bin/env bash
mkdir -p ~/virtual/fescache/
python3 -m venv ~/virtual/fescache/
~/virtual/fescache//bin/pip install -U pip==20.2.4
~/virtual/fescache//bin/pip install wheel
~/virtual/fescache//bin/pip install -r requirements.txt
