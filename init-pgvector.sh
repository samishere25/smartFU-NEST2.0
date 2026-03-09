#!/bin/bash
set -e

apt-get update
apt-get install -y postgresql-15-pgvector
